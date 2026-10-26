"""
Benchmarks RapidOCR detector / recogniser model sets for the printed-text path.

Compares the legacy rapidocr-onnxruntime package (PP-OCRv4 mobile) against rapidocr 3.x model sets
(PP-OCRv5 mobile/server, PP-OCRv6 small/medium) on:
  - FUNSD test forms (real noisy scans, word-level ground truth)
  - the synthetic medical document samples under datasets/<category>/sample_1.{png,txt}
Metric: word-level multiset F1 (case-insensitive, punctuation stripped) and CPU latency per page.

Usage:
    python scripts/benchmark_rapidocr_models.py --configs legacy,v5_server,v6_medium --threads 4
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MEDICAL_DIRS = ["admission_forms", "clinical_notes", "consent_forms", "discharge_summaries", "lab_reports",
                "mixed_documents", "prescriptions", "referral_forms"]


def words(text: str):
    return [w for w in (re.sub(r"[^\w./%-]", "", t).lower().strip(".,") for t in text.split()) if w]


def f1(gt_words, pred_words):
    g, p = Counter(gt_words), Counter(pred_words)
    tp = sum((g & p).values())
    prec = tp / max(1, sum(p.values()))
    rec = tp / max(1, sum(g.values()))
    return 2 * prec * rec / max(1e-9, prec + rec), prec, rec


def load_samples(max_funsd: int):
    samples = []
    funsd = ROOT / "datasets" / "report dataset" / "testing_data"
    for ann in sorted((funsd / "annotations").glob("*.json"))[:max_funsd]:
        img = funsd / "images" / (ann.stem + ".png")
        if not img.exists():
            continue
        form = json.loads(ann.read_text(encoding="utf-8")).get("form", [])
        gt = " ".join(w["text"] for f in form for w in f.get("words", []) if w.get("text"))
        samples.append(("funsd", str(img), gt))
    for d in MEDICAL_DIRS:
        base = ROOT / "datasets" / d
        for img in sorted(base.glob("*.png")) + sorted(base.glob("*.jpg")):
            txt = img.with_suffix(".txt")
            if txt.exists() and txt.stat().st_size > 0:
                samples.append(("medical", str(img), txt.read_text(encoding="utf-8")))
    return samples


def make_engine(name: str, threads: int):
    """Returns a callable image -> (list of quads, list of texts)."""
    if name == "legacy":
        from rapidocr_onnxruntime import RapidOCR as LegacyOCR
        eng = LegacyOCR(intra_op_num_threads=threads)

        def run(img):
            res, _ = eng(img)
            res = res or []
            return [np.array(r[0]) for r in res], [r[1] for r in res]
        return run

    from rapidocr import RapidOCR
    from rapidocr.utils.typings import LangDet, LangRec, ModelType, OCRVersion
    presets = {
        "v5_mobile": (OCRVersion.PPOCRV5, ModelType.MOBILE, ModelType.MOBILE, LangRec.EN),
        "v5_server": (OCRVersion.PPOCRV5, ModelType.SERVER, ModelType.SERVER, LangRec.CH),
        "v6_small": (OCRVersion.PPOCRV6, ModelType.SMALL, ModelType.SMALL, None),
        "v6_medium": (OCRVersion.PPOCRV6, ModelType.MEDIUM, ModelType.MEDIUM, None),
    }
    ver, det_t, rec_t, rec_lang = presets[name]
    params = {
        "Global.log_level": "error",
        "EngineConfig.onnxruntime.intra_op_num_threads": threads,
        "Det.ocr_version": ver, "Det.model_type": det_t,
        "Rec.ocr_version": ver, "Rec.model_type": rec_t,
    }
    if ver == OCRVersion.PPOCRV6:
        params["Det.lang_type"] = "en"
        params["Rec.lang_type"] = "en"
    elif rec_lang is not None:
        params["Rec.lang_type"] = rec_lang
    eng = RapidOCR(params=params)

    def run(img):
        out = eng(img)
        boxes = [] if out.boxes is None else list(out.boxes)
        return boxes, list(out.txts or [])
    return run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", default="legacy,v5_mobile,v5_server,v6_small,v6_medium")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--max_funsd", type=int, default=50)
    parser.add_argument("--handwritten_page", default=None, help="optional page to count detected lines on")
    parser.add_argument("--out", default=str(ROOT / "outputs" / "rapidocr_model_benchmark.json"))
    args = parser.parse_args()

    samples = load_samples(args.max_funsd)
    print(f"samples: {Counter(s[0] for s in samples)}")
    report = {}
    for name in args.configs.split(","):
        try:
            run = make_engine(name, args.threads)
            run(cv2.imread(samples[0][1]))  # warm-up / model download
        except Exception as e:
            print(f"{name}: unavailable ({str(e)[:160]})")
            continue
        per = {"funsd": [], "medical": []}
        times = []
        for kind, path, gt in samples:
            img = cv2.imread(path)
            t = time.time()
            _, txts = run(img)
            times.append(time.time() - t)
            per[kind].append(f1(words(gt), words(" ".join(txts)))[0])
        entry = {k: round(float(np.mean(v)), 4) for k, v in per.items() if v}
        entry["sec_per_page"] = round(float(np.mean(times)), 2)
        if args.handwritten_page:
            boxes, _ = run(cv2.imread(args.handwritten_page))
            entry["handwritten_page_boxes"] = len(boxes)
        report[name] = entry
        print(f"{name:10s} {entry}", flush=True)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
