"""Model-free tests for layout roles, structured extraction, spelling channel model and the feedback store."""
import json

import cv2
import numpy as np

from app.ai.ocr.document_layout import DocumentLayoutAnalyzer, find_separators, resolve_applies_to
from app.ai.ocr.htr_language_model import channel_cost
from app.ai.ocr.medical_structurer import MedicalStructurer
from app.ai.ocr.ocr_engine import ReadingOrderRebuilder


def _page_with_brace():
    img = np.full((400, 700, 3), 250, np.uint8)
    cv2.putText(img, "after", (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
    cv2.ellipse(img, (110, 150), (12, 90), 0, 100, 260, (20, 20, 20), 2)  # "{"-like brace spanning 2 lines
    cv2.putText(img, "Tab. Augmentin 625mg", (150, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    cv2.putText(img, "1 - 0 - 1 x 5days", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (20, 20, 20), 2)
    return img


def test_brace_is_detected_as_separator():
    seps = find_separators(_page_with_brace(), line_height=35)
    assert any(90 <= (s[0] + s[2]) / 2 <= 130 and s[3] - s[1] > 100 for s in seps)


def test_margin_note_gets_scope_and_its_own_line():
    img = _page_with_brace()
    blocks = [
        {"text": "after", "bbox": [8, 115, 80, 142], "source": "handwritten", "confidence": 0.9},
        {"text": "Tab. Augmentin 625mg", "bbox": [148, 78, 480, 108], "source": "handwritten", "confidence": 0.9},
        {"text": "1 - 0 - 1 x 5days", "bbox": [148, 178, 420, 208], "source": "handwritten", "confidence": 0.9},
    ]
    DocumentLayoutAnalyzer().annotate(blocks, img)
    assert blocks[0]["role"] == "margin_note"
    ordered, raw = ReadingOrderRebuilder().rebuild_order(blocks)
    resolve_applies_to(ordered)
    note = next(b for b in ordered if b["role"] == "margin_note")
    assert raw.splitlines()[0] == "after"  # not fused into the medicine line
    assert len(note["applies_to"]) == 2


def test_signature_is_masked_but_reading_kept():
    img = np.full((1000, 800, 3), 250, np.uint8)
    blocks = [{"text": "Cwite", "bbox": [500, 850, 650, 900], "source": "handwritten", "confidence": 0.4}]
    DocumentLayoutAnalyzer(validity=lambda t: 0.0).annotate(blocks, img)
    assert blocks[0]["role"] == "signature" and blocks[0]["text"] == "[signature]" and blocks[0]["raw_text"] == "Cwite"


def test_prescription_structuring_with_margin_timing():
    s = MedicalStructurer(["Augmentin", "Pan-D"], ["massage", "gum", "paint"])
    lines = ["12/10/22", "Mr. Sachin Sansare", "28/m", "after meals", "Tab. Augmentin 625mg", "1 - 0 - 1 x 5days",
             "Adv: Hexigel gum paint", "massage", "1 - 0 - 1 x 1week"]
    blocks = [{"id": f"b{i}", "text": t, "role": "body"} for i, t in enumerate(lines)]
    blocks[3].update(role="margin_note", applies_to=["b4", "b5"])
    out = s.extract(blocks)
    assert (out["patient_name"], out["age"], out["sex"], out["date"]) == ("Sachin Sansare", "28", "M", "12/10/22")
    aug, hexi = out["medications"]
    assert (aug["drug"], aug["strength"], aug["frequency"], aug["duration"], aug["timing"]) == \
        ("Augmentin", "625mg", "1-0-1", "5 days", "after meals")
    assert (hexi["drug"], hexi["frequency"], hexi["duration"]) == ("Hexigel", "1-0-1", "1 week")
    assert out["document_type"] == "prescription"


def test_lab_rows_and_flags():
    out = MedicalStructurer().extract([{"id": "l1", "text": "Fasting Blood Sugar 128 mg/dL 70 - 100", "role": "body"},
                                       {"id": "l2", "text": "Hemoglobin (Hb) 13.8 g/dL 12.0 - 15.5", "role": "body"},
                                       {"id": "l0", "text": "CLINICAL BIOCHEMISTRY", "role": "body"}])
    flags = {r["test"]: r["flag"] for r in out["lab_results"]}
    assert flags == {"Fasting Blood Sugar": "H", "Hemoglobin (Hb)": ""}


def test_handwriting_confusions_are_cheap():
    assert channel_cost("leauning", "learning") < 0.5
    assert channel_cost("fuom", "from") < 0.5
    assert channel_cost("leauning", "leaving") > channel_cost("leauning", "learning")


def test_feedback_store_turns_corrections_into_pairs(tmp_path, monkeypatch):
    from app.services import feedback_service as fb
    monkeypatch.setenv("OCR_FEEDBACK_DATASET", "1")
    monkeypatch.setenv("OCR_FEEDBACK_DIR", str(tmp_path))
    page = np.full((200, 400, 3), 255, np.uint8)
    blocks = [{"id": "block_1", "text": "Machine leauning", "bbox": [10, 10, 300, 40], "page": 1, "source": "handwritten"},
              {"id": "block_2", "text": "is fun", "bbox": [10, 60, 200, 90], "page": 1, "source": "handwritten"}]
    fb.record_extraction("note.png", [page], blocks)
    n = fb.record_correction("note.png", "Machine leauning\nis fun", "Machine learning\nis fun")
    assert n == 1
    rows = [json.loads(l) for l in (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows[0]["text"] == "Machine learning" and rows[0]["bbox"] == [10, 10, 300, 40]


def test_feedback_store_is_off_by_default(tmp_path, monkeypatch):
    from app.services import feedback_service as fb
    monkeypatch.delenv("OCR_FEEDBACK_DATASET", raising=False)
    monkeypatch.setenv("OCR_FEEDBACK_DIR", str(tmp_path))
    fb.record_extraction("x.png", [np.zeros((10, 10, 3), np.uint8)], [])
    assert not any(tmp_path.iterdir())


def test_exif_rotated_phone_photo_is_decoded_upright():
    import io
    from PIL import Image
    from app.services.document_processing_service import DocumentProcessingService
    upright = np.full((300, 200, 3), 255, np.uint8)
    upright[:40] = 0  # dark band at the top of the page
    stored = Image.fromarray(upright).transpose(Image.Transpose.ROTATE_90)  # how a phone stores it, tag 6
    exif = Image.Exif()
    exif[274] = 6
    buf = io.BytesIO()
    stored.save(buf, format="JPEG", exif=exif)
    page = DocumentProcessingService()._process_raster(buf.getvalue(), "photo.jpg", "image").pages[0]
    assert page.image.shape[:2] == (300, 200)
    assert page.image[:30].mean() < 60 and page.image[-100:].mean() > 200


def test_sideways_and_upside_down_pages_are_detected():
    import pytest
    try:
        from app.ai.ocr.rapid_adapter import create_rapid_ocr
        rapid = create_rapid_ocr()
    except Exception:
        pytest.skip("PP-OCR models unavailable")
    from app.ai.ocr.page_orientation import detect_rotation, rotate
    page = np.full((900, 700, 3), 255, np.uint8)
    for i, line in enumerate(["Patient: Ramesh Kumar", "Tab. Paracetamol 500mg", "1 - 0 - 1 after food",
                              "Review after 5 days", "Blood pressure 130/80"]):
        cv2.putText(page, line, (30, 80 + 70 * i), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    for turned in (0, 90, 180, 270):
        assert (turned + detect_rotation(rotate(page, turned), rapid)) % 360 == 0


def test_two_line_and_fused_margin_timing():
    s = MedicalStructurer(["Augmentin", "Pan-D"], [])
    lines = [("after", "margin_note"), ("meals", "margin_note"), ("Tab. Augmentin 625mg", "body"),
             ("1 - 0 - 1 x 5days", "body"), ("before & Tab Pan-D 40 mg", "body"), ("meals", "body"),
             ("1 - 0 - 0 x 5days", "body")]
    blocks = [{"id": f"b{i}", "text": t, "role": r, "reading_order": i} for i, (t, r) in enumerate(lines)]
    blocks[0]["applies_to"] = blocks[1]["applies_to"] = ["b2", "b3"]
    aug, pan = s.extract(blocks)["medications"]
    assert aug["timing"] == "after meals"
    assert (pan["drug"], pan["timing"], pan["frequency"]) == ("Pan-D", "before meals", "1-0-0")
    assert blocks[4]["text"] == "before & Tab Pan-D 40 mg"  # OCR output untouched


def test_lab_rows_split_into_cells_are_read_whole():
    cells = [("Hemoglobin (Hb) 13.8", 4), ("g/dL 12.0 - 15.5", 4), ("Serum Creatinine 0.9 mg/dL", 5), ("0.6 - 1.2", 5)]
    blocks = [{"id": f"c{i}", "text": t, "role": "body", "line_number": ln, "reading_order": i}
              for i, (t, ln) in enumerate(cells)]
    out = MedicalStructurer(["Serum"], []).extract(blocks)
    assert out["medications"] == []
    assert [(r["test"], r["value"], r["source_blocks"]) for r in out["lab_results"]] == \
        [("Hemoglobin (Hb)", "13.8", ["c0", "c1"]), ("Serum Creatinine", "0.9", ["c2", "c3"])]


def test_garbled_field_labels_and_sig_instructions():
    s = MedicalStructurer(["Lisinopril", "Amoxicillin"], ["parent"])
    lines = ["Date: 2024-12-16", "Pauent: Michael Brown, Apr: 42", "Lisinopril 20 mg - Every 8 hours",
             "Amoxicillin 10 mg - As directed", "Ibuprofen 400 mg - As needed for pain"]
    blocks = [{"id": f"b{i}", "text": t, "role": "body"} for i, t in enumerate(lines)]
    out = s.extract(blocks)
    assert (out["patient_name"], out["age"]) == ("Michael Brown", "42")
    assert [m["instructions"] for m in out["medications"]] == ["every 8 hours", "as directed", "as needed for pain"]
    assert blocks[1]["text"].startswith("Pauent")  # OCR text untouched
