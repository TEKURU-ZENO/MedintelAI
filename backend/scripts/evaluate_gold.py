"""
Gold-set evaluation of the full desktop OCR pipeline (backend/app) on real documents.

Gold files live in datasets/gold/<name>.json (see datasets/gold/README.md). Per page it reports:
  line_cer / line_wer   recognition quality independent of order: each gold line is matched one-to-one to
                        its best predicted block; missed gold lines count as fully wrong
  insertion_rate        characters of predicted text that match no gold line (signatures read as text,
                        bleed-through, hallucinations), relative to gold characters
  page_cer              order-aware CER of the whole page text
  order_tau             Kendall tau between gold and predicted order of matched lines (1.0 = same order)
  field_f1              structured-field F1 (medications etc.) when the pipeline returns structured output

Usage (from backend/):
    python scripts/evaluate_gold.py                      # all gold pages
    python scripts/evaluate_gold.py --only rx_white_tusk --label lm_rescoring
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

GOLD_DIR = REPO / "datasets" / "gold"
OUT_DIR = REPO / "outputs" / "gold_eval"


def edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def norm(t: str) -> str:
    t = t.replace("—", "-").replace("–", "-").replace("×", "x")
    return re.sub(r"\s+", " ", t).strip().lower()


def kendall_tau(order_pairs):
    n = len(order_pairs)
    if n < 2:
        return 1.0
    conc = disc = 0
    for i in range(n):
        for j in range(i + 1, n):
            a = (order_pairs[i][0] - order_pairs[j][0]) * (order_pairs[i][1] - order_pairs[j][1])
            conc += a > 0
            disc += a < 0
    return (conc - disc) / max(1, conc + disc)


def match_lines(gold, preds):
    """Greedy one-to-one matching by normalised CER (accept CER < 0.6)."""
    cands = []
    for gi, g in enumerate(gold):
        for pi, p in enumerate(preds):
            if not g or not p:
                continue
            c = edit_distance(g, p) / max(1, len(g))
            if c < 0.6:
                cands.append((c, gi, pi))
    cands.sort()
    used_g, used_p, pairs = set(), set(), []
    for c, gi, pi in cands:
        if gi in used_g or pi in used_p:
            continue
        used_g.add(gi)
        used_p.add(pi)
        pairs.append((gi, pi))
    return pairs


MED_ATTRS = ("strength", "frequency", "duration", "timing", "form")


def _fval(v):
    return re.sub(r"[\s.]", "", norm(str(v)))


def field_f1(gold_fields, structured):
    """
    F1 over (attribute, value) facts: each medication contributes (drug) plus (drug, attribute, value) for every
    attribute the gold labels; patient fields contribute (field, value). Only attribute types the gold page
    labels are scored, so a dataset without e.g. durations is not penalised for extracting them.
    """
    if not gold_fields or structured is None:
        return None
    gold_items, pred_items = set(), set()
    labelled = {a for m in gold_fields.get("medications", []) for a in MED_ATTRS if m.get(a)}
    for src, items in ((gold_fields, gold_items), (structured, pred_items)):
        for m in src.get("medications", []) or []:
            d = _fval(m.get("drug", ""))
            if not d:
                continue
            items.add(("drug", d))
            for a in labelled:
                # Gold "timing" also holds SIG instructions ("as directed", "every 8 hours"), which the
                # structurer reports separately as "instructions"
                value = m.get(a) or (m.get("instructions") if a == "timing" else None)
                if value:
                    items.add((a, d, _fval(value)))
        for k in ("patient_name", "age", "sex", "date"):
            if gold_fields.get(k) and src.get(k):
                items.add((k, _fval(src[k])))
    if not gold_items:
        return None
    tp = len(gold_items & pred_items)
    prec = tp / max(1, len(pred_items))
    rec = tp / max(1, len(gold_items))
    return round(2 * prec * rec / max(1e-9, prec + rec), 4)


def word_f1(gold_text, pred_text):
    """Order- and segmentation-free bag-of-words F1 (punctuation stripped)."""
    from collections import Counter
    tok = lambda t: Counter(w for w in re.sub(r"[^\w/%.-]", " ", norm(t)).split() if w.strip(".-"))
    g, p = tok(gold_text), tok(pred_text)
    tp = sum((g & p).values())
    prec = tp / max(1, sum(p.values()))
    rec = tp / max(1, sum(g.values()))
    return round(2 * prec * rec / max(1e-9, prec + rec), 4)


def evaluate_page(controller, gold_path: Path):
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    img_path = gold_path.parent / gold["image"]
    t0 = time.time()
    result = controller.process_document(img_path.read_bytes(), doc_name=img_path.name)
    elapsed = time.time() - t0
    blocks = result.get("blocks", [])
    ignore = gold.get("ignore_top_px", 0)
    # Score reading rows (blocks sharing a row joined in reading order), the unit a reader sees: table cells
    # of one row form one line, and a margin note merged into a line counts against it
    rows = {}
    for b in blocks:
        if b.get("bbox", [0, ignore + 1])[3] <= ignore or not b.get("text") or b.get("role") == "signature":
            continue  # gold excludes signatures, so detected signatures are not scored as text
        rows.setdefault(b.get("line_number", b.get("reading_order", 0)), []).append(b)
    preds_raw = ["  ".join(x["text"] for x in sorted(r, key=lambda x: x.get("reading_order", 0)))
                 for _, r in sorted(rows.items())]
    preds = [norm(t) for t in preds_raw]
    scored_lines = [l for l in gold["lines"] if l.get("role") != "signature" and l.get("text")]
    gold_norm = [norm(l["text"]) for l in scored_lines]

    pairs = match_lines(gold_norm, preds)
    matched_g = {g for g, _ in pairs}
    matched_p = {p for _, p in pairs}
    errors = sum(edit_distance(gold_norm[g], preds[p]) for g, p in pairs)
    errors += sum(len(gold_norm[g]) for g in range(len(gold_norm)) if g not in matched_g)
    gold_chars = sum(len(g) for g in gold_norm) or 1
    word_err = sum(edit_distance(gold_norm[g].split(), preds[p].split()) for g, p in pairs)
    word_err += sum(len(gold_norm[g].split()) for g in range(len(gold_norm)) if g not in matched_g)
    gold_words = sum(len(g.split()) for g in gold_norm) or 1
    insertions = sum(len(preds[p]) for p in range(len(preds)) if p not in matched_p)

    page_gold = " ".join(gold_norm)
    page_pred = " ".join(preds)
    report = {
        "page": gold_path.stem,
        "doc_type": gold.get("doc_type"),
        "handwritten": gold.get("handwritten", False),
        "line_cer": round(errors / gold_chars, 4),
        "line_wer": round(word_err / gold_words, 4),
        "insertion_rate": round(insertions / gold_chars, 4),
        "page_cer": round(edit_distance(page_gold, page_pred) / max(1, len(page_gold)), 4),
        "order_tau": round(kendall_tau(sorted(pairs)), 4),
        "word_f1": word_f1(" ".join(gold_norm), " ".join(preds)),
        "missed_lines": [scored_lines[g]["text"] for g in range(len(scored_lines)) if g not in matched_g],
        "extra_text": [preds_raw[p] for p in range(len(preds)) if p not in matched_p],
        "field_f1": field_f1(gold.get("fields"), (result.get("metadata") or {}).get("structured") or result.get("structured")),
        "seconds": round(elapsed, 1),
        "predicted_text": result.get("raw_text", ""),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default=None, help="comma-separated gold page names")
    parser.add_argument("--label", default="current", help="name for the saved report (for before/after)")
    parser.add_argument("--verbose", action="store_true", help="print every page")
    args = parser.parse_args()

    os.chdir(BACKEND)
    from app.ai.pipeline.pipeline_controller import PipelineController
    controller = PipelineController()

    pages = sorted(GOLD_DIR.glob("*.json"))
    if args.only:
        wanted = set(args.only.split(","))
        pages = [p for p in pages if p.stem in wanted]
    reports = [evaluate_page(controller, p) for p in pages]

    def agg(rows, key):
        vals = [r[key] for r in rows if r[key] is not None]
        return round(sum(vals) / len(vals), 4) if vals else None

    keys = ("line_cer", "line_wer", "word_f1", "insertion_rate", "page_cer", "order_tau", "field_f1", "seconds")
    if args.verbose:
        print(f"{'page':40s} " + " ".join(f"{k[:8]:>8s}" for k in keys))
        for r in reports:
            print(f"{r['page']:40s} " + " ".join(f"{str(r[k]):>8s}" for k in keys))

    def group(r):
        p = r["page"]
        for pre in ("gnhk_", "funsd_", "rxsynth_", "printed_"):
            if p.startswith(pre):
                return pre.rstrip("_")
        return "user_pages"

    summary = {}
    for name in sorted({group(r) for r in reports}):
        rows = [r for r in reports if group(r) == name]
        summary[name] = {"pages": len(rows), **{k: agg(rows, k) for k in keys}}
    print(f"{'group':12s} {'pages':>5s} " + " ".join(f"{k[:8]:>8s}" for k in keys))
    for name, s in summary.items():
        print(f"{name:12s} {s['pages']:5d} " + " ".join(f"{str(s[k]):>8s}" for k in keys))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.label}.json"
    out.write_text(json.dumps({"summary": summary, "pages": reports}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"saved {out}")


if __name__ == "__main__":
    main()
