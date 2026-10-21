"""
app/services/ml/recommendation_engine.py — Unified Recommendation Orchestrator

Single entry point for all ML layer calls.
Structure:
  ├── rules layer    (always runs)
  ├── ml layer       (runs in shadow; promoted when confidence high)
  ├── confidence scoring
  ├── ranking layer
  └── fallback safety (if all fails → safe defaults)

Routes and other services call this file only — never call sub-services directly.

Public API:
  get_full_recommendation(user_id, user, db) → RecommendationResult
"""

from __future__ import annotations
from sqlalchemy.orm import Session

from app.models.user import User
from app.services.analytics.progress_aggregator import (
    get_best_and_worst_letters, get_rolling_average,
    get_weekly_accuracy, get_accuracy_trend, get_learning_velocity,
)
from app.services.analytics.engagement_analyzer import (
    get_practice_consistency, get_engagement_level, get_abandon_rate,
)
from app.services.analytics.confidence_analyzer import (
    get_hesitation_profile, get_retry_pattern, get_replay_dependence,
    get_recovery_patterns, get_frustration_level, get_confidence_level,
    get_direction_struggle,
)
from app.services.analytics.difficulty_trends import (
    get_difficulty_progression_summary, get_promotion_readiness,
)
from app.services.ml.feature_snapshot import build_feature_snapshot, snapshot_completeness
from app.services.ml.pattern_classifier import classify, STYLE_LABELS, STYLE_RECOMMENDATIONS
from app.services.ml.difficulty_predictor import predict as predict_difficulty
from app.services.ml.item_recommender import recommend_items
from app.services.ml.adaptive_session_planner import build_session_plan


# ──────────────────────────────────────────────────────────────────────────────
# Safe defaults — returned when data is too sparse
# ──────────────────────────────────────────────────────────────────────────────

_SAFE_DEFAULTS = {
    "learning_style":          "methodical",
    "style_label":             "Deliberate Learner",
    "style_recommendation":    "Keep practicing consistently",
    "recommended_difficulty":  "beginner",
    "recommended_items":       [],
    "session_plan":            {
        "items": [], "session_length_s": 300,
        "focus_mode": "standard", "reasoning": "Complete more sessions for personalization",
        "difficulty": "beginner", "confidence": 0.0, "source": "fallback",
        "learning_style": "unknown", "session_config": "Standard session",
    },
    "feature_snapshot":        {},
    "data_completeness":       0.0,
    "shadow_deltas":           [],
    "overall_confidence":      0.0,
    "source":                  "fallback",
}


# ──────────────────────────────────────────────────────────────────────────────
# Main engine
# ──────────────────────────────────────────────────────────────────────────────

def get_full_recommendation(
    user_id: int,
    user:    User,
    db:      Session,
    module_type: str = "alphabet_practice",
) -> dict:
    """
    Full recommendation pipeline:
      1. Gather analytics signals
      2. Build feature snapshot
      3. Classify learning style (shadow ML)
      4. Predict difficulty (shadow ML)
      5. Rank items
      6. Build session plan
      7. Assemble result with confidence + shadow_deltas
    """
    try:
        return _run_pipeline(user_id, user, db, module_type)
    except Exception:
        # Fallback safety: never crash the recommendation layer
        return dict(_SAFE_DEFAULTS)


def _run_pipeline(user_id: int, user: User, db: Session, module_type: str) -> dict:
    # ── 1. Gather signals ──────────────────────────────────────────────────────
    bw           = get_best_and_worst_letters(user_id, db)
    rolling      = get_rolling_average(user_id, module_type, db)
    weekly       = get_weekly_accuracy(user_id, module_type, db)
    trend        = get_accuracy_trend(weekly)
    velocity     = get_learning_velocity(user_id, module_type, db)
    consistency  = get_practice_consistency(user_id, db, days=14)
    abandon      = get_abandon_rate(user_id, db)
    hesitation   = get_hesitation_profile(user_id, db)
    retry        = get_retry_pattern(user_id, db)
    replay       = get_replay_dependence(user_id, db)
    recovery     = get_recovery_patterns(user_id, db)
    frustration  = get_frustration_level(hesitation, retry, replay)
    confidence   = get_confidence_level(hesitation, retry, frustration, recovery)
    direction    = get_direction_struggle(user_id, db)
    engagement   = get_engagement_level(consistency, abandon, user.user_streak or 0)
    diff_prog    = get_difficulty_progression_summary(user_id, module_type, db)
    promo        = diff_prog.get("promotion_readiness", 0.0)
    current_diff = diff_prog.get("current_difficulty", "beginner")
    streak       = user.user_streak or 0

    # ── 2. Feature snapshot ────────────────────────────────────────────────────
    snapshot = build_feature_snapshot(
        retry_pattern      = retry,
        hesitation_profile = hesitation,
        replay_dependence  = replay,
        consistency        = consistency,
        rolling_accuracy   = rolling,
        velocity           = velocity,
        frustration_level  = frustration,
        confidence_level   = confidence,
        trend              = trend,
        streak             = streak,
    )
    completeness = snapshot_completeness(snapshot)

    # ── 3. Learning style (shadow ML) ──────────────────────────────────────────
    style_result = classify(snapshot, completeness)
    style        = style_result["style"]
    shadow_deltas = [{"type": "learning_style", **style_result.get("shadow_delta", {})}]

    # ── 4. Difficulty prediction (shadow ML) ───────────────────────────────────
    diff_result  = predict_difficulty(
        snapshot            = snapshot,
        current_difficulty  = current_diff,
        rolling_accuracy    = rolling,
        trend               = trend,
        velocity            = velocity,
        promotion_readiness = promo,
        data_completeness   = completeness,
    )
    shadow_deltas.append({"type": "difficulty", **diff_result.get("shadow_delta", {})})

    # ── 5. Item ranking ────────────────────────────────────────────────────────
    items = recommend_items(
        worst_letters       = bw["worst"],
        high_retry_letters  = retry.get("high_retry_letters", []),
        direction_struggles = direction,
        frustration_level   = frustration,
        best_letters        = bw["best"],
        data_completeness   = completeness,
    )

    # ── 6. Session plan ────────────────────────────────────────────────────────
    plan = build_session_plan(
        recommended_items  = items,
        learning_style     = style,
        frustration_level  = frustration,
        engagement_level   = engagement,
        trend              = trend,
        rolling_accuracy   = rolling,
        difficulty         = diff_result["recommended_difficulty"],
        best_letters       = bw["best"],
        data_completeness  = completeness,
    )

    # ── 7. Overall confidence ──────────────────────────────────────────────────
    confidence_scores = [
        style_result["confidence"],
        diff_result["confidence"],
        completeness,
    ]
    overall_confidence = round(sum(confidence_scores) / len(confidence_scores), 4)

    return {
        "learning_style":         style,
        "style_label":            STYLE_LABELS.get(style, style),
        "style_recommendation":   STYLE_RECOMMENDATIONS.get(style, ""),
        "style_confidence":       style_result["confidence"],
        "style_source":           style_result["source"],
        "recommended_difficulty": diff_result["recommended_difficulty"],
        "difficulty_confidence":  diff_result["confidence"],
        "difficulty_source":      diff_result["source"],
        "recommended_items":      items,
        "session_plan":           plan,
        "feature_snapshot":       snapshot,
        "data_completeness":      completeness,
        "shadow_deltas":          shadow_deltas,
        "overall_confidence":     overall_confidence,
        "source":                 "recommendation_engine_v1",
    }
