"""Model-free tests for image-checked spelling correction: a fake language model and a fake ink score."""
import pytest

pytest.importorskip("symspellpy")

from app.ai.ocr.htr_language_model import ContextSpellCorrector  # noqa: E402


def _corrector(lm_scores, **params):
    c = ContextSpellCorrector(params={"channel_weight": 1.0, "freq_weight": 0.0, "margin": 1.0, **params})
    c.sentence_logprobs = lambda lines: [lm_scores.get(l, -50.0) for l in lines]
    return c


LINE = "this is a buanch of trees"
LM = {LINE: -40.0, "this is a branch of trees": -20.0, "this is a bunch of trees": -20.5}


def test_text_only_correction_is_unchanged_without_an_image():
    text, changes = _corrector(LM).correct_line(LINE)
    assert text == "this is a branch of trees" and "image_gain" not in changes[0]


def test_the_ink_can_veto_a_correction():
    ink = {LINE: -10.0, "this is a branch of trees": -30.0, "this is a bunch of trees": -31.0}
    c = _corrector(LM, image_weight=0.5, image_veto=5.0)
    text, changes = c.correct_line(LINE, image_score=lambda lines: [ink.get(l, -60.0) for l in lines])
    assert text == LINE and changes == []


def test_the_ink_picks_between_candidates_the_text_rates_alike():
    ink = {LINE: -12.0, "this is a branch of trees": -25.0, "this is a bunch of trees": -11.0}
    c = _corrector(LM, image_weight=1.0, image_veto=5.0)
    text, changes = c.correct_line(LINE, image_score=lambda lines: [ink.get(l, -60.0) for l in lines])
    assert text == "this is a bunch of trees" and changes[0]["image_gain"] == 1.0


def test_image_score_is_ignored_when_not_fitted_or_failing():
    def broken(_lines):
        raise RuntimeError("no GPU")
    assert _corrector(LM).correct_line(LINE, image_score=broken)[0] == "this is a branch of trees"
    assert _corrector(LM, image_weight=1.0).correct_line(LINE, image_score=broken)[0] == "this is a branch of trees"


def _reading_corrector(lm_scores, **params):
    c = ContextSpellCorrector(protected_terms=["hexigel", "augmentin"], params={"reading_margin": 3.0, **params})
    c.sentence_logprobs = lambda lines: [lm_scores.get(l, -50.0) for l in lines]
    return c


def test_the_other_reading_wins_when_the_line_prefers_it():
    c = _reading_corrector({"Hexigel gun paint": -30.0, "Hexigel gum paint": -22.0})
    text, changes = c.choose_reading("Hexigel gun paint", "Hexigel gum paint")
    assert text == "Hexigel gum paint" and changes[0]["reason"] == "other reading"


def test_the_other_reading_needs_the_margin_and_a_real_word():
    c = _reading_corrector({"Hexigel gun paint": -30.0, "Hexigel gum paint": -28.0})
    assert c.choose_reading("Hexigel gun paint", "Hexigel gum paint")[0] == "Hexigel gun paint"
    assert c.reading_swaps("Hexigel gun paint", "Hexigel gxq paint") == []  # not a word: no swap offered


def test_a_drug_name_is_never_traded_for_an_english_word():
    c = _reading_corrector({"Tab Augmentin 625mg": -40.0, "Tab argument 625mg": -10.0})
    assert c.reading_swaps("Tab Augmentin 625mg", "Tab argument 625mg") == []


def test_garbled_other_reading_offers_nothing():
    assert _reading_corrector({}).reading_swaps("Hexigel gum paint", "xx yy zz qq") == []


def test_an_unknown_word_takes_the_drug_the_other_reader_ran_into_its_dose():
    c = ContextSpellCorrector(protected_terms=["Pan-D", "Augmentin"], params={"reading_margin": 3.0})
    c.sentence_logprobs = lambda lines: [-50.0 for _ in lines]
    text, changes = c.choose_reading("before & Tab ParID 40mg", "befece Tab. PanD40nmg")
    assert text == "before & Tab Pan-D 40mg" and changes == [{"from": "ParID", "to": "Pan-D", "reason": "drug in other reading"}]
    assert c.drug_swaps("Tab Pantop 40mg", "Tab. PanD40nmg") == []        # too far from the drug: kept
    assert c.drug_swaps("Tab Pan-D 40mg", "Tab. PanD40nmg") == []         # already there


def test_a_clinical_term_needs_less_language_model_support():
    lm = {"Adv: Hexigel gun paint": -30.0, "Adv: Hexigel gum paint": -32.0}
    plain = _reading_corrector(lm, clinical_prior=0.0)
    clinical = _reading_corrector(lm, clinical_prior=6.0)
    assert plain.choose_reading("Adv: Hexigel gun paint", "Adv: Hexigel gum paint")[0] == "Adv: Hexigel gun paint"
    assert clinical.choose_reading("Adv: Hexigel gun paint", "Adv: Hexigel gum paint")[0] == "Adv: Hexigel gum paint"
    assert clinical.choose_reading("Adv: Hexigel gum paint", "Adv: Hexigel gun paint")[0] == "Adv: Hexigel gum paint"
