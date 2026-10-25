"""
Downloads the public handwriting (HTR) corpora used to fine-tune the medical TrOCR model.

Sources (all written under datasets/htr_corpora/ which is git-ignored):
  - iam_line/       Teklia/IAM-line (Hugging Face, parquet, 10,373 handwritten English lines)
  - rxhandbd/       RxHandBD-ML.zip (Mendeley Data, 5,578 handwritten prescription word crops)
  - chinmays_rx/    chinmays18/medical-prescription-dataset annotations only (used as a text corpus
                    for synthetic medical lines; page images carry no line boxes so they are skipped)
  - rxnorm/         RxNorm Current Prescribable Content (NLM, no licence needed): drug ingredient and
                    brand names for the medical lexicon
  - fonts/          OFL handwriting fonts from google/fonts for synthetic prescription lines
  - kaggle_rx_bd/   Doctors' Handwritten Prescription BD (Kaggle) -- requires a Kaggle login, so it is
                    NOT downloaded here. Download it manually from
                    https://www.kaggle.com/datasets/mamun1113/doctors-handwritten-prescription-bd-dataset
                    and extract the archive into this folder; the loader discovers its CSVs recursively.

Usage:
    python scripts/download_htr_datasets.py            # download everything that is public
    python scripts/download_htr_datasets.py --only iam
"""
import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPORA_DIR = ROOT / "datasets" / "htr_corpora"

IAM_FILES = {
    split: f"https://huggingface.co/datasets/Teklia/IAM-line/resolve/main/data/{split}.parquet"
    for split in ("train", "validation", "test")
}
RXHANDBD_URL = (
    "https://data.mendeley.com/public-files/datasets/dsb5r6vskg/files/"
    "98acd360-ba4c-45d0-b614-5d66f4deee47/file_downloaded"
)
RXHANDBD_SHA256 = "c6371c0a3a89301c0b6b2eac1d2d49f6f3d8e559a7a71b338655dde0a6a63b51"
CHINMAYS_REPO = "chinmays18/medical-prescription-dataset"
RXNORM_URL = "https://download.nlm.nih.gov/rxnorm/RxNorm_full_prescribe_current.zip"


def _download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"  [skip] {dest.name} already present")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    print(f"  [get ] {url}")
    with urllib.request.urlopen(url) as resp, open(tmp, "wb") as f:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    tmp.replace(dest)
    return dest


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(zip_path: Path, out_dir: Path):
    """Extracts a zip while refusing entries that escape out_dir (zip-slip)."""
    out_dir = out_dir.resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (out_dir / member.filename).resolve()
            if not str(target).startswith(str(out_dir)):
                raise RuntimeError(f"Unsafe path in archive: {member.filename}")
        zf.extractall(out_dir)


def download_iam(corpora_dir: Path):
    print("IAM-line (Teklia/IAM-line)")
    for split, url in IAM_FILES.items():
        _download(url, corpora_dir / "iam_line" / f"{split}.parquet")


def download_rxhandbd(corpora_dir: Path):
    print("RxHandBD (Mendeley Data, RxHandBD-ML.zip)")
    target_dir = corpora_dir / "rxhandbd"
    zip_path = _download(RXHANDBD_URL, target_dir / "RxHandBD-ML.zip")
    digest = _sha256(zip_path)
    if digest != RXHANDBD_SHA256:
        raise RuntimeError(f"RxHandBD checksum mismatch: {digest}")
    marker = target_dir / ".extracted"
    if not marker.exists():
        print("  [unzip] RxHandBD-ML.zip")
        _safe_extract(zip_path, target_dir)
        marker.write_text("ok")


def download_chinmays_annotations(corpora_dir: Path):
    print(f"Medical prescription text corpus ({CHINMAYS_REPO}, annotations only)")
    out_dir = corpora_dir / "chinmays_rx" / "annotations"
    out_dir.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val", "test"):
        api = f"https://huggingface.co/api/datasets/{CHINMAYS_REPO}/tree/main/{split}/annotations"
        with urllib.request.urlopen(api) as resp:
            entries = json.loads(resp.read().decode("utf-8"))
        files = [e["path"] for e in entries if e.get("type") == "file" and e["path"].endswith(".json")]
        fetched = 0
        for rel in files:
            dest = out_dir / split / Path(rel).name
            if dest.exists():
                continue
            url = f"https://huggingface.co/datasets/{CHINMAYS_REPO}/resolve/main/{rel}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(url) as resp:
                dest.write_bytes(resp.read())
            fetched += 1
        print(f"  {split}: {len(files)} annotations ({fetched} new)")


def download_rxnorm(corpora_dir: Path):
    """RxNorm Current Prescribable Content (no UMLS licence needed): ingredient + brand names for the lexicon."""
    print("RxNorm Current Prescribable Content (NLM)")
    target_dir = corpora_dir / "rxnorm"
    zip_path = _download(RXNORM_URL, target_dir / "RxNorm_full_prescribe_current.zip")
    out = target_dir / "RXNCONSO.RRF"
    if not out.exists():
        with zipfile.ZipFile(zip_path) as zf:
            member = next(m for m in zf.namelist() if m.endswith("rrf/RXNCONSO.RRF"))
            out.write_bytes(zf.read(member))
        print("  [unzip] RXNCONSO.RRF")


GOOGLE_HANDWRITING_FONTS = [
    "caveat", "indieflower", "shadowsintolight", "patrickhand", "kalam", "gloriahallelujah", "reeniebeanie",
    "nothingyoucoulddo", "handlee", "coveredbyyourgrace", "architectsdaughter", "homemadeapple", "rocksalt",
    "dawningofanewday", "labelleaurore", "zeyada", "waitingforthesunrise", "justanotherhand", "overtherainbow",
    "gochihand", "schoolbell", "sueellenfrancisco", "kristi", "nanumpenscript", "cedarvillecursive",
    "mrsaintdelafield", "marckscript", "neucha", "shadowsintolighttwo", "yellowtail", "nothingyoucoulddo",
    "loversquarrel", "liukeyandrew", "comingsoon", "annieuseyourtelescope", "delius", "itim", "sriracha",
]


def download_fonts(corpora_dir: Path):
    """OFL-licensed handwriting fonts from the google/fonts repository, for synthetic line rendering."""
    print("Handwriting fonts (google/fonts, OFL)")
    out_dir = corpora_dir / "fonts"
    out_dir.mkdir(parents=True, exist_ok=True)
    got = 0
    for family in sorted(set(GOOGLE_HANDWRITING_FONTS)):
        if any(out_dir.glob(f"{family}__*.ttf")):
            got += 1
            continue
        try:
            with urllib.request.urlopen(f"https://api.github.com/repos/google/fonts/contents/ofl/{family}") as resp:
                entries = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
        ttfs = [e for e in entries if e.get("name", "").lower().endswith(".ttf")]
        regular = [e for e in ttfs if "regular" in e["name"].lower() or "[" in e["name"]] or ttfs
        if not regular:
            continue
        e = regular[0]
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", e["name"])
        _download(e["download_url"], out_dir / f"{family}__{safe}")
        got += 1
    print(f"  {got} font families available")


def main():
    parser = argparse.ArgumentParser(description="Download public HTR corpora for medical TrOCR training")
    parser.add_argument("--corpora_dir", type=str, default=str(DEFAULT_CORPORA_DIR))
    parser.add_argument("--only", choices=["iam", "rxhandbd", "chinmays", "rxnorm", "fonts"], default=None)
    args = parser.parse_args()

    corpora_dir = Path(args.corpora_dir)
    corpora_dir.mkdir(parents=True, exist_ok=True)
    (corpora_dir / "kaggle_rx_bd").mkdir(exist_ok=True)

    steps = {
        "iam": download_iam,
        "rxhandbd": download_rxhandbd,
        "chinmays": download_chinmays_annotations,
        "rxnorm": download_rxnorm,
        "fonts": download_fonts,
    }
    for name, fn in steps.items():
        if args.only and args.only != name:
            continue
        try:
            fn(corpora_dir)
        except Exception as e:
            print(f"  [fail] {name}: {e}", file=sys.stderr)

    print("\nKaggle 'Doctors Handwritten Prescription BD' must be downloaded manually into:")
    print(f"  {corpora_dir / 'kaggle_rx_bd'}")


if __name__ == "__main__":
    main()
