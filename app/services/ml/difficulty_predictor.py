"""
app/services/ml/difficulty_predictor.py — Next Difficulty Prediction

Shadow ML pattern: rule version + ML weighted version run in parallel.
ML is advisor only — rule output is production output when ML confidence is low.

Outputs:
  {
    "recommended_difficulty": str,
    "confidence": float,
    "source": "rule" | "ml",
    "shadow_delta": {...},
  }
"""

from __future__ import annotations
from typing import Literal

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
DIFFICULTY_ORDER: list[str] = ["beginner", "intermediate", "advanced"]

# Thresholds (mirrors difficulty_adapter.py)
PROMOTE_THRESHOLD = 0.85
DEMOTE_THRESHOLD  = 0.50


# ── Rule predictor (deterministic) ────────────────────────────────────────────

def predict_rule(
    rolling_accuracy: float,
    trend:            str,
    velocity:         str,
    current_difficulty: str,
    promotion_readiness: float,
) -> dict:
    """Exact threshold logic — always explainable."""
    idx = DIFFICULTY_ORDER.index(current_difficulty) if current_difficulty in DIFFICULTY_ORDER else 0

    if rolling_accuracy >= PROMOTE_THRESHOLD and trend != "declining":
        next_idx = min(idx + 1, len(DIFFICULTY_ORDER) - 1)
        reason = "Accuracy consistently above promotion threshold"
    elif rolling_accuracy <= DEMOTE_THRESHOLD or trend == "declining":
        next_idx = max(idx - 1, 0)
        reason = "Accuracy below threshold or declining trend"
    else:
        next_idx = idx
        reason = "Accuracy in acceptable range — maintain current level"

    return {
        "recommended_difficulty": DIFFICULTY_ORDER[next_idx],
        "confidence":            0.90,
        "source":                "rule",
        "reason":                reason,
    }


# ── ML predictor (weighted scoring) ───────────────────────────────────────────

def predict_ml(snapshot: dict, data_completeness: float = 1.0) -> dict:
    """
    Weighted linear model for difficulty prediction.
    Outputs a continuous score → mapped to difficulty level.

    score > 0.75 → promote
    score < 0.35 → demote
    else         → maintain
    """
    # Weighted formula (interpretable — not a black box)
    weights = {
        "rolling_accuracy":  0.40,
        "trend_score":       0.25,
        "velocity_score":    0.15,
        "confidence_score":  0.10,
        "consistency_score": 0.10,
    }

    score = sum(
        snapshot.get(feat, 0.5) * w
        for feat, w in weights.items()
    )
    score = max(0.0, min(1.0, score))

    # Map to direction
    if score > 0.72:
        direction = "promote"
    elif score < 0.35:
        direction = "demote"
    else:
        direction = "maintain"

    # Translate to difficulty level — needs current level from caller
    current = snapshot.get("_current_difficulty", "beginner")
    idx     = DIFFICULTY_ORDER.index(current) if current in DIFFICULTY_ORDER else 0
    if direction == "promote":
        next_idx = min(idx + 1, len(DIFFICULTY_ORDER) - 1)
    elif direction == "demote":
        next_idx = max(idx - 1, 0)
    else:
        next_idx = idx

    # Distance from threshold = confidence proxy
    if direction == "promote":
        raw_conf = (score - 0.72) / 0.28
    elif direction == "demote":
        raw_conf = (0.35 - score) / 0.35
    else:
        raw_conf = 1.0 - abs(score - 0.535) * 2.0

    confidence = round(max(0.25, min(0.95, data_completeness * raw_conf)), 4)

    return {
        "recommended_difficulty": DIFFICULTY_ORDER[next_idx],
        "confidence":            confidence,
        "source":                "ml",
        "ml_score":              round(score, 4),
        "direction":             direction,
    }


# ── Shadow predictor ──────────────────────────────────────────────────────────

def predict(
    snapshot:            dict,
    current_difficulty:  str,
    rolling_accuracy:    float,
    trend:               str,
    velocity:            str,
    promotion_readiness: float,
    data_completeness:   float = 1.0,
) -> dict:
    """
    Shadow ML: runs both rule and ML, logs delta.
    Returns ML if confidence ≥ 0.65, else rule.
    """
    ML_THRESHOLD = 0.65
    snapshot["_current_difficulty"] = current_difficulty

    rule = predict_rule(rolling_accuracy, trend, velocity, current_difficulty, promotion_readiness)
    ml   = predict_ml(snapshot, data_completeness)

    shadow_delta = {
        "rule_difficulty": rule["recommended_difficulty"],
        "ml_difficulty":   ml["recommended_difficulty"],
        "agreement":       rule["recommended_difficulty"] == ml["recommended_difficulty"],
        "ml_score":        ml.get("ml_score"),
        "ml_confidence":   ml["confidence"],
    }

    if ml["confidence"] >= ML_THRESHOLD:
        chosen = dict(ml)
    else:
        chosen = dict(rule)

    chosen["shadow_delta"] = shadow_delta
    return chosen
