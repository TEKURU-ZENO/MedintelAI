"""Model-free tests for the word review (ambiguity / spelling flags) and the formatted document view."""
from app.ai.ocr.document_formatter import format_document
from app.ai.ocr.medical_structurer import MedicalStructurer
from app.ai.ocr.text_review import TextReviewer

COMMON = ["machine", "learning", "is", "a", "branch", "of", "the", "gum", "gun", "paint", "adv", "tab", "after",
          "meals", "review", "in", "week", "one", "fever", "and", "cough", "for", "days", "with"]


class FakeSpell:
    """Stands in for the language-model corrector: fixed suggestions, dictionary = COMMON."""
    def _is_known(self, w):
        return w.lower() in COMMON

    def suggest(self, tokens, i, n=3):
        return {"buanch": ["branch", "bunch"]}.get(tokens[i].strip(".,").lower(), [])


def _reviewer():
    return TextReviewer(COMMON, ["Augmentin", "Pan-D", "Hexigel"], spell=FakeSpell())


def _block(text, **kw):
    return {"id": kw.pop("id", "b1"), "text": text, "confidence": kw.pop("confidence", 0.9),
            "source": kw.pop("source", "handwritten"), **kw}


def test_ambiguity_needs_a_real_word_as_the_other_reading():
    b = _block("Adv: Hexigel gun paint", readings={"ppocr": "Adv: Hexigel gum paint", "trocr": "Adv: Hexigel gun paint"})
    flags = _reviewer().review_block(b)
    assert [(f["kind"], f["word"], f["suggestions"]) for f in flags] == [("ambiguous", "gun", ["gum"])]
    noisy = _block("Machine learning is fun", readings={"ppocr": "Machine leaurtes is fun"})
    assert not [f for f in _reviewer().review_block(noisy) if f["kind"] == "ambiguous"]


def test_spelling_flag_offsets_and_suggestions():
    b = _block("Machine learning is a buanch of the", confidence=0.95)
    (flag,) = _reviewer().review_block(b)
    assert flag["kind"] == "spelling" and flag["suggestions"][0] == "branch"
    assert b["text"][flag["start"]:flag["end"]] == "buanch"


def test_auto_correction_is_offered_for_revert():
    b = _block("Machine learning is a branch", corrections=[{"from": "buanch", "to": "branch"}])
    (flag,) = _reviewer().review_block(b)
    assert (flag["kind"], flag["word"], flag["suggestions"]) == ("corrected", "branch", ["buanch"])


def test_word_beside_a_dose_gets_drug_suggestions_only():
    b = _block("Tab Augmentim 625 mg", confidence=0.7)
    (flag,) = _reviewer().review_block(b)
    assert flag["word"] == "Augmentim" and flag["suggestions"] == ["Augmentin"]


def test_unknown_word_without_close_match_is_not_flagged_on_a_confident_line():
    assert _reviewer().review_block(_block("Machine learning is datasets", confidence=0.95)) == []
    review = _reviewer().review([_block("xq", confidence=0.4)])
    assert review["lines_to_check"] == 1


def test_age_sex_read_as_a_dose_is_recognised_only_with_the_other_reading():
    from app.ai.ocr.ocr_engine import _AGE_SEX_READ, _DOSE_ONLY
    for dose, other in (("28 mg", "281m"), ("28mg", "28/M"), ("45 mg", "45|f")):
        d, a = _DOSE_ONLY.match(dose), _AGE_SEX_READ.match(other)
        assert d and a and d.group(1) == a.group(1)
    assert not _AGE_SEX_READ.match("28mg")             # the other reader also saw a dose: keep it
    assert not _DOSE_ONLY.match("Tab Augmentin 28 mg")  # a medicine line is never rewritten


def _rx_blocks():
    rows = [("THE WHITE TUSK", "header"), ("12/10/22 Mr. Sachin Sansare 28/M", "body"), ("Rx", "body"),
            ("Tab. Augmentin 625mg", "body"), ("1 - 0 - 1 x 5days", "body"), ("Adv: Hexigel gum paint", "body"),
            ("1 - 0 - 1 x 1week", "body"), ("Review after one week", "body"), ("Ph: 98765 43210", "footer")]
    blocks = [{"id": f"b{i}", "text": t, "role": r, "line_number": i, "reading_order": i, "page": 1,
               "bbox": [100, 40 * i, 400, 40 * i + 30]} for i, (t, r) in enumerate(rows)]
    blocks.append({"id": "m1", "text": "after meals", "role": "margin_note", "applies_to": ["b3", "b4"],
                   "line_number": 3, "reading_order": 99, "page": 1, "bbox": [10, 120, 80, 150]})
    return blocks


def test_prescription_is_formatted_into_sections():
    blocks = _rx_blocks()
    structured = MedicalStructurer(["Augmentin", "Hexigel"], COMMON).extract(blocks)
    text = format_document(blocks, structured)
    lines = [l for l in text.splitlines() if l]
    assert lines[0] == "THE WHITE TUSK"
    assert lines[1] == "Patient: Sachin Sansare | Age/Sex: 28/M | Date: 12/10/22"
    assert lines[2] == "Rx"
    assert lines[3] == "1. Tab Augmentin 625mg — 1-0-1 for 5 days, after meals"
    assert lines[4] == "2. Hexigel gum paint — 1-0-1 for 1 week"
    assert "Follow-up: Review after one week" in lines and lines[-1] == "Ph: 98765 43210"
    assert "after meals" not in lines  # the margin note is folded into the medicines it covers


def test_patient_row_with_an_unparsed_bit_is_not_repeated():
    rows = ["CLINIC", "12/10/22 Me Sachin Sansare 28 mg", "Review after one week"]
    blocks = [{"id": f"b{i}", "text": t, "role": "header" if i == 0 else "body", "line_number": i,
               "reading_order": i, "page": 1, "bbox": [10, 30 * i, 300, 30 * i + 20]} for i, t in enumerate(rows)]
    lines = [l for l in format_document(blocks, {"patient_name": "Sachin Sansare", "date": "12/10/22"}).splitlines() if l]
    assert lines == ["CLINIC", "Patient: Sachin Sansare | Date: 12/10/22 | 28 mg", "Review after one week"]


def test_wrapped_lines_become_paragraphs_and_lists_stay():
    rows = ["Machine learning is a branch of", "artificial intelli-", "gence used for recommenda", "tion systems.",
            "1. first item", "2. second item"]
    blocks = [{"id": f"b{i}", "text": t, "line_number": i, "reading_order": i, "page": 1,
               "bbox": [10, 30 * i, 300, 30 * i + 20]} for i, t in enumerate(rows)]
    text = format_document(blocks, {}, is_word=lambda w: w.lower() in {"recommendation", "artificial"})
    assert text.splitlines()[0] == ("Machine learning is a branch of artificial intelligence used for "
                                    "recommendation systems.")
    assert "1. first item" in text.splitlines() and "2. second item" in text.splitlines()


def test_side_column_is_read_after_main_text_but_tables_keep_rows():
    main = [f"main line {i} of the page text" for i in range(6)]
    blocks = [{"id": f"m{i}", "text": t, "line_number": i, "reading_order": 2 * i, "page": 1,
               "bbox": [20, 40 * i, 400, 40 * i + 25]} for i, t in enumerate(main)]
    # side notes in a right-hand column, not aligned with the main lines
    blocks += [{"id": f"s{i}", "text": f"side note {i}", "line_number": 2 * i, "reading_order": 2 * i + 1, "page": 1,
                "bbox": [600, 40 * 2 * i + 18, 760, 40 * 2 * i + 50]} for i in range(2)]
    paragraphs = format_document(blocks, {}).split("\n\n")
    assert paragraphs[0].startswith("main line 0") and paragraphs[0].endswith("main line 5 of the page text")
    assert paragraphs[-1] == "side note 0 side note 1"
    table = [{"id": f"t{i}{c}", "text": f"{'Label' if c == 0 else 'value'} {i}", "line_number": i,
              "reading_order": 2 * i + c, "page": 1, "bbox": [20 + 500 * c, 40 * i, 200 + 500 * c, 40 * i + 25]}
             for i in range(4) for c in (0, 1)]
    assert [l for l in format_document(table, {}).splitlines() if l][0] == "Label 0 | value 0"


def _lines(*rows):
    return [{"id": f"b{i}", "text": t, "role": "body", "line_number": i, "reading_order": i, "page": 1,
             "bbox": [10, 30 * i, 300, 30 * i + 20]} for i, t in enumerate(rows)]


def test_paediatric_syrups_keep_concentration_interval_and_weight():
    blocks = _lines("Weight: 13.25 kg", "Rx", "Syp Calpol (250/5) 4ml Q6H x 3 days", "Syp Delcon 3ml TDS x 5 days")
    s = MedicalStructurer(["Calpol", "Delcon"], COMMON).extract(blocks)
    calpol = s["medications"][0]
    assert s["weight"].startswith("13.25")
    assert calpol["concentration"] == "250/5" and calpol["strength"] == "4ml" and "Q6H" in calpol["frequency"].upper()
    assert "(250/5)" in format_document(blocks, s)


def test_a_wrapped_word_after_a_medicine_joins_its_preparation():
    blocks = _lines("Rx", "Adv: Hexigel gum paint", "massage", "1 - 0 - 1 x 1week")
    med = MedicalStructurer(["Hexigel"], COMMON).extract(blocks)["medications"][0]
    assert med["preparation"] == "gum paint massage"


def test_an_approximate_drug_match_is_flagged_for_checking():
    blocks = _lines("Rx", "Tab Augmentim 625mg 1-0-1 x 5 days")
    s = MedicalStructurer(["Augmentin"], COMMON).extract(blocks)
    assert s["medications"][0]["normalized_drug"] == "Augmentin"
    assert "drug matched approximately to Augmentin (verify)" in s["medications"][0]["issues"]


def test_a_line_both_readers_disagree_on_is_a_signature():
    from app.ai.ocr.document_layout import DocumentLayoutAnalyzer
    import numpy as np
    blocks = [{"text": "Review after one week", "bbox": [10, 100, 300, 130], "source": "printed", "confidence": 0.95},
              {"text": "Cwite", "bbox": [200, 700, 300, 740], "source": "printed", "confidence": 0.6,
               "readings": {"rapid": "Cwite", "trocr": "omasto"}},
              {"text": "Clinic hours", "bbox": [10, 760, 200, 790], "source": "printed", "confidence": 0.6,
               "readings": {"rapid": "Clinic hours", "trocr": "Clinic hour"}}]
    DocumentLayoutAnalyzer(validity=lambda t: 0.0 if t == "Cwite" else 1.0).annotate(
        blocks, np.full((1000, 600, 3), 255, np.uint8), separators=[])
    assert blocks[1]["role"] == "signature" and blocks[1]["raw_text"] == "Cwite"
    assert blocks[2]["role"] != "signature"


def test_formulary_names_extend_the_drug_terms(tmp_path, monkeypatch):
    from app.ai.ocr.ocr_engine import MedIntelOCREngine
    formulary = tmp_path / "formulary.csv"
    formulary.write_text("Brand Name,Strength\nZerodolx,100mg\nCalpol,500mg\n", encoding="utf-8")
    monkeypatch.setenv("OCR_FORMULARY", str(formulary))
    engine = MedIntelOCREngine.__new__(MedIntelOCREngine)
    engine._model_dir, engine._vocab_cache = None, None
    terms = engine._vocabularies()["terms"]
    assert "Zerodolx" in terms and "Calpol" in terms and "Brand Name" not in terms
    assert sum(t.lower() == "calpol" for t in terms) == 1


def _messy_rx(order):
    """A prescription written in a jumbled order; `order` is the page's top-to-bottom sequence of row keys."""
    rows = {"head": ("CITY CHILD CLINIC", "header"), "pt": ("Name: Ashika 4/F Date: 20-11-2022", "body"),
            "adv": ("Adv: plenty of fluids", "body"), "rr": ("RR - 22/min", "body"),
            "dx": ("Dx: URTI", "body"), "co": ("C/O fever and cough x 3 days", "body"), "rx": ("Rx", "body"),
            "m1": ("Syp Calpol (250/5) 4ml Q6H x 3 days", "body"), "m2": ("Syp Delcon 3ml TDS x 5 days", "body"),
            "fu": ("Review after 5 days", "body"), "foot": ("Ph: 98765 43210", "footer")}
    return [{"id": k, "text": rows[k][0], "role": rows[k][1], "line_number": i, "reading_order": i, "page": 1,
             "bbox": [10, 30 * i, 300, 30 * i + 20]} for i, k in enumerate(order)]


EXPECTED_RX = [
    "CITY CHILD CLINIC",
    "Patient: Ashika | Age/Sex: 4/F | Date: 20-11-2022",
    "Vitals: RR - 22/min",
    "Complaints: fever and cough x 3 days",
    "Diagnosis: URTI",
    "Rx",
    "1. Syp Calpol (250/5) 4ml — Q6H for 3 days",
    "2. Syp Delcon 3ml — TDS for 5 days",
    "Advice: plenty of fluids",
    "Follow-up: Review after 5 days",
    "Ph: 98765 43210",
]


def _formatted(blocks):
    s = MedicalStructurer(["Calpol", "Delcon"], COMMON).extract(blocks)
    return [l for l in format_document(blocks, s).splitlines() if l]


def test_sections_come_out_in_the_template_order_however_the_page_is_written():
    tidy = ["head", "pt", "co", "rr", "dx", "rx", "m1", "m2", "adv", "fu", "foot"]
    jumbled = ["head", "pt", "fu", "adv", "rx", "m1", "m2", "dx", "rr", "co", "foot"]
    assert _formatted(_messy_rx(tidy)) == EXPECTED_RX
    assert _formatted(_messy_rx(jumbled)) == EXPECTED_RX


def test_detector_order_of_the_blocks_does_not_matter():
    import random
    blocks = _messy_rx(["head", "pt", "dx", "co", "rx", "m1", "m2", "rr", "adv", "fu", "foot"])
    for seed in range(5):
        shuffled = list(blocks)
        random.Random(seed).shuffle(shuffled)
        assert _formatted(shuffled) == EXPECTED_RX


def test_lines_under_a_heading_stay_in_its_section_and_unlabelled_text_is_kept():
    blocks = _messy_rx(["head", "pt", "rx", "m1", "m2", "foot"])
    extra = [("C/O", 1.2), ("fever since 3 days", 1.4), ("loose motions", 1.6), ("Inv: CBC, CRP", 4.4),
             ("Mother counselled", 4.6)]
    for k, (text, ln) in enumerate(extra):
        blocks.append({"id": f"x{k}", "text": text, "role": "body", "line_number": ln, "reading_order": ln,
                       "page": 1, "bbox": [10, 30 * ln, 300, 30 * ln + 20]})
    lines = _formatted(blocks)
    at = lines.index("Complaints:")
    assert lines[at + 1:at + 3] == ["fever since 3 days", "loose motions"]
    assert lines.index("Complaints:") < lines.index("Rx") < lines.index("Investigations:")
    assert any("CBC, CRP" in l for l in lines) and any("Mother counselled" in l for l in lines)  # nothing dropped


def test_the_hospital_template_sets_names_and_order():
    from app.ai.ocr.document_formatter import format_sections, prepare_template
    template = prepare_template({"name": "city-hospital", "sections": [
        {"key": "patient", "title": None},
        {"key": "diagnosis", "title": "Provisional Diagnosis", "headings": ["dx", "diagnosis"]},
        {"key": "rx", "title": "Treatment"},
        {"key": "complaints", "title": "Presenting Complaints", "headings": ["c/o"]},
        {"key": "vitals", "title": "Vitals"}]})
    blocks = _messy_rx(["head", "pt", "co", "rr", "dx", "rx", "m1", "m2", "foot"])
    s = MedicalStructurer(["Calpol", "Delcon"], COMMON).extract(blocks)
    lines = [l for l in format_document(blocks, s, template=template).splitlines() if l]
    assert lines[2:5] == ["Provisional Diagnosis: URTI", "Treatment", "1. Syp Calpol (250/5) 4ml — Q6H for 3 days"]
    assert lines.index("Presenting Complaints: fever and cough x 3 days") < lines.index("Vitals: RR - 22/min")
    doc = format_sections(blocks, s, template=template)
    assert doc["template"] == "city-hospital" and [x["key"] for x in doc["sections"]][:3] == ["patient", "diagnosis", "rx"]
    assert doc["sections"][2]["medications"][0]["normalized_drug"] == "Calpol"


def test_notebook_pages_keep_the_plain_reading():
    from app.ai.ocr.document_formatter import format_sections
    blocks = _lines("Introduction", "Machine learning is a branch of", "artificial intelligence.", "Review of the topic")
    assert format_sections(blocks, {}) is None
