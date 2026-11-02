"""
Fits reading_margin for ContextSpellCorrector.choose_reading (app/ai/ocr/htr_language_model.py): where PP-OCR and
TrOCR read a word of the same crop differently and both readings are real words ("gun paint" / "gum paint"),
the language model may switch to the other reading when it prefers it by at least the margin.

Uses the crops collected by scripts/collect_ensemble_candidates.py (both readings + ground truth), in both
directions: a TrOCR line checked against PP-OCR's reading (handwriting path) and the reverse (printed path).
The margin (and clinical_prior, the margin's discount when the other word is a clinical term) is the pair whose
validation CER is best with no source worse than without the step. Drug swaps (an unknown word becomes the
formulary drug the other reading spells) have no parameter and are applied throughout.
--install adds reading_margin and clinical_prior to <checkpoint>/spell_correction.json.

Usage:
    python scripts/fit_reading_choice.py --val outputs/ensemble_large/ensemble_val.json \
        --test outputs/ensemble_large/ensemble_test.json --install app/ai/models/trocr_medical_finetuned
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ai.ocr.htr_language_model import ContextSpellCorrector, _match_case  # noqa: E402
from scripts.train_trocr_medical import _edit_distance  # noqa: E402

DIRECTIONS = (("trocr_text", "rapid_text"), ("rapid_text", "trocr_text"))
MARGINS = [0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 1e9]
PRIORS = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0]


def precompute(corrector, rows, mine, theirs):
    """Per row: the swaps choose_reading would consider, each with its LM gain and clinical flag (applied in order)."""
    import re
    out = []
    for r in rows:
        text, other = r[mine] or "", r[theirs] or ""
        text = _apply_drugs(corrector, text, other)
        tokens = text.split()
        swaps = []
        for i, alt in corrector.reading_swaps(text, other):
            m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z'-]*[A-Za-z])([^A-Za-z]*)$", tokens[i])
            if not m:
                continue
            pre, core, post = m.groups()
            variant = tokens[:i] + [f"{pre}{_match_case(core, alt)}{post}"] + tokens[i + 1:]
            base, new = corrector.sentence_logprobs([" ".join(tokens), " ".join(variant)])
            swaps.append((i, variant[i], new - base, corrector._clinical_bonus(core, alt) > 0))
        out.append((tokens, swaps))
    return out


def _apply_drugs(corrector, text, other):
    import re
    tokens = text.split()
    for i, drug in corrector.drug_swaps(text, other):
        m = re.match(r"^([^A-Za-z]*)([A-Za-z][A-Za-z'-]*[A-Za-z])([^A-Za-z]*)$", tokens[i])
        tokens[i] = f"{m.group(1)}{drug}{m.group(3)}"
    return " ".join(tokens)


def apply(pre_rows, margin, prior=0.0):
    preds = []
    for tokens, swaps in pre_rows:
        toks = list(tokens)
        for i, word, gain, clinical in swaps:
            if gain > margin - (prior if clinical else 0.0):
                toks[i] = word
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
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--install", default=None)
    args = parser.parse_args()

    lex = json.loads((Path(args.model_dir) / "medical_lexicon.json").read_text(encoding="utf-8"))
    corrector = ContextSpellCorrector(extra_words=lex.get("common_words", []), protected_terms=lex.get("terms", []),
                                      device=args.device, params={"clinical_prior": 1.0})
    val = json.loads(Path(args.val).read_text(encoding="utf-8"))
    test = json.loads(Path(args.test).read_text(encoding="utf-8"))
    pre = {d: (precompute(corrector, val, *d), precompute(corrector, test, *d)) for d in DIRECTIONS}

    best, best_obj = (1e9, 0.0), None
    for margin in MARGINS:
        for prior in PRIORS:
            objs, ok = [], True
            for d in DIRECTIONS:
                base = cer_by_source(val, [r[d[0]] or "" for r in val])
                cer = cer_by_source(val, apply(pre[d][0], margin, prior))
                ok &= all(cer[s] <= base[s] + 1e-9 for s in cer)
                objs.append(sum(cer.values()) / len(cer))
            obj = sum(objs) / len(objs)
            print(f"margin {margin:g} prior {prior:g}: val mean CER {obj:.5f}{'' if ok else ' (a source got worse)'}")
            if ok and (best_obj is None or obj < best_obj - 1e-9):
                best, best_obj = (margin, prior), obj
    best_margin, best_prior = best
    print("fitted reading_margin", best_margin, "clinical_prior", best_prior)
    for d in DIRECTIONS:
        drugs = sum(1 for r in test if corrector.drug_swaps(r[d[0]] or "", r[d[1]] or ""))
        clinical = sum(1 for (_, sw) in pre[d][1] for s in sw if s[3])
        print(f"{d[0]} checked against {d[1]}:")
        print(f"  test lines with a drug swap {drugs}, clinical candidate swaps {clinical}")
        print("  test before", cer_by_source(test, [r[d[0]] or "" for r in test]))
        print("  test after ", cer_by_source(test, apply(pre[d][1], best_margin, best_prior)))
        changed = sum(1 for (_, sw) in pre[d][1] for _, _, g, c in sw if g > best_margin - (best_prior if c else 0))
        print(f"  words switched on test: {changed}")
    if args.install:
        target = Path(args.install) / "spell_correction.json"
        cfg = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {"params": {}}
        cfg.setdefault("params", {}).update(reading_margin=best_margin, clinical_prior=best_prior)
        target.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("installed", target)


if __name__ == "__main__":
    main()
