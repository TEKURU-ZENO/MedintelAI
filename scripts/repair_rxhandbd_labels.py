"""
Detects and repairs row-offset misalignment in RxHandBD's Train_Label.csv / Test_Label.csv.

The published CSVs drift out of sync with the image files (e.g. a dropped row shifts every following
label onto the neighbouring image). This script decodes every image with a trained HTR checkpoint,
then for each image tests whether the *human* label from a neighbouring row (offset -3..+3) matches far
better than its own row. Offsets are only applied inside consistent runs (majority vote over a sliding
window), so isolated misreads never move a label. No label text is ever invented: repaired rows simply
take an existing human label from a neighbouring row.

Output: datasets/htr_corpora/rxhandbd/labels_realigned.json, used by datasets/htr_sources.load_rxhandbd
when present. The original CSVs are left untouched.

Usage:
    python scripts/repair_rxhandbd_labels.py --model_dir app/ai/models/trocr_medical_finetuned
"""
import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datasets.htr_sources import DEFAULT_CORPORA_DIR, normalize_label  # noqa: E402
from app.ai.ocr.htr_engine import MedicalHTREngine  # noqa: E402

OFFSETS = (-3, -2, -1, 1, 2, 3)


def _cer(a: str, b: str) -> float:
    a, b = a.lower(), b.lower()
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1] / max(1, len(b) if len(b) else len(a))


def repair_split(rows, preds, window: int = 7, min_votes: int = 3, accept_cer: float = 0.34, margin: float = 0.25):
    labels = [normalize_label(r["Text"]) for r in rows]
    n = len(labels)
    votes = []
    for i in range(n):
        own = _cer(labels[i], preds[i]) if labels[i] else 9.0
        best_k, best_d = 0, own
        for k in OFFSETS:
            j = i + k
            if 0 <= j < n and labels[j]:
                d = _cer(labels[j], preds[i])
                if d < best_d:
                    best_k, best_d = k, d
        ok = best_k != 0 and best_d <= accept_cer and best_d + margin < own
        votes.append(best_k if ok else (0 if own <= accept_cer else None))

    offsets = [0] * n
    half = window // 2
    for i in range(n):
        win = [v for v in votes[max(0, i - half): i + half + 1] if v is not None]
        if not win:
            continue
        k, c = Counter(win).most_common(1)[0]
        if k != 0 and c >= min_votes:
            offsets[i] = k

    fixed = {}
    for i, k in enumerate(offsets):
        if k != 0 and 0 <= i + k < n:
            fixed[rows[i]["Images"]] = {"original": labels[i], "realigned": labels[i + k], "offset": k}
    return fixed, offsets


def main():
    parser = argparse.ArgumentParser(description="Repair RxHandBD label/row misalignment")
    parser.add_argument("--model_dir", default=str(ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"))
    parser.add_argument("--corpora_dir", default=str(DEFAULT_CORPORA_DIR))
    parser.add_argument("--batch_size", type=int, default=16)
    args = parser.parse_args()

    base = Path(args.corpora_dir) / "rxhandbd"
    root = next(p.parent for p in base.rglob("Train_Label.csv"))
    engine = MedicalHTREngine.from_pretrained(args.model_dir, num_beams=4, lexicon_conf_gate=0.0, rescore_weight=0.0)

    import cv2
    import numpy as np

    report = {"model_dir": args.model_dir, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "splits": {}}
    realigned = {}
    for csv_name, img_dir in (("Train_Label.csv", "Train_Set"), ("Test_Label.csv", "Test_Set")):
        with open(root / csv_name, encoding="utf-8-sig", newline="") as f:
            rows = [r for r in csv.DictReader(f) if (root / img_dir / r["Images"].strip()).exists()]
        preds = []
        for i in range(0, len(rows), args.batch_size):
            chunk = rows[i: i + args.batch_size]
            imgs = [cv2.imdecode(np.fromfile(str(root / img_dir / r["Images"].strip()), np.uint8), cv2.IMREAD_COLOR)
                    for r in chunk]
            preds += [res["raw_text"] for res in engine.recognize_batch(imgs)]
        fixed, offsets = repair_split(rows, preds)
        realigned.update({f"{img_dir}/{k}": v for k, v in fixed.items()})
        runs = Counter(offsets)
        report["splits"][csv_name] = {
            "rows": len(rows), "realigned": len(fixed), "offset_histogram": {str(k): v for k, v in sorted(runs.items())},
        }
        print(f"{csv_name}: {len(fixed)}/{len(rows)} rows realigned, offsets {dict(runs)}", flush=True)

    out = base / "labels_realigned.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"report": report, "labels": realigned}, f, indent=1, ensure_ascii=False)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
