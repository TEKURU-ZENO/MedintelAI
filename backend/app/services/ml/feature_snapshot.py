"""
app/services/ml/feature_snapshot.py — Structured Feature Extraction

Converts analytics signals into a flat, normalized feature vector.
This is the future training data source — every snapshot stored becomes
a labeled example when the user's outcome is known.

Output contract:
  {
    "retry_rate":        float 0-1,
    "avg_hesitation_ms": float,
    "replay_rate":       float 0-1,
    "failsafe_rate":     float 0-1,
    "consistency_score": float 0-1,
    "streak":            int,
    "rolling_accuracy":  float 0-1,
    "velocity_score":    float 0-1,   # fast=1.0 steady=0.5 slow=0.0
    "frustration_score": float 0-1,   # high=1.0 medium=0.5 low=0.0
    "confidence_score":  float 0-1,   # high=1.0 medium=0.5 low=0.0 unknown=0.25
    "trend_score":       float 0-1,   # improving=1.0 stable=0.5 declining=0.0
    "has_telemetry":     bool,
  }
"""

from __future__ import annotations


# ──────────────────────────────────────────────────────────────────────────────
# Normalizers (map categorical → float)
# ──────────────────────────────────────────────────────────────────────────────

_VELOCITY = {"fast": 1.0, "steady": 0.5, "slow": 0.0}
_FRUSTRATION = {"low": 0.0, "medium": 0.5, "high": 1.0}
_CONFIDENCE  = {"high": 1.0, "medium": 0.5, "low": 0.0, "unknown": 0.25}
_TREND       = {"improving": 1.0, "stable": 0.5, "declining": 0.0}


def build_feature_snapshot(
    retry_pattern:      dict,
    hesitation_profile: dict,
    replay_dependence:  dict,
    consistency:        dict,
    rolling_accuracy:   float,
    velocity:           str,
    frustration_level:  str,
    confidence_level:   str,
    trend:              str,
    streak:             int,
) -> dict:
    """
    Produces a normalized, flat feature dict from analytics signals.
    Safe to call even when signals are empty (graceful defaults).
    """
    # Clamp helper
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, round(v, 4)))

    # Normalize hesitation: cap at 5000ms as max reference
    avg_hes = hesitation_profile.get("avg_pause_between_strokes_ms", 0)
    hes_norm = _clamp(avg_hes / 5000.0)

    has_telemetry = (
        retry_pattern.get("has_data", False)
        or hesitation_profile.get("has_data", False)
    )

    return {
        "retry_rate":        _clamp(retry_pattern.get("avg_retries_per_stroke", 0.0) / 5.0),
        "avg_hesitation_ms": float(avg_hes),
        "hesitation_norm":   hes_norm,
        "replay_rate":       _clamp(replay_dependence.get("replay_rate", 0.0)),
        "failsafe_rate":     _clamp(retry_pattern.get("failsafe_unlock_rate", 0.0)),
        "consistency_score": _clamp(consistency.get("consistency_score", 0.0)),
        "streak":            max(0, streak),
        "rolling_accuracy":  _clamp(rolling_accuracy),
        "velocity_score":    _VELOCITY.get(velocity, 0.5),
        "frustration_score": _FRUSTRATION.get(frustration_level, 0.0),
        "confidence_score":  _CONFIDENCE.get(confidence_level, 0.25),
        "trend_score":       _TREND.get(trend, 0.5),
        "has_telemetry":     has_telemetry,
    }


def snapshot_completeness(snapshot: dict) -> float:
    """
    Returns 0.0-1.0: how complete this snapshot's data is.
    Used as confidence multiplier in ML predictions.
    """
    if not snapshot.get("has_telemetry"):
        return 0.3   # low completeness → ML falls back to rules

    score = 0.3  # base (rolling_accuracy + consistency always available)
    if snapshot.get("retry_rate", 0) > 0:
        score += 0.2
    if snapshot.get("avg_hesitation_ms", 0) > 0:
        score += 0.2
    if snapshot.get("replay_rate", 0) > 0:
        score += 0.15
    if snapshot.get("streak", 0) > 0:
        score += 0.15
    return round(min(1.0, score), 4)
