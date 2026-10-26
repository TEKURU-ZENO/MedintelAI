"""
Recogniser ensemble for uncertain handwritten lines: PP-OCRv6 (RapidOCR) vs the medical TrOCR model.

Each engine reads the same rectified line crop. The reading with the higher combined score wins:
    score = conf_weight * calibrated_confidence + validity_weight * word_validity
where word_validity is the share of words that are real (drug / clinical lexicon, common English, dose and
frequency tokens) and confidences are put on a common scale per engine. The weights and the TrOCR
confidence scale are fitted on validation data (scripts/collect_ensemble_candidates.py) and stored in
ENSEMBLE_PARAMS; see docs/HTR_TRAINING.md for the measured effect.
"""
import os
from typing import Callable, Dict, Tuple

# Fitted (scripts/fit_ensemble.py) on validation crops from GNHK, IAM, RxHandBD, Kaggle Rx BD, FUNSD
# scanned print and synthetic print, jointly with the routing threshold below. Held-out test macro CER:
#   PP-OCRv6 only 0.176 | TrOCR only 0.075 | routed ensemble (threshold 0.97) 0.0675 | ensemble on all 0.0647
ENSEMBLE_PARAMS: Dict[str, float] = {
    "trocr_conf_scale": 2.5,   # TrOCR geometric-mean token probability runs lower than PP-OCR's score
    "conf_weight": 1.0,
    "validity_weight": 0.2,
    "rapid_bias": -0.1,        # added to the RapidOCR score (negative = prefer TrOCR on handwriting)
}

# Lines PP-OCR reads with at least this confidence take the fast printed path; everything else goes
# through the ensemble. HTR_PRINTED_CONF=1.01 sends every line through the ensemble (most accurate,
# runs TrOCR on printed lines too: best with a GPU).
PRINTED_CONF_THRESHOLD = float(os.getenv("HTR_PRINTED_CONF", "0.97"))


# Raw engine confidence -> expected character accuracy (binned validation means, made monotone).
# Held-out test: mean predicted 0.847 vs actual 0.843 (PP-OCR), 0.932 vs 0.922 (TrOCR).
CALIBRATION: Dict[str, Dict[str, list]] = {
    "rapid": {"x": [0.5719, 0.805, 0.8897, 0.9406, 0.9643, 0.981, 0.9912, 0.9976, 0.9998, 1.0],
              "y": [0.4289, 0.6649, 0.7908, 0.878, 0.9132, 0.9419, 0.9655, 0.9655, 0.9774, 0.9977]},
    "trocr": {"x": [0.25, 0.4263, 0.5351, 0.6449, 0.7377, 0.8027, 0.856, 0.8941, 0.9204, 0.9467],
              "y": [0.727, 0.857, 0.9236, 0.9349, 0.9581, 0.9834, 0.9889, 0.9972, 0.9994, 0.9994]},
}


ENSEMBLE_FILENAME = "ensemble.json"


def configure_from(model_dir, device: str = "cpu") -> bool:
    """
    Loads the selection rule, routing threshold and calibration fitted for a specific TrOCR checkpoint
    (written by scripts/fit_ensemble.py --install). On CPU the faster "cpu" profile is used when present;
    HTR_PRINTED_CONF still overrides the threshold. Returns True when a fitted configuration was found.
    """
    global PRINTED_CONF_THRESHOLD
    import json
    if not model_dir:
        return False
    path = os.path.join(str(model_dir), ENSEMBLE_FILENAME)
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        profile = cfg.get("cpu", cfg) if device != "cuda" else cfg
        ENSEMBLE_PARAMS.update({k: float(v) for k, v in profile.get("params", {}).items()})
        for engine, table in cfg.get("calibration", {}).items():
            if table.get("x") and table.get("y"):
                CALIBRATION[engine] = {"x": list(table["x"]), "y": list(table["y"])}
        if "printed_conf_threshold" in profile and "HTR_PRINTED_CONF" not in os.environ:
            PRINTED_CONF_THRESHOLD = float(profile["printed_conf_threshold"])
        return True
    except Exception:
        return False


def calibrate(conf: float, engine: str) -> float:
    """Maps an engine's raw confidence to its expected character accuracy."""
    import numpy as np
    table = CALIBRATION[engine]
    return float(np.interp(conf, table["x"], table["y"]))


def combined_score(text: str, conf: float, engine: str, validity: Callable[[str], float],
                   params: Dict[str, float] = ENSEMBLE_PARAMS) -> float:
    if not text or not text.strip():
        return -1.0
    c = min(1.0, conf * params["trocr_conf_scale"]) if engine == "trocr" else conf
    s = params["conf_weight"] * c + params["validity_weight"] * validity(text)
    if engine == "rapid":
        s += params["rapid_bias"]
    return s


def choose(rapid: Tuple[str, float], trocr: Tuple[str, float], validity: Callable[[str], float],
           params: Dict[str, float] = ENSEMBLE_PARAMS) -> Tuple[str, float, str]:
    """Returns (text, calibrated confidence, engine) for the better of the two readings."""
    # On forms TrOCR can read a checkbox glyph next to a label as a lone character ("4 Denied", "1 Dementia");
    # when its reading is exactly PP-OCR's plus such a token, the extra token is noise
    t_words, r_text = trocr[0].split(), rapid[0].strip()
    if r_text and len(t_words) >= 2 and len(t_words[0]) == 1 and " ".join(t_words[1:]).lower() == r_text.lower():
        return rapid[0], calibrate(rapid[1], "rapid"), "rapid"
    rs = combined_score(rapid[0], rapid[1], "rapid", validity, params)
    ts = combined_score(trocr[0], trocr[1], "trocr", validity, params)
    if ts > rs:
        return trocr[0], calibrate(trocr[1], "trocr"), "trocr"
    return rapid[0], calibrate(rapid[1], "rapid"), "rapid"
