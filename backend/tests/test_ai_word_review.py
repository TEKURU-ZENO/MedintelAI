"""Model-free tests for the AI word suggestions: a fake vision model; the text must never change."""
import numpy as np

from app.ai.ocr.ai_word_review import AIWordReviewer, enhanced_view, word_pairs

KNOWN = {"consultancy", "approved", "keep", "the", "office", "take", "after", "food", "paracetamol", "for", "days"}


class FakeReader:
    def __init__(self, reads):
        self.reads, self.prompts = reads, None

    @staticmethod
    def context_prompt(readings, context=()):
        return " | ".join(list(readings) + list(context))

    def read(self, crops, prompts=None, batch_size=4):
        self.prompts = prompts
        return [self.reads[i % len(self.reads)] for i in range(len(crops))]


def _block(text="Cousuleacy approved", **kw):
    return {"id": "b1", "text": text, "confidence": 0.5, "bbox": [0, 0, 100, 20], "page": 1, "reading_order": 1,
            "source": "handwritten", "readings": {"ppocr": "Consultancy approved", "trocr": text}, **kw}


def _run(block, reads, **kw):
    r = AIWordReviewer(FakeReader(reads), lambda w: w.lower() in KNOWN, drugs=["paracetamol"], **kw)
    n = r.review([block], lambda b: np.full((20, 100, 3), 255, np.uint8))
    return n, block.get("review", [])


def test_a_word_both_views_agree_on_is_flagged_and_the_text_stays():
    b = _block()
    n, flags = _run(b, [("Consultancy approved", 0.9)])
    assert n == 1 and b["text"] == "Cousuleacy approved"
    f = flags[0]
    assert (f["kind"], f["word"], f["suggestions"]) == ("ai", "Cousuleacy", ["Consultancy"])
    assert b["text"][f["start"]:f["end"]] == "Cousuleacy" and f["bbox"] == [0, 0, 100, 20]
    assert f["evidence"]["views_agree"] and f["evidence"]["in_dictionary"] and f["evidence"]["matches_other_reader"]


def test_views_that_disagree_or_a_weak_or_unrelated_reading_propose_nothing():
    assert _run(_block(), [("Consultancy approved", 0.9), ("Consultant approved", 0.9)])[0] == 0
    assert _run(_block(), [("Consultancy approved", 0.2)])[0] == 0
    assert _run(_block(), [("The weather is lovely today", 0.95)])[0] == 0


def test_an_existing_flag_gains_the_suggestion_instead_of_a_duplicate():
    b = _block(review=[{"word": "Cousuleacy", "start": 0, "end": 10, "kind": "spelling", "suggestions": ["Counsel"],
                        "reason": "Not a known word"}])
    _, flags = _run(b, [("Consultancy approved", 0.9)])
    assert len(flags) == 1 and flags[0]["kind"] == "spelling"
    assert flags[0]["suggestions"] == ["Consultancy", "Counsel"] and flags[0]["ai_suggestion"] == "Consultancy"


def test_a_known_word_is_not_traded_for_an_unknown_one():
    b = _block("keep the office", readings={"trocr": "keep the office"})
    assert _run(b, [("keep the offize", 0.9)])[0] == 0


def test_medicines_and_numbers_always_ask_for_confirmation():
    b = _block("Paracetamal 500 for 5 days", readings={"trocr": "Paracetamal 500 for 5 days"})
    _, flags = _run(b, [("Paracetamol 650 for 5 days", 0.9)])
    assert [f["suggestions"][0] for f in flags] == ["Paracetamol", "650"] and all(f["confirm"] for f in flags)
    assert "Confirm against the page" in flags[0]["reason"]


def test_the_ink_check_is_recorded_as_evidence():
    scores = {"Cousuleacy approved": -5.0, "Consultancy approved": -9.0}
    _, flags = _run(_block(), [("Consultancy approved", 0.9)], ink_score=lambda _c, ts: [scores[t] for t in ts])
    assert flags[0]["evidence"]["ink"] == "against" and "prefers the current word" in flags[0]["reason"]


def test_confident_clean_lines_and_signatures_are_not_sent_to_the_model():
    r = AIWordReviewer(FakeReader([("x", 0.9)]), lambda w: True)
    assert not r.needs_check(_block(confidence=0.99)) and not r.needs_check(_block(role="signature"))
    assert r.needs_check(_block(confidence=0.99, needs_review=True))


def test_alignment_and_enhanced_view():
    assert [(w["word"], alt) for w, alt in word_pairs("keep Ha office", "keep HQ office")] == [("Ha", "HQ")]
    assert enhanced_view(np.full((20, 100, 3), 200, np.uint8)).shape[0] == 64


def test_a_restyled_symbol_is_not_a_suggestion():
    b = _block("1) Radial Basis", readings={"trocr": "1) Radial Basis"})
    assert _run(b, [("\u2460 Radial Basis", 0.9)])[0] == 0


def test_drug_guess_needs_the_list_or_the_other_reader():
    b = _block("Tab Amlocal 5mg", readings={"trocr": "Tab Amlocal 5mg"})
    assert _run(b, [("Tab Amlopal 5mg", 0.9)])[0] == 0


def test_invented_text_is_recognised_only_when_unsure_and_unsupported():
    from app.ai.ocr.ocr_engine import unsupported_reading
    assert unsupported_reading("Lumona", 0.26, "Ane ho tarnytad") and unsupported_reading("Fexo-Ketri", 0.23, "")
    assert not unsupported_reading("Lumona", 0.9, "peanors")           # confident
    assert not unsupported_reading("Hexigel gum", 0.2, "Hexigel gun")  # the other reader backs it up
    assert not unsupported_reading("allow", 0.16, "me973", 0.94)       # the other reader is sure of something else
    assert not unsupported_reading("Dublin rd Athlone 0902", 0.3, "Dbh")  # long lines are usually mostly right


def test_scattered_handwriting_is_not_joined_but_table_rows_and_print_are():
    from app.ai.ocr.ocr_engine import ReadingOrderRebuilder
    def block(text, x0, y0, y1, source="handwritten"):
        return {"text": text, "bbox": [x0, y0, x0 + 80, y1], "confidence": 0.9, "source": source}
    rows = lambda bs: ReadingOrderRebuilder().rebuild_order(bs)[1].splitlines()
    assert rows([block("JEJUNUM", 0, 100, 130), block("BREAST FEEDING", 300, 108, 138)]) == ["JEJUNUM", "BREAST FEEDING"]
    assert rows([block("Cancer", 0, 100, 130), block("45", 300, 100, 130)]) == ["Cancer  45"]
    assert rows([block("Name", 0, 100, 130, "printed"), block("Date", 300, 108, 138, "printed")]) == ["Name  Date"]
