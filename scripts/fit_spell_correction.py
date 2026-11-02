"""
Fits the context spelling-correction parameters (app/ai/ocr/htr_language_model.py) on the TrOCR readings of
validation crops collected by scripts/collect_ensemble_candidates.py, and reports the held-out effect.

Medical word crops (RxHandBD, Kaggle) are part of the objective, so a setting that helps English but damages
drug names is rejected. --install writes the fitted parameters to <checkpoint>/spell_correction.json.

--image also scores every candidate line against its crop with the TrOCR checkpoint (the crops are rebuilt
exactly as collect_ensemble_candidates.py sampled them) and fits image_weight / image_veto.

Usage:
    python scripts/fit_spell_correction.py --val outputs/ensemble_large/ensemble_val.json \
        --test outputs/ensemble_large/ensemble_test.json --image --install app/ai/models/trocr_medical_finetuned
"""
import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ai.ocr.htr_language_model import ContextSpellCorrector, channel_cost  # noqa: E402
from scripts.train_trocr_medical import _edit_distance  # noqa: E402

HANDWRITING = ("gnhk_line", "iam_line", "rxhandbd", "kaggle_rx_bd")


def rebuild_crops(rows, split):
    """The crops each row was read from, re-sampled in collection order (same rng => same crops)."""
    import random
    from datasets.htr_sources import load_all_image_corpora
    from scripts.collect_ensemble_candidates import sample_pairs
    corpora = load_all_image_corpora()
    synth_texts = sorted({s.text for name in ("iam_line", "rxhandbd") for s in corpora.get(name, [])
                          if s.split == "train" and 3 <= len(s.text) <= 60})
    order = []
    for r in rows:
        if r["source"] not in order:
            order.append(r["source"])
    by_source = defaultdict(list)
    for r in rows:
        by_source[r["source"]].append(r)
    rng = random.Random(7 if split == "val" else 11)
    crops = {}
    for src in order:
        pairs = sample_pairs(src, split, len(by_source[src]), rng, corpora, synth_texts)
        for (img, gt), r in zip(pairs, by_source[src]):
            assert gt == r["gt"], (src, gt, r["gt"])
            crops[id(r)] = img
    return crops


def precompute(corrector, rows, htr=None, crops=None, field="trocr_text"):
    """
    Per row: list of suspicious word slots, each with candidate (word, lm_gain, channel, rarity, image_gain);
    image_gain is 0 without --image.
    """
    import re
    out = []
    for r in rows:
        tokens = (r[field] or "").split()
        slots = []
        if len(tokens) >= 2:
            for i in range(len(tokens)):
                if not corrector.suspicious(tokens, i):
                    continue
                m = re.match(r"^([^A-Za-z]*)([A-Za-z]+)([^A-Za-z]*)$", tokens[i])
                if not m:
                    continue
                pre, core, post = m.groups()
                from symspellpy import Verbosity
                sugg = corrector.sym.lookup(core.lower(), Verbosity.ALL, max_edit_distance=2, include_unknown=False)
                cands = sorted({s.term for s in sugg if s.term != core.lower()},
                               key=lambda t: (channel_cost(core, t), -corrector.sym.words.get(t, 0)))[:8]
                if not cands:
                    continue
                cased = [c[:1].upper() + c[1:] if core[:1].isupper() else c for c in cands]
                variants = [" ".join(tokens[:i] + [f"{pre}{c}{post}"] + tokens[i + 1:]) for c in cased]
                scores = corrector.sentence_logprobs([" ".join(tokens)] + variants)
                img = [0.0] * (len(variants) + 1)
                if htr is not None:
                    img = htr.score_texts(crops[id(r)], [" ".join(tokens)] + variants)
                slots.append((i, pre, post, [(cw, s - scores[0], channel_cost(core, c), corrector._rarity(c), im - img[0])
                                             for c, cw, s, im in zip(cands, cased, scores[1:], img[1:])]))
        out.append((tokens, slots))
    return out


def apply(pre_rows, rows, params, min_words):
    preds = []
    for r, (tokens, slots) in zip(rows, pre_rows):
        toks = list(tokens)
        if len(toks) >= min_words:
            for i, pre, post, cands in slots:
                best, best_gain = None, params["margin"]
                for cw, lm_gain, ch, rar, img_gain in cands:
                    if params.get("image_weight", 0) > 0 and img_gain < -params["image_veto"]:
                        continue
                    g = lm_gain - params["channel_weight"] * ch - params["freq_weight"] * rar \
                        + params.get("image_weight", 0) * img_gain
                    if g > best_gain:
                        best, best_gain = cw, g
                if best:
                    toks[i] = f"{pre}{best}{post}"
        preds.append(" ".join(toks))
    return preds


def cer_by_source(rows, preds):
    agg = defaultdict(lambda: [0, 0])
    for r, p in zip(rows, preds):
        agg[r["source"]][0] += _edit_distance(r["gt"].lower(), p.lower())
        agg[r["source"]][1] += max(1, len(r["gt"]))
    return {k: round(e / n, 4) for k, (e, n) in agg.items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val", required=True)
    parser.add_argument("--test", required=True)
    parser.add_argument("--model_dir", default=str(ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"))
    parser.add_argument("--install", default=None)
    parser.add_argument("--image", action="store_true", help="also fit image_weight / image_veto from the crops")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--reading", choices=("trocr", "rapid"), default="trocr",
                        help="whose readings to correct: TrOCR (handwriting path) or PP-OCR (printed path)")
    args = parser.parse_args()

    lex = json.loads((Path(args.model_dir) / "medical_lexicon.json").read_text(encoding="utf-8"))
    corrector = ContextSpellCorrector(extra_words=lex.get("common_words", []), protected_terms=lex.get("terms", []))
    all_val = json.loads(Path(args.val).read_text(encoding="utf-8"))
    all_test = json.loads(Path(args.test).read_text(encoding="utf-8"))
    htr = crops_v = crops_t = None
    if args.image:
        from app.ai.ocr.htr_engine import MedicalHTREngine
        htr = MedicalHTREngine.from_pretrained(args.model_dir, device=args.device)
        crops_v, crops_t = rebuild_crops(all_val, "val"), rebuild_crops(all_test, "test")
    val = [r for r in all_val if r["source"] in HANDWRITING]
    test = [r for r in all_test if r["source"] in HANDWRITING]
    field = f"{args.reading}_text"
    pv, pt = precompute(corrector, val, htr, crops_v, field), precompute(corrector, test, htr, crops_t, field)

    base_v = cer_by_source(val, [r[field] or "" for r in val])
    base_t = cer_by_source(test, [r[field] or "" for r in test])
    print("val  baseline", base_v)
    grid = {"channel_weight": [0.5, 1.0, 2.0, 3.0, 4.0], "freq_weight": [0.0, 0.3, 0.6, 1.0],
            "margin": [0.0, 0.5, 1.0, 2.0, 3.0], "min_line_words": [2, 3, 4]}
    if args.image:
        grid.update({"channel_weight": [1.0, 2.0, 3.0, 4.0], "freq_weight": [0.0, 0.3, 0.6],
                     "margin": [0.0, 0.5, 1.0, 2.0, 3.0], "min_line_words": [2, 3],
                     "image_weight": [0.0, 0.1, 0.25, 0.5, 1.0], "image_veto": [0.0, 2.0, 5.0, 1e9]})
    best, best_obj, text_only, text_obj = None, None, None, None
    for vals in itertools.product(*grid.values()):
        p = dict(zip(grid.keys(), vals))
        if p.get("image_weight", 0) == 0 and p.get("image_veto", 1e9) != 1e9:
            continue  # the veto only acts with the image term on
        cer = cer_by_source(val, apply(pv, val, p, p["min_line_words"]))
        # Never accept a setting that worsens any medical source
        if any(cer[s] > base_v[s] + 1e-9 for s in ("rxhandbd", "kaggle_rx_bd") if s in cer):
            continue
        obj = sum(cer.values()) / len(cer)
        if best_obj is None or obj < best_obj:
            best, best_obj = p, obj
        if p.get("image_weight", 0) == 0 and (text_obj is None or obj < text_obj):
            text_only, text_obj = p, obj
    if args.image and text_only:
        print("text-only fit", text_only)
        print("test text-only", cer_by_source(test, apply(pt, test, text_only, text_only["min_line_words"])))
    print("fitted", best)
    print("val  corrected", cer_by_source(val, apply(pv, val, best, best["min_line_words"])))
    print("test baseline ", base_t)
    print("test corrected", cer_by_source(test, apply(pt, test, best, best["min_line_words"])))
    if args.install:
        target = Path(args.install) / "spell_correction.json"
        target.write_text(json.dumps({"params": best}, indent=2), encoding="utf-8")
        print("installed", target)


if __name__ == "__main__":
    main()
