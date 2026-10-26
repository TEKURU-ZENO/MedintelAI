"""
Collects PP-OCR and TrOCR readings of the same crops so the ensemble selection rule in
app/ai/ocr/htr_ensemble.py can be fitted on validation data and checked on test data.

Sources:
  handwriting  gnhk_line, iam_line, rxhandbd, kaggle_rx_bd (corpus splits)
  printed      funsd_word   word crops from FUNSD scanned forms (training_data for val, testing_data for test)
               printed_synth clinical / general lines rendered in standard print fonts with scan noise

Usage:
    python scripts/collect_ensemble_candidates.py --split val --per_source 200 --out outputs/ensemble_val.json
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from datasets.htr_sources import load_all_image_corpora  # noqa: E402
from app.ai.ocr.htr_engine import MedicalHTREngine  # noqa: E402
from app.ai.ocr.rapid_adapter import create_rapid_ocr  # noqa: E402

PRINT_FONTS = ["arial.ttf", "times.ttf", "calibri.ttf", "segoeui.ttf", "verdana.ttf", "consola.ttf", "tahoma.ttf"]


def funsd_words(split: str, n: int, rng: random.Random):
    folder = ROOT / "datasets" / "report dataset" / ("training_data" if split == "val" else "testing_data")
    items = []
    for ann in sorted((folder / "annotations").glob("*.json")):
        img_path = folder / "images" / (ann.stem + ".png")
        if not img_path.exists():
            continue
        for f in json.loads(ann.read_text(encoding="utf-8")).get("form", []):
            for w in f.get("words", []):
                t = w.get("text", "").strip()
                x0, y0, x1, y1 = w["box"]
                if len(t) >= 3 and x1 - x0 > 8 and y1 - y0 > 8:
                    items.append((str(img_path), (x0, y0, x1, y1), t))
    rng.shuffle(items)
    out = []
    cache = {}
    for path, (x0, y0, x1, y1), t in items[:n]:
        img = cache.setdefault(path, cv2.imread(path))
        pad = max(2, (y1 - y0) // 6)
        crop = img[max(0, y0 - pad): y1 + pad, max(0, x0 - pad): x1 + pad]
        if crop.size:
            out.append((crop, t))
    return out


def printed_synth(texts, n: int, rng: random.Random):
    fonts_dir = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    fonts = [os.path.join(fonts_dir, f) for f in PRINT_FONTS if os.path.exists(os.path.join(fonts_dir, f))]
    out = []
    for _ in range(n):
        text = rng.choice(texts)
        font = ImageFont.truetype(rng.choice(fonts), rng.randint(16, 34))
        l, t, r, b = font.getbbox(text)
        img = Image.new("RGB", (r - l + 20, b - t + 14), (rng.randint(235, 255),) * 3)
        ImageDraw.Draw(img).text((10 - l, 7 - t), text, font=font, fill=(rng.randint(0, 60),) * 3)
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        if rng.random() < 0.5:
            arr = cv2.GaussianBlur(arr, (3, 3), rng.uniform(0.3, 0.9))
        if rng.random() < 0.5:
            arr = np.clip(arr + np.random.normal(0, rng.uniform(2, 8), arr.shape), 0, 255).astype(np.uint8)
        out.append((arr, text))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="val")
    parser.add_argument("--per_source", type=int, default=200)
    parser.add_argument("--sources", default="gnhk_line,iam_line,rxhandbd,kaggle_rx_bd,funsd_word,printed_synth")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--out", required=True)
    parser.add_argument("--append_to", default=None, help="reuse rows from an earlier run for sources already present")
    args = parser.parse_args()

    rows = []
    if args.append_to and Path(args.append_to).exists():
        rows = json.loads(Path(args.append_to).read_text(encoding="utf-8"))
    done = {r["source"] for r in rows}

    corpora = load_all_image_corpora()
    rng = random.Random(7 if args.split == "val" else 11)
    rapid = create_rapid_ocr()
    htr = MedicalHTREngine.from_pretrained(str(ROOT / "app" / "ai" / "models" / "trocr_medical_finetuned"),
                                           device=args.device)
    synth_texts = sorted({s.text for name in ("iam_line", "rxhandbd") for s in corpora.get(name, [])
                          if s.split == "train" and 3 <= len(s.text) <= 60})
    t0 = time.time()
    for src in args.sources.split(","):
        if src in done:
            continue
        if src == "funsd_word":
            pairs = funsd_words(args.split, args.per_source, rng)
        elif src == "printed_synth":
            pairs = printed_synth(synth_texts, args.per_source, rng)
        else:
            pool = [s for s in corpora.get(src, []) if s.split == args.split]
            rng.shuffle(pool)
            pairs = [(s.load_bgr(), s.text) for s in pool[: args.per_source]]
        for img, gt in pairs:
            rec, _ = rapid.text_recognizer([img])
            rt, rc = rec[0] if rec else ("", 0.0)
            h = htr.recognize_detailed(img)
            rows.append({
                "source": src, "gt": gt,
                "rapid_text": rt, "rapid_conf": rc,
                "trocr_text": h["text"], "trocr_conf": h["confidence"],
                "rapid_validity": htr.word_validity(rt), "trocr_validity": htr.word_validity(h["text"]),
            })
        print(f"{src}: {len(rows)} rows, {time.time() - t0:.0f}s", flush=True)
    Path(args.out).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
