"""
app/services/ml/pattern_classifier.py — Learning Style Classification

Classifies a learner into one of 4 behavioral styles using weighted
feature scoring. No ML libraries — pure Python dot-product + normalization.

Styles:
  visual        — learns by watching/replay, high replay_rate, fast recovery
  methodical    — low retries, slow pace, deliberate, low frustration
  impulsive     — high retries, fast velocity, low hesitation
  replay-dependent — high replay, slow recovery, medium-high frustration

Shadow ML pattern:
  classify_rule(snapshot)  → deterministic rule classification
  classify_ml(snapshot)    → weighted scoring classification
  classify(snapshot)       → runs both, returns ml result + delta logged
"""

from __future__ import annotations
from typing import Literal

LearningStyle = Literal["visual", "methodical", "impulsive", "replay_dependent"]

# ── Weight matrices (row = style, col = feature) ──────────────────────────────
# Features: [retry_rate, hesitation_norm, replay_rate, velocity_score,
#            frustration_score, consistency_score, confidence_score, trend_score]

_STYLE_WEIGHTS: dict[str, list[float]] = {
    "visual":           [-0.1,  0.2,  0.5,  0.1, -0.1,  0.1,  0.2,  0.2],
    "methodical":       [-0.3, -0.1, -0.2, -0.2, -0.3,  0.4,  0.4,  0.3],
    "impulsive":        [ 0.4, -0.3, -0.1,  0.4,  0.2, -0.1, -0.1, -0.1],
    "replay_dependent": [ 0.2,  0.2,  0.4, -0.1,  0.3, -0.2, -0.3, -0.1],
}

_FEATURE_KEYS = [
    "retry_rate", "hesitation_norm", "replay_rate", "velocity_score",
    "frustration_score", "consistency_score", "confidence_score", "trend_score",
]


def _feature_vector(snapshot: dict) -> list[float]:
    return [snapshot.get(k, 0.0) for k in _FEATURE_KEYS]


def _dot(weights: list[float], features: list[float]) -> float:
    return sum(w * f for w, f in zip(weights, features))


def _softmax(scores: dict[str, float]) -> dict[str, float]:
    """Normalize raw scores to probabilities (0-1, sum ≈ 1)."""
    import math
    exp_scores = {k: math.exp(v) for k, v in scores.items()}
    total = sum(exp_scores.values())
    return {k: round(v / total, 4) for k, v in exp_scores.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Rule-based classifier (deterministic — the "control" branch)
# ──────────────────────────────────────────────────────────────────────────────

def classify_rule(snapshot: dict) -> dict:
    """
    Fast deterministic classification using explicit thresholds.
    Always returns a result regardless of data quality.
    """
    retry    = snapshot.get("retry_rate", 0.0)
    replay   = snapshot.get("replay_rate", 0.0)
    velocity = snapshot.get("velocity_score", 0.5)
    hesitation = snapshot.get("hesitation_norm", 0.0)
    frustration = snapshot.get("frustration_score", 0.0)
    consistency = snapshot.get("consistency_score", 0.5)

    # Priority: most specific rules first
    if replay > 0.35 and frustration > 0.4:
        style: LearningStyle = "replay_dependent"
    elif replay > 0.25 and snapshot.get("confidence_score", 0.5) > 0.5:
        style = "visual"
    elif retry > 0.40 and velocity > 0.7:
        style = "impulsive"
    elif hesitation < 0.25 and consistency > 0.55 and frustration < 0.4:
        style = "methodical"
    elif replay > 0.15:
        style = "visual"
    elif retry > 0.30:
        style = "impulsive"
    else:
        style = "methodical"   # default: deliberate learner

    return {
        "style":      style,
        "confidence": 0.75 if snapshot.get("has_telemetry") else 0.40,
        "source":     "rule",
        "probabilities": {style: 1.0},   # rules are binary
    }


# ──────────────────────────────────────────────────────────────────────────────
# ML-style weighted scorer (the "advisor" branch)
# ──────────────────────────────────────────────────────────────────────────────

def classify_ml(snapshot: dict, data_completeness: float = 1.0) -> dict:
    """
    Weighted feature scoring with soft probabilities.
    More nuanced than rules — but less reliable with sparse data.
    """
    features = _feature_vector(snapshot)
    raw_scores = {
        style: _dot(weights, features)
        for style, weights in _STYLE_WEIGHTS.items()
    }
    probs = _softmax(raw_scores)
    best_style = max(probs, key=lambda k: probs[k])

    # Confidence = completeness × top probability (higher = more certain)
    top_prob    = probs[best_style]
    second_prob = sorted(probs.values(), reverse=True)[1]
    separation  = top_prob - second_prob   # how dominant the top style is

    raw_confidence = data_completeness * (0.5 + separation * 0.5)
    confidence = round(min(0.95, max(0.20, raw_confidence)), 4)

    return {
        "style":         best_style,
        "confidence":    confidence,
        "source":        "ml",
        "probabilities": probs,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Shadow classifier — runs both, logs delta, returns ML (if confident)
# ──────────────────────────────────────────────────────────────────────────────

def classify(
    snapshot: dict,
    data_completeness: float = 1.0,
) -> dict:
    """
    Shadow ML pattern:
      1. Run rule classifier (always safe)
      2. Run ML classifier (confidence-gated)
      3. If ML confidence ≥ threshold → return ML result
      4. Else → return rule result
      5. Always include shadow_delta for monitoring

    Returns:
      {style, confidence, source, probabilities, shadow_delta}
    """
    ML_CONFIDENCE_THRESHOLD = 0.55

    rule_result = classify_rule(snapshot)
    ml_result   = classify_ml(snapshot, data_completeness)

    shadow_delta = {
        "rule_style":  rule_result["style"],
        "ml_style":    ml_result["style"],
        "agreement":   rule_result["style"] == ml_result["style"],
        "ml_confidence": ml_result["confidence"],
    }

    if ml_result["confidence"] >= ML_CONFIDENCE_THRESHOLD:
        chosen = dict(ml_result)
    else:
        chosen = dict(rule_result)

    chosen["shadow_delta"] = shadow_delta
    return chosen


# ── Human-readable labels ──────────────────────────────────────────────────────

STYLE_LABELS = {
    "visual":          "Visual Learner — benefits from guided replay",
    "methodical":      "Methodical Learner — deliberate and consistent",
    "impulsive":       "Active Learner — benefits from slowing down",
    "replay_dependent": "Replay-Dependent — needs guided repetition",
}

STYLE_RECOMMENDATIONS = {
    "visual":          "Use ghost replay for new strokes before attempting",
    "methodical":      "Maintain current pace — try advancing difficulty",
    "impulsive":       "Focus on one stroke at a time before moving on",
    "replay_dependent": "Short daily sessions with replay assistance enabled",
}
