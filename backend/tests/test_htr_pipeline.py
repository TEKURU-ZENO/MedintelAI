"""Model-free unit tests for the handwriting layout path, recogniser ensemble and reading order."""
import cv2
import numpy as np

from app.ai.ocr.htr_ensemble import calibrate, choose
from app.ai.ocr.htr_layout import (
    HandwritingLineBuilder, order_quad, piecewise_line_crop, quad_geometry, split_long_line,
)
from app.ai.ocr.ocr_engine import MedIntelOCREngine, ReadingOrderRebuilder


def _quad(x0, y0, x1, y1):
    return np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float32)


def _page_with_lines(lines, w=900, h=300, ink=20):
    img = np.full((h, w, 3), 245, np.uint8)
    for (x, y, text) in lines:
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (ink, ink, ink), 3)
    return img


def test_order_quad_returns_tl_tr_br_bl():
    shuffled = np.array([[100, 50], [0, 0], [0, 50], [100, 0]], dtype=np.float32)
    q = order_quad(shuffled)
    assert q.tolist() == [[0, 0], [100, 0], [100, 50], [0, 50]]


def test_collinear_fragments_merge_but_separate_lines_do_not():
    quads = [_quad(0, 0, 100, 40), _quad(120, 2, 220, 42), _quad(0, 80, 100, 120)]
    groups = sorted(sorted(g) for g in HandwritingLineBuilder.merge_into_lines(quads))
    assert groups == [[0, 1], [2]]


def test_tall_box_spanning_two_lines_is_split():
    img = _page_with_lines([(20, 60, "first line of text"), (20, 140, "second line here")])
    tall = _quad(10, 20, 500, 160)
    single = [_quad(10, 220, 300, 270)]  # establishes the normal line height
    builder = HandwritingLineBuilder()
    line_h = builder.median_height([_quad(10, 20, 500, 85), _quad(10, 95, 500, 160)])
    out = builder.split_multiline(img, [tall] + single, line_h)
    assert len(out) == 3


def test_piecewise_crop_trims_overlap_instead_of_duplicating_ink():
    img = _page_with_lines([(20, 60, "overlapping words")])
    a, b = _quad(10, 20, 260, 75), _quad(200, 20, 420, 75)  # 60 px overlap
    crop = piecewise_line_crop(img, [a, b], pad_ratio=0.0)
    whole = piecewise_line_crop(img, [_quad(10, 20, 420, 75)], pad_ratio=0.0)
    assert crop is not None and whole is not None
    # Stitched width ~ union width (+ a small spacer), never the sum of both pieces
    assert crop.shape[1] < quad_geometry(a)[2] + quad_geometry(b)[2]


def test_split_long_line_only_splits_out_of_distribution_strips():
    strip = np.full((40, 1200, 3), 250, np.uint8)
    cv2.putText(strip, "aaaaaaaaaa", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    cv2.putText(strip, "bbbbbbbbbb", (700, 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    assert len(split_long_line(strip)) == 2           # aspect 30 > 16
    assert len(split_long_line(strip[:, :500])) == 1  # aspect 12.5 stays whole


def test_ensemble_prefers_non_empty_and_calibrates_confidence():
    validity = lambda t: 1.0 if t else 0.0
    text, conf, engine = choose(("", 0.0), ("Paracetamol 650 mg", 0.6), validity)
    assert (text, engine) == ("Paracetamol 650 mg", "trocr") and 0.0 < conf <= 1.0
    assert calibrate(0.3, "rapid") <= calibrate(0.9, "rapid") <= calibrate(1.0, "rapid")


def test_reading_order_uses_line_band_for_slanted_lines():
    # Two slanted lines whose axis-aligned boxes overlap heavily; bands keep them on separate rows
    blocks = [
        {"text": "second", "bbox": [0, 40, 500, 140], "_line_band": [85, 125]},
        {"text": "first", "bbox": [30, 0, 520, 100], "_line_band": [20, 60]},
    ]
    ordered, raw_text = ReadingOrderRebuilder().rebuild_order(blocks)
    assert raw_text.splitlines() == ["first", "second"]
    assert all("_line_band" not in b for b in ordered)


def test_partition_drops_faint_low_confidence_bleed_through():
    engine = MedIntelOCREngine.__new__(MedIntelOCREngine)
    engine._trocr_model = object()
    img = _page_with_lines([(20, 60, "real ink one"), (20, 140, "real ink two"), (20, 220, "real three")])
    cv2.putText(img, "ghost", (600, 140), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (200, 200, 200), 3)
    items = [
        {"confidence": 0.99, "quad": _quad(10, 25, 400, 75).tolist(), "bbox": [10, 25, 400, 75]},
        {"confidence": 0.60, "quad": _quad(10, 105, 400, 155).tolist(), "bbox": [10, 105, 400, 155]},
        {"confidence": 0.99, "quad": _quad(10, 185, 400, 235).tolist(), "bbox": [10, 185, 400, 235]},
        {"confidence": 0.50, "quad": _quad(590, 105, 760, 155).tolist(), "bbox": [590, 105, 760, 155]},
    ]
    printed, uncertain, _ = engine._partition_handwriting(items, img, "auto")
    kept = printed + uncertain
    assert len(kept) == 3 and all(it["bbox"][0] < 500 for it in kept)
