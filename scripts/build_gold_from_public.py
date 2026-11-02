"""
Adds public, labelled document pages to the gold evaluation set (datasets/gold/), next to the hand-labelled
pages. Each source is evaluated as a full page through the real pipeline (scripts: backend/scripts/evaluate_gold.py).

  gnhk_*     GNHK test pages (GoodNotes, CC-BY-4.0): real phone photos of handwriting; lines rebuilt from
             word polygons (lines containing %math% / %SC% / %NA% tokens are excluded)
  funsd_*    FUNSD test forms: real noisy scanned forms; one gold "line" per annotated entity
  rxsynth_*  chinmays18/medical-prescription-dataset test pages: synthetic cursive prescriptions with patient /
             medication fields (template text rebuilt from the annotation)

Usage:
    python scripts/build_gold_from_public.py --gnhk 20 --funsd 15 --rx 20
"""
import argparse
import json
import random
import re
import shutil
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "datasets" / "gold"
IMAGES = GOLD / "images" / "public"
CHINMAYS = "chinmays18/medical-prescription-dataset"


def gnhk_pages(n, rng):
    src = ROOT / "datasets" / "gnhk_dataset" / "test"
    pages = sorted(src.glob("*.json"))
    rng.shuffle(pages)
    made = 0
    for jp in pages:
        words = json.loads(jp.read_text(encoding="utf-8"))
        by_line = {}
        for w in words:
            by_line.setdefault(w.get("line_idx", -1), []).append(w)
        lines = []
        for idx in sorted(k for k in by_line if k >= 0):
            ws = sorted(by_line[idx], key=lambda w: min(w["polygon"][f"x{i}"] for i in range(4)))
            texts = [w["text"] for w in ws]
            if any(t.startswith("%") for t in texts):
                continue  # math / scribble / illegible: no reliable transcription
            ys = [w["polygon"][f"y{i}"] for w in ws for i in range(4)]
            lines.append((sum(ys) / len(ys), " ".join(texts)))
        if len(lines) < 4:
            continue
        lines.sort()
        name = f"gnhk_{jp.stem}"
        dst = IMAGES / f"{name}.jpg"
        shutil.copy(jp.with_suffix(".jpg"), dst)
        gold = {"image": f"images/public/{dst.name}", "doc_type": "handwritten_note", "handwritten": True,
                "source": "GNHK test split (GoodNotes, CC-BY-4.0)", "lines": [{"text": t, "role": "body"} for _, t in lines],
                "fields": {}}
        (GOLD / f"{name}.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False), encoding="utf-8")
        made += 1
        if made >= n:
            break
    return made


def funsd_pages(n, rng):
    src = ROOT / "datasets" / "report dataset" / "testing_data"
    anns = sorted((src / "annotations").glob("*.json"))
    rng.shuffle(anns)
    made = 0
    for ap in anns[:n]:
        form = json.loads(ap.read_text(encoding="utf-8")).get("form", [])
        entities = [(e["box"][1], e["box"][0], e["text"].strip()) for e in form if e.get("text", "").strip()]
        entities.sort()
        name = f"funsd_{ap.stem}"
        dst = IMAGES / f"{name}.png"
        shutil.copy(src / "images" / f"{ap.stem}.png", dst)
        gold = {"image": f"images/public/{dst.name}", "doc_type": "scanned_form", "handwritten": False,
                "source": "FUNSD test split (research use)", "lines": [{"text": t, "role": "body"} for _, _, t in entities],
                "fields": {}, "notes": "One gold line per FUNSD entity; question/answer pairs on one row are separate lines."}
        (GOLD / f"{name}.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False), encoding="utf-8")
        made += 1
    return made


def parse_chinmays(gt):
    def grab(key, nxt):
        m = re.search(rf"{key}:\s*(.*?)\s*(?:{nxt}:|</s>|$)", gt)
        return m.group(1).strip() if m else ""
    fields = {
        "doctor": grab("doctor_name", "clinic_name"), "clinic": grab("clinic_name", "clinic_address"),
        "address": grab("clinic_address", "patient_name"), "patient": grab("patient_name", "patient_age"),
        "age": grab("patient_age", "date"), "date": grab("date", "medications"),
    }
    meds_raw = grab("medications", "signature")
    meds, current = [], None
    for item in re.split(r"\s+-\s+(?=[A-Z0-9])", " " + meds_raw):
        item = item.lstrip("- ").strip()
        if not item:
            continue
        m = re.match(r"^([A-Za-z][A-Za-z\-]+)\s+(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu))$", item, flags=re.IGNORECASE)
        if m:
            current = {"drug": m.group(1), "strength": m.group(2).replace(" ", ""), "instruction": ""}
            meds.append(current)
        elif current is not None:
            current["instruction"] = item
    return fields, meds


def rx_pages(n, rng):
    ann_dir = ROOT / "datasets" / "htr_corpora" / "chinmays_rx" / "annotations" / "test"
    anns = sorted(ann_dir.glob("*.json"))
    rng.shuffle(anns)
    made = 0
    for ap in anns:
        gt = json.loads(ap.read_text(encoding="utf-8")).get("ground_truth", "")
        f, meds = parse_chinmays(gt)
        if not meds or not f["patient"]:
            continue
        name = f"rxsynth_{ap.stem}"
        dst = IMAGES / f"{name}.png"
        if not dst.exists():
            url = f"https://huggingface.co/datasets/{CHINMAYS}/resolve/main/test/images/{ap.stem}.png"
            with urllib.request.urlopen(url) as resp:
                dst.write_bytes(resp.read())
        lines = [f["clinic"], f["address"], f"Prescribed by: {f['doctor']}", f"Date: {f['date']}",
                 f"Patient: {f['patient']}, Age: {f['age']}"]
        lines += [f"{m['drug']} {m['strength'].replace('mg', ' mg')} - {m['instruction']}".rstrip(" -") for m in meds]
        gold = {"image": f"images/public/{dst.name}", "doc_type": "prescription", "handwritten": True,
                "source": "chinmays18/medical-prescription-dataset test split (synthetic cursive)",
                "lines": [{"text": t, "role": "body"} for t in lines if t] +
                         [{"text": "Signature:", "role": "body"}, {"text": f["doctor"], "role": "signature"}],
                "fields": {"patient_name": f["patient"], "age": f["age"], "date": f["date"],
                           "medications": [{"drug": m["drug"], "strength": m["strength"], "timing": m["instruction"]} for m in meds]},
                "notes": "Line text rebuilt from the dataset's structured annotation and its fixed page template."}
        (GOLD / f"{name}.json").write_text(json.dumps(gold, indent=1, ensure_ascii=False), encoding="utf-8")
        made += 1
        if made >= n:
            break
    return made


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gnhk", type=int, default=20)
    parser.add_argument("--funsd", type=int, default=15)
    parser.add_argument("--rx", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    IMAGES.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    print("gnhk", gnhk_pages(args.gnhk, rng))
    print("funsd", funsd_pages(args.funsd, rng))
    print("rx", rx_pages(args.rx, rng))


if __name__ == "__main__":
    main()
