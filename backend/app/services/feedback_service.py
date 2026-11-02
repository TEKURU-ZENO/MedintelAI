"""
Clinician-correction feedback store: turns corrections made in the OCR studio into handwriting training data.

Opt-in (OCR_FEEDBACK_DATASET=1) because it keeps page images of patient documents on this machine. When enabled:
  - every extraction stores its page images and block boxes (latest MAX_DOCUMENTS documents)
  - a saved correction is aligned line-by-line with the extracted text; each corrected line that maps to a single
    block becomes a training pair (page image region, corrected text) in manifest.jsonl
datasets/htr_sources.load_feedback() reads the manifest, so scripts/train_trocr_medical.py picks the pairs up as
the "feedback" source. Storage: OCR_FEEDBACK_DIR (default <repo>/datasets/htr_corpora/feedback, git-ignored).
"""
import difflib
import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from app.core.logging import logger

MAX_DOCUMENTS = 200
_lock = threading.Lock()


def _enabled() -> bool:
    return os.getenv("OCR_FEEDBACK_DATASET", "0") == "1"


def _root() -> Path:
    env = os.getenv("OCR_FEEDBACK_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "datasets" / "htr_corpora" / "feedback"


def _index_path() -> Path:
    return _root() / "extractions.json"


def _load_index() -> Dict[str, Any]:
    try:
        return json.loads(_index_path().read_text(encoding="utf-8"))
    except Exception:
        return {}


def record_extraction(document: str, page_images: List[Any], blocks: List[Dict[str, Any]]) -> None:
    if not _enabled() or not page_images:
        return
    try:
        with _lock:
            root = _root()
            (root / "pages").mkdir(parents=True, exist_ok=True)
            stamp = hashlib.sha1(f"{document}-{time.time()}".encode()).hexdigest()[:16]
            pages = []
            for n, img in enumerate(page_images, 1):
                rel = f"pages/{stamp}_p{n}.png"
                cv2.imwrite(str(root / rel), img)
                pages.append(rel)
            index = _load_index()
            index[document] = {
                "stamp": stamp, "pages": pages, "time": time.time(),
                "blocks": [{"id": b.get("id"), "page": b.get("page", 1), "text": b.get("text", ""),
                            "bbox": b.get("bbox"), "source": b.get("source"), "line_number": b.get("line_number")}
                           for b in blocks],
            }
            if len(index) > MAX_DOCUMENTS:
                for name, _ in sorted(index.items(), key=lambda kv: kv[1].get("time", 0))[: len(index) - MAX_DOCUMENTS]:
                    del index[name]
            _index_path().write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Could not store extraction for feedback: {exc}")


def record_correction(document: str, original_text: str, corrected_text: str, block_id: Optional[str] = None) -> int:
    """Returns the number of training pairs written."""
    if not _enabled():
        return 0
    try:
        with _lock:
            entry = _load_index().get(document)
            if not entry:
                return 0
            blocks = entry["blocks"]
            pairs = []
            if block_id:
                match = [b for b in blocks if b.get("id") == block_id]
                if match and corrected_text.strip():
                    pairs.append((match[0], corrected_text.strip()))
            else:
                orig_lines = [l.strip() for l in original_text.splitlines()]
                corr_lines = [l.strip() for l in corrected_text.splitlines()]
                sm = difflib.SequenceMatcher(a=orig_lines, b=corr_lines, autojunk=False)
                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if tag != "replace" or (i2 - i1) != (j2 - j1):
                        continue  # only line-for-line edits can be tied to an image region
                    for o, c in zip(orig_lines[i1:i2], corr_lines[j1:j2]):
                        match = [b for b in blocks if b.get("text", "").strip() == o]
                        if len(match) == 1 and c:
                            pairs.append((match[0], c))
            if not pairs:
                return 0
            root = _root()
            with open(root / "manifest.jsonl", "a", encoding="utf-8") as f:
                for block, text in pairs:
                    page = entry["pages"][max(0, int(block.get("page") or 1) - 1)]
                    f.write(json.dumps({"page_image": page, "bbox": block["bbox"], "text": text,
                                        "ocr_text": block.get("text", ""), "document": entry["stamp"],
                                        "source_kind": block.get("source"), "time": time.time()},
                                       ensure_ascii=False) + "\n")
            return len(pairs)
    except Exception as exc:
        logger.warning(f"Could not record correction for feedback: {exc}")
        return 0
