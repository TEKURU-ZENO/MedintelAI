"""
Unified loaders for the handwriting-recognition (HTR) corpora used to fine-tune the medical TrOCR model.

Every loader returns a list of HTRSample records so the training script can mix sources freely:
  - iam_line      Teklia/IAM-line parquet (general English cursive lines)
  - rxhandbd      RxHandBD-ML word crops (Bangladeshi physician prescriptions: brands, generics, dosages)
  - kaggle_rx_bd  Doctors' Handwritten Prescription BD (Kaggle, 78 medicine classes) -- optional, manual download
  - chinmays_rx   Text-only corpus of medication lines parsed from chinmays18/medical-prescription-dataset

Run `python scripts/download_htr_datasets.py` first. Missing sources are skipped with a warning.
"""
import csv
import io
import json
import os
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPORA_DIR = ROOT / "datasets" / "htr_corpora"


@dataclass
class HTRSample:
    """One handwritten text image paired with its transcription."""
    text: str
    source: str
    split: str
    image_path: Optional[str] = None
    image_bytes: Optional[bytes] = field(default=None, repr=False)

    def load_bgr(self) -> np.ndarray:
        import cv2
        if self.image_bytes is not None:
            buf = np.frombuffer(self.image_bytes, dtype=np.uint8)
        else:
            # np.fromfile + imdecode handles non-ASCII Windows paths that cv2.imread cannot open
            buf = np.fromfile(self.image_path, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR) if buf.size else None
        if img is None:
            raise ValueError(f"Unreadable image for sample ({self.source}): {self.image_path or '<bytes>'}")
        return img


def normalize_label(text: str) -> str:
    """Collapses whitespace and unifies dashes/quotes so labels from different corpora agree."""
    if text is None:
        return ""
    t = str(text)
    t = t.replace("–", "-").replace("—", "-").replace("−", "-")
    t = t.replace("‘", "'").replace("’", "'").replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ---------------------------------------------------------------------------
# IAM-line (Teklia, parquet)
# ---------------------------------------------------------------------------
def load_iam_line(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[HTRSample]:
    base = Path(corpora_dir) / "iam_line"
    split_map = {"train": "train", "validation": "val", "test": "test"}
    samples: List[HTRSample] = []
    try:
        import pyarrow.parquet as pq
    except ImportError:
        print("[htr_corpora] pyarrow not installed; skipping IAM-line")
        return samples

    for fname, split in split_map.items():
        path = base / f"{fname}.parquet"
        if not path.exists():
            continue
        table = pq.read_table(path, columns=["image", "text"])
        images = table.column("image").to_pylist()
        texts = table.column("text").to_pylist()
        for img, text in zip(images, texts):
            raw = img.get("bytes") if isinstance(img, dict) else img
            label = normalize_label(text)
            if raw and label:
                samples.append(HTRSample(text=label, source="iam_line", split=split, image_bytes=raw))
    if not samples:
        print(f"[htr_corpora] IAM-line not found under {base}")
    return samples


# ---------------------------------------------------------------------------
# RxHandBD (Mendeley, word crops + Train_Label.csv / Test_Label.csv)
# ---------------------------------------------------------------------------
def _read_label_csv(csv_path: Path) -> List[Dict[str, str]]:
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_rxhandbd(
    corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR,
    val_fraction: float = 0.10,
    seed: int = 13,
    use_realigned: bool = True
) -> List[HTRSample]:
    """
    RxHandBD ships Train/Test only. A deterministic val split is carved from Train so the
    official Test split stays untouched for the final report.
    """
    base = Path(corpora_dir) / "rxhandbd"
    root = next((p.parent for p in base.rglob("Train_Label.csv")), None)
    if root is None:
        print(f"[htr_corpora] RxHandBD not found under {base}")
        return []

    # Row-offset repairs produced by scripts/repair_rxhandbd_labels.py (the published CSVs drift out of
    # sync with the image files). Set use_realigned=False to train / evaluate on the raw CSV labels.
    realigned: Dict[str, dict] = {}
    realigned_path = base / "labels_realigned.json"
    if use_realigned and realigned_path.exists():
        realigned = json.loads(realigned_path.read_text(encoding="utf-8")).get("labels", {})

    samples: List[HTRSample] = []
    for csv_name, img_dir, split in (("Train_Label.csv", "Train_Set", "train"), ("Test_Label.csv", "Test_Set", "test")):
        csv_path = root / csv_name
        if not csv_path.exists():
            continue
        rows = _read_label_csv(csv_path)
        for row in rows:
            fname = (row.get("Images") or row.get("Image") or "").strip()
            label = normalize_label(row.get("Text") or row.get("Label") or "")
            fix = realigned.get(f"{img_dir}/{fname}")
            if fix:
                label = fix["realigned"]
            img_path = root / img_dir / fname
            if fname and label and img_path.exists():
                samples.append(HTRSample(text=label, source="rxhandbd", split=split, image_path=str(img_path)))

    rng = random.Random(seed)
    train_idx = [i for i, s in enumerate(samples) if s.split == "train"]
    rng.shuffle(train_idx)
    for i in train_idx[: int(len(train_idx) * val_fraction)]:
        samples[i].split = "val"
    return samples


# ---------------------------------------------------------------------------
# Doctors' Handwritten Prescription BD (Kaggle) -- optional
# ---------------------------------------------------------------------------
def _kaggle_roots(corpora_dir: Path) -> List[Path]:
    """The Kaggle archive may live in htr_corpora/kaggle_rx_bd or be extracted directly under datasets/."""
    roots = [corpora_dir / "kaggle_rx_bd"]
    roots += [p for p in (ROOT / "datasets").iterdir() if p.is_dir() and "prescription bd" in p.name.lower()]
    return [r for r in roots if r.exists()]


def load_kaggle_rx_bd(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[HTRSample]:
    """
    Discovers every CSV with IMAGE + MEDICINE_NAME columns (the dataset's Training/Validation/Testing
    folders each carry one) and resolves images from the sibling *_words directory.
    """
    samples: List[HTRSample] = []
    csv_paths = [p for base in _kaggle_roots(Path(corpora_dir)) for p in base.rglob("*.csv")]
    for csv_path in csv_paths:
        rows = _read_label_csv(csv_path)
        if not rows or "IMAGE" not in rows[0] or "MEDICINE_NAME" not in rows[0]:
            continue
        lower = csv_path.name.lower()
        split = "val" if "valid" in lower else ("test" if "test" in lower else "train")
        image_dirs = [d for d in csv_path.parent.iterdir() if d.is_dir()] + [csv_path.parent]
        for row in rows:
            fname = row["IMAGE"].strip()
            label = normalize_label(row["MEDICINE_NAME"])
            img_path = next((d / fname for d in image_dirs if (d / fname).exists()), None)
            if img_path is not None and label:
                samples.append(HTRSample(text=label, source="kaggle_rx_bd", split=split, image_path=str(img_path)))

    if not samples:
        print("[htr_corpora] Kaggle prescription dataset not found (optional)")
    return samples


# ---------------------------------------------------------------------------
# GNHK (GoodNotes Handwriting Kollection): camera-captured real-world handwriting
# ---------------------------------------------------------------------------
GNHK_SPECIAL = re.compile(r"^%")  # %math%, %SC% (scribble), %NA% (illegible)


def _order_quad(pts: np.ndarray) -> np.ndarray:
    """Orders 4 points as top-left, top-right, bottom-right, bottom-left."""
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1).ravel()
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype=np.float32)


def _rectify(img: np.ndarray, quad: np.ndarray, pad_ratio: float = 0.12, max_height: int = 128) -> Optional[np.ndarray]:
    import cv2
    q = _order_quad(quad.astype(np.float32))
    w = int(max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3])))
    h = int(max(np.linalg.norm(q[3] - q[0]), np.linalg.norm(q[2] - q[1])))
    if w < 8 or h < 8:
        return None
    # Map the quad onto an inset rectangle; the margin around it is extrapolated by the perspective
    # transform so ascenders/descenders clipped by tight annotations survive.
    scale = min(1.0, max_height / float(h))
    sw, sh = w * scale, h * scale
    p = pad_ratio * sh
    dst = np.array([[p, p], [p + sw, p], [p + sw, p + sh], [p, p + sh]], dtype=np.float32)
    M = cv2.getPerspectiveTransform(q, dst)
    size = (int(round(sw + 2 * p)), int(round(sh + 2 * p)))
    return cv2.warpPerspective(img, M, size, flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)


def _find_gnhk_root(corpora_dir: Path) -> Optional[Path]:
    for cand in (Path(corpora_dir) / "gnhk", ROOT / "datasets" / "gnhk_dataset", ROOT / "datasets" / "gnhk"):
        if (cand / "train").is_dir():
            return cand
    return None


def build_gnhk_crops(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR, val_fraction: float = 0.08) -> Optional[Path]:
    """
    Extracts rectified line and word crops from GNHK page photos once into
    <corpora_dir>/gnhk_crops/{lines,words}/<split>/ with a labels.jsonl manifest.
    Validation pages are carved from train by page so no writer page leaks across splits.
    """
    import cv2
    import hashlib

    src = _find_gnhk_root(Path(corpora_dir))
    out = Path(corpora_dir) / "gnhk_crops"
    manifest = out / "labels.jsonl"
    if manifest.exists():
        return out
    if src is None:
        return None

    out.mkdir(parents=True, exist_ok=True)
    records = []
    for split_dir in ("train", "test"):
        for jpath in sorted((src / split_dir).glob("*.json")):
            img = cv2.imread(str(jpath.with_suffix(".jpg")), cv2.IMREAD_COLOR)
            if img is None:
                continue
            split = split_dir
            if split_dir == "train":
                bucket = int(hashlib.md5(jpath.stem.encode()).hexdigest(), 16) % 1000
                split = "val" if bucket < val_fraction * 1000 else "train"
            words = json.loads(jpath.read_text(encoding="utf-8"))
            by_line: Dict[int, List[dict]] = {}
            for wd in words:
                by_line.setdefault(wd.get("line_idx", -1), []).append(wd)

            for line_idx, items in by_line.items():
                quads = []
                for wd in items:
                    p = wd["polygon"]
                    quads.append(np.array([[p["x0"], p["y0"]], [p["x1"], p["y1"]], [p["x2"], p["y2"]], [p["x3"], p["y3"]]], dtype=np.float32))
                # Word crops (skip special tokens)
                for wd, q in zip(items, quads):
                    text = normalize_label(wd["text"])
                    if not text or GNHK_SPECIAL.match(text):
                        continue
                    crop = _rectify(img, q)
                    if crop is None:
                        continue
                    rel = f"words/{split}/{jpath.stem}_{line_idx}_{len(records)}.png"
                    (out / rel).parent.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(out / rel), crop)
                    records.append({"path": rel, "text": text, "split": split, "kind": "word"})
                # Line crops: only lines whose every word is transcribable
                texts = [normalize_label(wd["text"]) for wd in items]
                if line_idx < 0 or any(not t or GNHK_SPECIAL.match(t) for t in texts):
                    continue
                order = np.argsort([q[:, 0].mean() for q in quads])
                line_text = " ".join(texts[i] for i in order)
                rect = cv2.minAreaRect(np.concatenate(quads))
                crop = _rectify(img, cv2.boxPoints(rect))
                if crop is None or crop.shape[1] < crop.shape[0]:
                    continue
                rel = f"lines/{split}/{jpath.stem}_{line_idx}.png"
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(out / rel), crop)
                records.append({"path": rel, "text": line_text, "split": split, "kind": "line"})

    with open(manifest, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return out


def load_gnhk(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[HTRSample]:
    """GNHK line crops (source 'gnhk_line') and word crops (source 'gnhk_word')."""
    out = build_gnhk_crops(corpora_dir)
    if out is None:
        print("[htr_corpora] GNHK not found (expected datasets/gnhk_dataset/{train,test})")
        return []
    samples: List[HTRSample] = []
    with open(out / "labels.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            samples.append(HTRSample(
                text=r["text"], source=f"gnhk_{r['kind']}", split=r["split"], image_path=str(out / r["path"])
            ))
    return samples


# ---------------------------------------------------------------------------
# Drug-name lexicon sources
# ---------------------------------------------------------------------------
def load_rxnorm_names(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[str]:
    """Ingredient (IN/PIN) and brand (BN) names from RxNorm Current Prescribable Content."""
    path = Path(corpora_dir) / "rxnorm" / "RXNCONSO.RRF"
    if not path.exists():
        return []
    names = set()
    with open(path, "r", encoding="utf-8") as f:
        for row in f:
            cols = row.split("|")
            if len(cols) > 14 and cols[11] == "RXNORM" and cols[12] in ("IN", "PIN", "BN"):
                name = cols[14].strip()
                if 3 <= len(name) <= 40:
                    names.add(name)
    return sorted(names)


def load_kaggle_generic_names(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[str]:
    names = set()
    for base in _kaggle_roots(Path(corpora_dir)):
        for csv_path in base.rglob("*.csv"):
            for row in _read_label_csv(csv_path):
                g = normalize_label(row.get("GENERIC_NAME", ""))
                if g:
                    names.add(g)
    return sorted(names)


# ---------------------------------------------------------------------------
# Text-only medication corpus (chinmays18 annotations)
# ---------------------------------------------------------------------------
def load_medication_text_corpus(corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR) -> List[str]:
    """
    Parses the Donut-style ground-truth strings into individual medication lines such as
    'Prednisone 25 mg - After meals'. Used to render synthetic medical handwriting lines.
    """
    base = Path(corpora_dir) / "chinmays_rx" / "annotations"
    lines: List[str] = []
    if not base.exists():
        return lines
    for path in base.rglob("*.json"):
        try:
            gt = json.loads(path.read_text(encoding="utf-8")).get("ground_truth", "")
        except Exception:
            continue
        meds = re.search(r"medications:\s*(.*?)\s*(?:signature:|</s>|$)", gt)
        if not meds:
            continue
        # Items alternate "<Drug> <dose>" and "<instruction>"; pair them into one medication line
        current = None
        for item in re.split(r"\s+-\s+(?=[A-Z0-9])", " " + meds.group(1)):
            item = normalize_label(item.lstrip("- ").strip())
            if not item:
                continue
            if re.search(r"\d\s*(?:mg|mcg|ml|g|iu)\b", item, flags=re.IGNORECASE) or current is None:
                if current:
                    lines.append(current)
                current = item
            else:
                current = f"{current} - {item}"
        if current:
            lines.append(current)
    lines = [l for l in lines if 3 <= len(l) <= 64]
    return sorted(set(lines))


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------
IMAGE_LOADERS = {
    "iam_line": load_iam_line,
    "rxhandbd": load_rxhandbd,
    "kaggle_rx_bd": load_kaggle_rx_bd,
    "gnhk": load_gnhk,
}

# Sources that are general English handwriting (excluded from the medical lexicon / medical score)
GENERAL_SOURCES = ("iam_line", "gnhk_line", "gnhk_word")


def load_all_image_corpora(
    corpora_dir: Union[str, Path] = DEFAULT_CORPORA_DIR,
    sources: Optional[List[str]] = None
) -> Dict[str, List[HTRSample]]:
    """Returns {source_name: [HTRSample, ...]} for every requested source that is present on disk."""
    out: Dict[str, List[HTRSample]] = {}
    for name, loader in IMAGE_LOADERS.items():
        if sources and name not in sources:
            continue
        for s in loader(corpora_dir):
            out.setdefault(s.source, []).append(s)
    return out


def build_medical_lexicon(
    corpora: Dict[str, List[HTRSample]],
    extra_terms: Optional[List[str]] = None,
    min_len: int = 4
) -> List[str]:
    """
    Builds the drug / clinical term lexicon shipped next to the model weights. Only alphabetic tokens
    from the medical corpora are kept (IAM is general English and is excluded).
    """
    counts: Dict[str, int] = {}
    canonical: Dict[str, str] = {}
    for source, items in corpora.items():
        if source in GENERAL_SOURCES:
            continue
        for s in items:
            for tok in re.findall(r"[A-Za-z][A-Za-z\-]+", s.text):
                key = tok.lower()
                if len(key) < min_len:
                    continue
                counts[key] = counts.get(key, 0) + 1
                # Prefer the capitalised spelling as the canonical form
                if key not in canonical or (tok[0].isupper() and not canonical[key][0].isupper()):
                    canonical[key] = tok
    for term in extra_terms or []:
        for tok in re.findall(r"[A-Za-z][A-Za-z\-]+", term):
            if len(tok) >= min_len:
                canonical.setdefault(tok.lower(), tok)
    return sorted(canonical.values(), key=str.lower)


def summarize(corpora: Dict[str, List[HTRSample]]) -> Dict[str, Dict[str, int]]:
    summary: Dict[str, Dict[str, int]] = {}
    for name, items in corpora.items():
        per_split: Dict[str, int] = {}
        for s in items:
            per_split[s.split] = per_split.get(s.split, 0) + 1
        summary[name] = per_split
    return summary


if __name__ == "__main__":
    corpora = load_all_image_corpora()
    print(json.dumps(summarize(corpora), indent=2))
    print(f"Medication text lines: {len(load_medication_text_corpus())}")
