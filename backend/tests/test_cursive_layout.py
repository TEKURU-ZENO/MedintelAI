"""Model-free tests for messy handwriting: line straightening, line ends, braces, stacked lines, reader fusion."""
import cv2
import numpy as np
import pytest

from app.ai.ocr.document_layout import find_separators
from app.ai.ocr.htr_layout import HandwritingLineBuilder, straighten_line
from app.ai.ocr.ocr_engine import ReadingOrderRebuilder


def _text_strip(rows, w=420, h=110):
    img = np.full((h, w, 3), 245, dtype=np.uint8)
    for y in rows:
        cv2.putText(img, "minimum class label", (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (30, 30, 30), 2)
    return img


def test_a_line_with_neighbours_is_followed_and_cut_out():
    crop = _text_strip([18, 62, 106])
    out = straighten_line(crop)
    assert out is not crop and out.shape[1] == crop.shape[1] and out.shape[0] < 0.8 * crop.shape[0]


def test_a_clean_line_is_returned_as_is():
    crop = _text_strip([40], h=56)
    assert straighten_line(crop) is crop


def _quad(x0, y0, x1, y1, rise=0.0):
    return np.array([[x0, y0], [x1, y0 - rise], [x1, y1 - rise], [x0, y1]], dtype=np.float32)


def test_the_last_word_of_a_curving_line_rejoins_it():
    line = _quad(0, 100, 1000, 140, rise=60)     # climbs to the right; its end is at y 40-80
    last = _quad(1005, 40, 1070, 80)             # far from the line's centre, but right at its end
    assert sorted(map(sorted, HandwritingLineBuilder.merge_into_lines([line, last]))) == [[0, 1]]


def test_the_next_line_down_does_not_join_at_the_end():
    line = _quad(0, 100, 1000, 140, rise=60)
    below = _quad(1005, 110, 1070, 150)
    assert len(HandwritingLineBuilder.merge_into_lines([line, below])) == 2


def _page_with_stroke(xs, ys):
    page = np.full((1000, 800, 3), 255, dtype=np.uint8)
    cv2.polylines(page, [np.array(list(zip(xs, ys)), dtype=np.int32)], False, (0, 0, 0), 2)
    return page


def test_a_brace_is_a_separator_but_the_page_edge_is_not():
    ys = np.arange(200, 330)
    brace = (400 + 12 * np.sin((ys - 200) / 20.0)).astype(int)
    assert len(find_separators(_page_with_stroke(brace, ys), 40)) == 1
    edge = (780 + 12 * np.sin((ys - 200) / 20.0)).astype(int)
    assert find_separators(_page_with_stroke(edge, ys), 40) == []


def _block(text, bbox, source="handwritten", **extra):
    return {"text": text, "bbox": bbox, "source": source, **extra}


def test_a_list_gathered_into_one_row_by_a_side_note_is_unstacked():
    blocks = [_block("- classification", [80, 100, 270, 140]), _block("- clustering", [75, 118, 230, 158]),
              _block("- neural network", [75, 136, 270, 176]), _block("solve problem after", [500, 112, 800, 160])]
    _, text = ReadingOrderRebuilder().rebuild_order(blocks)
    assert text.split("\n") == ["- classification", "- clustering", "- neural network", "solve problem after"]


def test_a_note_wrapped_over_two_lines_stays_together():
    blocks = [_block("after", [80, 100, 170, 140]), _block("meals", [80, 118, 170, 158])]
    assert ReadingOrderRebuilder().rebuild_order(blocks)[1] == "after  meals"


def test_cells_at_one_height_stay_in_one_row():
    blocks = [_block("Tab Pan-D", [80, 100, 270, 140]), _block("40 mg", [290, 102, 380, 142])]
    assert ReadingOrderRebuilder().rebuild_order(blocks)[1] == "Tab Pan-D  40 mg"


def test_text_after_a_brace_starts_its_own_row():
    blocks = [_block("- language processing", [80, 100, 370, 140]),
              _block("mimic human", [400, 100, 610, 140], _after_separator=True)]
    assert ReadingOrderRebuilder().rebuild_order(blocks)[1].split("\n") == ["- language processing", "mimic human"]


def _fuser(**kwargs):
    pytest.importorskip("symspellpy")
    from app.ai.ocr.htr_language_model import ContextSpellCorrector
    c = ContextSpellCorrector(params={"fusion_weight": 3.0, "fusion_margin": 2.0}, **kwargs)
    c.sentence_logprobs = lambda lines: [-40.0 + 5 * ("maximum" in l) + 5 * ("class" in l) for l in lines]
    return c


def test_a_fluent_wrong_word_gives_way_to_what_the_other_reader_saw():
    text, changes = _fuser().fuse_readings("space to minimum exact", "spase to maximom ciass")
    assert text == "space to maximum class" and {c["to"] for c in changes} == {"maximum", "class"}


def test_fusion_is_off_until_fitted():
    c = _fuser()
    c.params["fusion_margin"] = 1e9
    assert c.fuse_readings("space to minimum exact", "spase to maximom ciass") == ("space to minimum exact", [])


def test_fusion_leaves_drugs_and_words_beside_doses_alone():
    c = _fuser(protected_terms=["Pantop"])
    assert c.fuse_readings("take Pantop with class", "take maximum with class")[0] == "take Pantop with class"
    assert c.fuse_readings("Tab Zerodol 100 mg", "Tab maximum 100 mg")[0] == "Tab Zerodol 100 mg"


def test_fusion_leaves_instructions_names_and_labels_alone():
    c = _fuser()
    assert c.fuse_readings("Paracetamol 100 mg with food", "Paracetamol 100 mg with class")[0] \
        == "Paracetamol 100 mg with food"
    assert c.fuse_readings("seen by Dr Exact today", "seen by Dr class today")[0] == "seen by Dr Exact today"
    assert c.fuse_readings("exact: seen today", "class: seen today")[0] == "exact: seen today"
    assert c.fuse_readings("EXACT seen today", "class seen today")[0] == "EXACT seen today"
