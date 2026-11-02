"""
Page orientation from content, for pages whose pixels are not upright and carry no EXIF tag to say so
(sideways scans, upside-down photocopies, rotated screenshots).

A PP-OCR detection-only pass on a downscaled copy tells whether text lines run horizontally or vertically;
PP-OCR then reads the longest line crops at both remaining candidate rotations (0/180 or 90/270) and the
rotation it reads with clearly higher confidence wins. Cost per page: one small detection and two recognition
batches of a few lines.
"""
from typing import Any, List, Tuple

import cv2
import numpy as np

MAX_SIDE = 960       # detection runs on a copy at most this large
MAX_CROPS = 4        # longest line crops compared at each candidate rotation
MAX_ASPECT = 8       # each crop is cut to this many line heights: enough to judge, and recognition time grows with length
MIN_LINES = 3        # fewer elongated lines than this: orientation is not decided, page left as is
FLIP_MARGIN = 0.08   # an upright-looking page is turned 180 degrees only if that reads this much more confidently


def rotate(image: np.ndarray, degrees_cw: int) -> np.ndarray:
    if degrees_cw == 90:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    if degrees_cw == 180:
        return cv2.rotate(image, cv2.ROTATE_180)
    if degrees_cw == 270:
        return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return image


def _detect_quads(rapid, image: np.ndarray) -> List[Any]:
    if hasattr(rapid, "detect"):  # rapidocr 3.x adapter: detection only
        return rapid.detect(image)
    if hasattr(rapid, "text_det"):  # legacy rapidocr-onnxruntime
        boxes, _ = rapid.text_det(image)
        return [] if boxes is None else list(boxes)
    results, _ = rapid(image)
    return [r[0] for r in results or []]


def _line_boxes(quads: List[Any], width: int, height: int) -> List[Tuple[int, int, int, int]]:
    boxes = []
    for quad in quads:
        xs = [p[0] for p in quad]
        ys = [p[1] for p in quad]
        x1, x2 = int(max(0, min(xs))), int(min(width, max(xs)))
        y1, y2 = int(max(0, min(ys))), int(min(height, max(ys)))
        w, h = x2 - x1, y2 - y1
        if min(w, h) >= 4 and max(w, h) >= 2.5 * min(w, h):  # short words are ambiguous about direction
            boxes.append((x1, y1, x2, y2))
    return boxes


def _read_score(rapid, crops: List[np.ndarray]) -> float:
    results, _ = rapid.text_recognizer(crops)
    # Weight by length so a confident single character does not outvote whole lines
    weights = [max(1, len(t.strip())) for t, _ in results]
    return float(np.average([s for _, s in results], weights=weights)) if results else 0.0


def detect_rotation(image: np.ndarray, rapid) -> int:
    """Clockwise rotation in degrees (0, 90, 180 or 270) that makes the page upright."""
    h, w = image.shape[:2]
    scale = min(1.0, MAX_SIDE / max(h, w))
    small = cv2.resize(image, (max(1, int(w * scale)), max(1, int(h * scale))), interpolation=cv2.INTER_AREA) \
        if scale < 1.0 else image
    boxes = _line_boxes(_detect_quads(rapid, small), small.shape[1], small.shape[0])
    if len(boxes) < MIN_LINES:
        return 0
    vertical = sum((y2 - y1) > (x2 - x1) for x1, y1, x2, y2 in boxes)
    sideways = vertical > len(boxes) / 2
    boxes.sort(key=lambda b: -max(b[2] - b[0], b[3] - b[1]))
    crops = []
    for x1, y1, x2, y2 in boxes:
        if ((y2 - y1) > (x2 - x1)) != sideways:
            continue
        if sideways:
            y2 = min(y2, y1 + MAX_ASPECT * (x2 - x1))
        else:
            x2 = min(x2, x1 + MAX_ASPECT * (y2 - y1))
        crops.append(small[y1:y2, x1:x2])
        if len(crops) == MAX_CROPS:
            break
    if len(crops) < min(MIN_LINES, MAX_CROPS):
        return 0
    if sideways:
        cw, ccw = _read_score(rapid, [rotate(c, 90) for c in crops]), _read_score(rapid, [rotate(c, 270) for c in crops])
        return 90 if cw >= ccw else 270
    upright, flipped = _read_score(rapid, crops), _read_score(rapid, [rotate(c, 180) for c in crops])
    return 180 if flipped > upright + FLIP_MARGIN else 0
