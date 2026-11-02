"""
Document layout analysis for handwritten and mixed medical pages.

Recognition quality is limited as much by layout as by reading: on a prescription a braced margin note such as
"after meals" fuses into the medicine line next to it ("aftes Tab. Augmentin ..."), and a doctor's signature is
read as a word. This module:

  find_separators()      tall, thin ink strokes (braces "{", brackets, vertical bars) that separate a margin
                         note from the lines it applies to; used by the line builder to avoid merging across them
  DocumentLayoutAnalyzer annotates recognised blocks with a role:
                           margin_note  short text on the far side of a separator; `applies_to` lists the body
                                        lines the separator spans, and it is ordered just before them
                           signature    short, low-confidence handwriting with no real words in the lower page,
                                        or the handwriting next to a "Signature" label; text becomes
                                        "[signature]" with the reading kept in `raw_text`
                           header / footer / body by position
"""
import difflib
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np

Separator = Tuple[float, float, float, float]  # x0, y0, x1, y1


def find_separators(image: np.ndarray, line_height: float,
                    text_boxes: Sequence[Sequence[float]] = ()) -> List[Separator]:
    """
    Tall thin ink components: height >= 1.6 line heights, narrow relative to their height, sparse (a curve or
    bar, not a word), and shorter than 60% of the page (full-height ruled margins are page furniture).
    """
    if image is None or image.size == 0 or line_height <= 0:
        return []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    H, W = gray.shape[:2]
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,
                                   max(15, int(line_height) | 1), 15)
    n, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    seps = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if h < 1.6 * line_height or h > 0.6 * H or w < 2:
            continue
        if w > 0.45 * h:
            continue  # wide: a word or drawing, not a brace
        if area / float(w * h) > 0.35:
            continue  # solid: a blot or thick bar, not a thin stroke
        seps.append((float(x), float(y), float(x + w), float(y + h)))
    return seps


def separator_between(sep: Separator, left_box, right_box) -> bool:
    """True when the separator lies in the horizontal gap between two boxes and shares their rows."""
    sx0, sy0, sx1, sy1 = sep
    lx1 = left_box[2]
    rx0 = right_box[0]
    if not (lx1 - 0.5 * (sx1 - sx0) <= (sx0 + sx1) / 2 <= rx0 + 0.5 * (sx1 - sx0)):
        return False
    top = min(left_box[1], right_box[1])
    bottom = max(left_box[3], right_box[3])
    return min(sy1, bottom) - max(sy0, top) > 0


class DocumentLayoutAnalyzer:
    def __init__(self, validity: Optional[Callable[[str], float]] = None):
        self.validity = validity or (lambda _t: 1.0)

    @staticmethod
    def _line_height(blocks: List[Dict]) -> float:
        hs = sorted(b["bbox"][3] - b["bbox"][1] for b in blocks if b.get("bbox"))
        return float(hs[len(hs) // 2]) if hs else 0.0

    def annotate(self, blocks: List[Dict], image: np.ndarray, separators: Optional[List[Separator]] = None) -> List[Dict]:
        if not blocks or image is None:
            return blocks
        H, W = image.shape[:2]
        line_h = self._line_height(blocks)
        if separators is None:
            separators = find_separators(image, line_h)

        for idx, b in enumerate(blocks):
            b.setdefault("role", "body")
            b["layout_uid"] = idx

        self._mark_margin_notes(blocks, separators, line_h)
        self._mark_signatures(blocks, H)
        for b in blocks:
            if b["role"] != "body":
                continue
            x0, y0, x1, y1 = b["bbox"]
            if y1 <= 0.12 * H and b.get("source") == "printed":
                b["role"] = "header"
            elif y0 >= 0.92 * H:
                b["role"] = "footer"
        return blocks

    def _mark_margin_notes(self, blocks: List[Dict], separators: List[Separator], line_h: float):
        for sep in separators:
            sx0, sy0, sx1, sy1 = sep
            cx = (sx0 + sx1) / 2
            band = lambda b: min(b["bbox"][3], sy1) - max(b["bbox"][1], sy0)
            left = [b for b in blocks if b["bbox"][2] <= cx + line_h * 0.3 and band(b) > 0]
            right = [b for b in blocks if b["bbox"][0] >= cx - line_h * 0.3 and band(b) > 0.3 * (b["bbox"][3] - b["bbox"][1])]
            if not left or not right:
                continue
            # The note is the short text immediately left of the separator, inside its vertical span
            notes = [b for b in left if len(b.get("text", "").split()) <= 3
                     and sy0 - line_h <= (b["bbox"][1] + b["bbox"][3]) / 2 <= sy1 + line_h
                     and cx - b["bbox"][2] <= 3 * line_h]
            if not notes:
                continue
            scope = sorted(right, key=lambda b: b["bbox"][1])
            top = min(b["bbox"][1] for b in scope)
            for k, note in enumerate(sorted(notes, key=lambda b: b["bbox"][1])):
                note["role"] = "margin_note"
                note["applies_to_uids"] = [b["layout_uid"] for b in scope]
                # Ordered as its own line just before the lines it governs (never fused into one of them)
                note["_line_band"] = [top - 3.0 + 0.1 * k, top - 2.0 + 0.1 * k]

    def _mark_signatures(self, blocks: List[Dict], H: int):
        by_row = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        for i, b in enumerate(by_row):
            if b["role"] != "body":
                continue
            text = b.get("text", "")
            words = text.split()
            labelled = False
            prev = by_row[i - 1] if i > 0 else None
            if prev is not None and prev.get("text", "").strip().lower().rstrip(":").endswith("signature"):
                same_row = min(prev["bbox"][3], b["bbox"][3]) - max(prev["bbox"][1], b["bbox"][1]) > 0
                labelled = same_row and b["bbox"][0] >= prev["bbox"][2] - 5
            readings = [r for r in (b.get("readings") or {}).values() if r]
            # Both recognisers read the line and agree on almost nothing: a scribble, whichever reading won
            scribble = len(readings) == 2 and difflib.SequenceMatcher(
                a=readings[0].lower(), b=readings[1].lower()).ratio() < 0.4
            unlabelled = (
                b["bbox"][1] >= 0.6 * H and (b.get("source") == "handwritten" or scribble) and 1 <= len(words) <= 3
                and not any(ch.isdigit() for ch in text) and self.validity(text) < 0.5
                and b.get("confidence", 1.0) < 0.85
            )
            if labelled or unlabelled:
                b["role"] = "signature"
                b["raw_text"] = text
                b["text"] = "[signature]"


def resolve_applies_to(sorted_blocks: List[Dict]) -> List[Dict]:
    """After reading-order ids are assigned, turns `applies_to_uids` into block ids and drops helper keys."""
    uid_to_id = {b.get("layout_uid"): b.get("id") for b in sorted_blocks}
    for b in sorted_blocks:
        if "applies_to_uids" in b:
            b["applies_to"] = [uid_to_id[u] for u in b.pop("applies_to_uids") if u in uid_to_id]
        b.pop("layout_uid", None)
    return sorted_blocks
