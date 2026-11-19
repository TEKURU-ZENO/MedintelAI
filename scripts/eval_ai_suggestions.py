"""
Measures the AI word suggestions (app/ai/ocr/ai_word_review.py) on the ensemble crops, where the true line is known:
of the words the local vision model proposes on unsure lines, how many are right, how many are wrong, and how many
replace a word that was already right. The text is never changed, so this measures reviewer effort and usefulness.

Usage:
    python scripts/eval_ai_suggestions.py --rows outputs/ensemble_large/ensemble_test.json --split test --per_source 80
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.ai.ocr.ai_word_review import AIWordReviewer, enhanced_view  # noqa: E402
from app.ai.ocr.htr_ensemble import choose, configure_from  # noqa: E402
from app.ai.ocr.htr_language_model import ContextSpellCorrector  # noqa: E402
from app.ai.ocr.text_review import _words  # noqa: E402
from app.ai.ocr.vlm_reader import VLMLineReader  # noqa: E402
from scripts.fit_spell_correction import rebuild_crops  # noqa: E402

SOURCES = ("gnhk_line", "iam_line", "rxhandbd", "kaggle_rx_bd")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--per_source", type=int, default=80)
    parser.add_argument("--model_dir", default=str(ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"))
    parser.add_argument("--min_conf", type=float, nargs="*", default=[0.3, 0.5, 0.7, 0.85])
    args = parser.parse_args()

    rows = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    crops = rebuild_crops(rows, args.split)
    configure_from(args.model_dir, "cuda")
    lex = json.loads((Path(args.model_dir) / "medical_lexicon.json").read_text(encoding="utf-8"))
    spell = ContextSpellCorrector(extra_words=lex.get("common_words", []), protected_terms=lex.get("terms", []), device="cpu")
    validity = lambda t: sum(spell._is_known(w.lower()) for w in t.split()) / max(1, len(t.split()))

    rng, chosen = random.Random(3), []
    for src in SOURCES:
        unsure = []
        for r in rows:
            if r["source"] != src:
                continue
            text, conf, _ = choose((r["rapid_text"] or "", r["rapid_conf"] or 0.0), (r["trocr_text"] or "", r["trocr_conf"] or 0.0), validity)
            if text and conf < 0.85:
                unsure.append({"row": r, "text": text, "confidence": conf})
        rng.shuffle(unsure)
        chosen += unsure[: args.per_source]
    print("unsure lines", len(chosen), flush=True)

    reader = VLMLineReader(device="cuda")
    images, prompts = [], []
    for c in chosen:
        crop, r = crops[id(c["row"])], c["row"]
        prompt = reader.context_prompt([x for x in (c["text"], r["rapid_text"], r["trocr_text"]) if x])
        images += [crop, enhanced_view(crop)]
        prompts += [prompt, prompt]
    reads = reader.read(images, prompts=prompts, batch_size=4)

    for min_conf in args.min_conf:
        rev = AIWordReviewer(reader, lambda w: spell._is_known(w.lower()), lex.get("terms", []), params={"min_conf": min_conf})
        tally = defaultdict(lambda: defaultdict(int))
        for k, c in enumerate(chosen):
            r = c["row"]
            block = {"text": c["text"], "readings": {"ppocr": r["rapid_text"], "trocr": r["trocr_text"]}}
            truth = {(w["word"] or w["token"]).lower() for w in _words(r["gt"])}
            for p in rev.proposals(block, reads[2 * k: 2 * k + 2]):
                t = tally[r["source"]]
                t["proposed"] += 1
                good, was_right = p["suggestion"].lower() in truth, p["word"].lower() in truth
                t["right"] += good
                t["replaces_right_word"] += was_right and not good
        print(f"min_conf {min_conf}")
        for src in SOURCES:
            t = tally[src]
            print(f"  {src:14s} proposed {t['proposed']:4d}  right {t['right']:4d}  would break a right word {t['replaces_right_word']:3d}"
                  f"  precision {t['right'] / max(1, t['proposed']):.2f}")


if __name__ == "__main__":
    main()
