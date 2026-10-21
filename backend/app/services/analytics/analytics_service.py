"""
app/services/analytics/analytics_service.py — Central Analytics Orchestrator

Single entry point for all analytics. Never called directly by routes —
routes call functions here, passing (user_id, db).

Responsibilities:
  - Calls sub-services to gather raw signals
  - Calls learning_insight_engine to convert signals → InsightItems
  - Assembles and returns clean DTOs
  - Never does string formatting or business interpretation itself

Sub-service call order:
  1. progress_aggregator    (weekly/rolling accuracy)
  2. engagement_analyzer    (streak, consistency, duration)
  3. difficulty_trends      (promotion readiness)
  4. confidence_analyzer    (hesitation, retry, frustration, replay, recovery)
  5. learning_insight_engine (signals → InsightItem[])
  → assemble DTOs
"""

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.practice_session import PracticeSession
from sqlalchemy import func

from app.services.analytics.progress_aggregator import (
    get_weekly_accuracy,
    get_accuracy_trend,
    get_learning_velocity,
    get_rolling_average,
    get_best_and_worst_letters,
    get_total_sessions,
    get_active_days_this_week,
)
from app.services.analytics.engagement_analyzer import (
    get_streak_context,
    get_session_duration_stats,
    get_abandon_rate,
    get_practice_consistency,
    get_engagement_level,
)
from app.services.analytics.difficulty_trends import (
    get_difficulty_progression_summary,
    get_promotion_readiness,
)
from app.services.analytics.confidence_analyzer import (
    get_hesitation_profile,
    get_retry_pattern,
    get_frustration_level,
    get_replay_dependence,
    get_recovery_patterns,
    get_confidence_level,
    get_direction_struggle,
)
from app.services.analytics.learning_insight_engine import (
    generate_strength_insights,
    generate_weakness_insights,
    generate_behavioral_insights,
    generate_recommended_focus,
)


# ──────────────────────────────────────────────────────────────────────────────

def get_dashboard_summary(user_id: int, user: User, db: Session) -> dict:
    """
    Home-screen analytics snapshot.
    Fast: only computes what's needed for the summary card.
    """
    # Engagement
    streak_ctx  = get_streak_context(user)
    consistency = get_practice_consistency(user_id, db, days=7)
    abandon     = get_abandon_rate(user_id, db)
    engagement  = get_engagement_level(consistency, abandon, streak_ctx["current_streak"])

    # Progress
    weekly   = get_weekly_accuracy(user_id, None, db)
    trend    = get_accuracy_trend(weekly)
    rolling  = get_rolling_average(user_id, None, db)
    total    = get_total_sessions(user_id, db)
    act_days = get_active_days_this_week(user_id, db)

    # Difficulty
    diff_prog   = get_difficulty_progression_summary(user_id, "alphabet_practice", db)
    readiness   = diff_prog.get("promotion_readiness", 0.0)
    current_diff = diff_prog.get("current_difficulty", "beginner")

    # Confidence & frustration (lightweight — reuses retry only)
    retry       = get_retry_pattern(user_id, db, limit=10)
    hesitation  = get_hesitation_profile(user_id, db, limit=10)
    replay      = get_replay_dependence(user_id, db, limit=10)
    frustration = get_frustration_level(hesitation, retry, replay)
    recovery    = get_recovery_patterns(user_id, db, limit=10)
    confidence  = get_confidence_level(hesitation, retry, frustration, recovery)

    return {
        "current_streak":        streak_ctx["current_streak"],
        "streak_status":         streak_ctx["streak_status"],
        "engagement_level":      engagement,
        "confidence_level":      confidence,
        "frustration_level":     frustration,
        "rolling_accuracy":      rolling,
        "accuracy_trend":        trend,
        "current_difficulty":    current_diff,
        "promotion_readiness":   readiness,
        "total_sessions":        total,
        "total_xp":              user.xp_points or 0,
        "level":                 user.level or 1,
        "active_days_this_week": act_days,
    }


def get_progress_report(
    user_id: int,
    module_type: str,
    db: Session,
) -> dict:
    """Progress trend for a specific module."""
    weekly   = get_weekly_accuracy(user_id, module_type, db)
    trend    = get_accuracy_trend(weekly)
    velocity = get_learning_velocity(user_id, module_type, db)
    rolling  = get_rolling_average(user_id, module_type, db)
    bw       = get_best_and_worst_letters(user_id, db)

    return {
        "module_type":    module_type,
        "weekly_accuracy": weekly,
        "trend":          trend,
        "velocity":       velocity,
        "rolling_average": rolling,
        "best_letters":   bw["best"],
        "worst_letters":  bw["worst"],
    }


def get_engagement_report(user_id: int, user: User, db: Session) -> dict:
    """Full engagement metrics."""
    streak_ctx  = get_streak_context(user)
    consistency = get_practice_consistency(user_id, db, days=14)
    duration    = get_session_duration_stats(user_id, db)
    abandon     = get_abandon_rate(user_id, db)
    engagement  = get_engagement_level(consistency, abandon, streak_ctx["current_streak"])

    return {
        "current_streak":      streak_ctx["current_streak"],
        "longest_streak":      streak_ctx["longest_streak"],
        "streak_status":       streak_ctx["streak_status"],
        "at_risk":             streak_ctx["at_risk"],
        "consistency_score":   consistency["consistency_score"],
        "active_days":         consistency["active_days"],
        "total_days_window":   consistency["total_days"],
        "practice_pattern":    consistency["pattern"],
        "avg_session_seconds": duration["avg_seconds"],
        "abandon_rate":        abandon,
        "engagement_level":    engagement,
    }


def get_learning_insights(user_id: int, user: User, db: Session) -> dict:
    """
    Full behavioral intelligence report.
    Calls confidence_analyzer sub-domains then passes raw signals to
    learning_insight_engine for interpretation.
    """
    # Gather raw signals
    hesitation   = get_hesitation_profile(user_id, db)
    retry        = get_retry_pattern(user_id, db)
    replay       = get_replay_dependence(user_id, db)
    recovery     = get_recovery_patterns(user_id, db)
    frustration  = get_frustration_level(hesitation, retry, replay)
    confidence   = get_confidence_level(hesitation, retry, frustration, recovery)
    direction    = get_direction_struggle(user_id, db)
    consistency  = get_practice_consistency(user_id, db, days=14)
    abandon      = get_abandon_rate(user_id, db)
    engagement   = get_engagement_level(consistency, abandon, user.user_streak or 0)
    bw           = get_best_and_worst_letters(user_id, db)
    weekly       = get_weekly_accuracy(user_id, None, db)
    trend        = get_accuracy_trend(weekly)

    # Interpret signals → InsightItems
    strengths  = generate_strength_insights(bw["best"], recovery, replay, consistency)
    weaknesses = generate_weakness_insights(bw["worst"], direction, retry, trend)
    behavioral = generate_behavioral_insights(hesitation, frustration, replay,
                                              consistency, engagement)

    return {
        "strengths":        strengths,
        "weaknesses":       weaknesses,
        "behavioral":       behavioral,
        "confidence_level": confidence,
        "frustration_level": frustration,
        "engagement":       engagement,
    }


def get_module_performance(user_id: int, db: Session) -> list[dict]:
    """
    Per-module summary for ModuleGrid.
    Returns one entry per module type the user has practiced.
    """
    from app.data.modules.registry import MODULES

    # Discover which modules this user has sessions for
    practiced = (
        db.query(PracticeSession.module_type)
        .filter(PracticeSession.user_id == user_id)
        .distinct()
        .all()
    )
    module_types = [r.module_type for r in practiced]

    results = []
    for mt in module_types:
        diff_prog = get_difficulty_progression_summary(user_id, mt, db)
        rolling   = get_rolling_average(user_id, mt, db)
        weekly    = get_weekly_accuracy(user_id, mt, db)
        trend     = get_accuracy_trend(weekly)
        total     = get_total_sessions(user_id, db)
        readiness = diff_prog.get("promotion_readiness", 0.0)

        # Retry for frustration (lightweight)
        retry = get_retry_pattern(user_id, db, limit=10)
        frustration = "low"  # default; full calc skipped for performance

        focus = generate_recommended_focus(
            worst_letters       = [],
            frustration_level   = frustration,
            promotion_readiness = readiness,
            trend               = trend,
            avg_accuracy        = rolling,
        )

        # Label from registry
        module_meta = MODULES.get(mt, {})
        label = module_meta.get("label", mt.replace("_", " ").title())

        # Last practiced date
        last_session = (
            db.query(PracticeSession.completed_at)
            .filter(PracticeSession.user_id     == user_id,
                    PracticeSession.module_type  == mt,
                    PracticeSession.is_completed == True)    # noqa: E712
            .order_by(PracticeSession.completed_at.desc())
            .first()
        )
        last_practiced = (
            last_session.completed_at.date().isoformat()
            if last_session and last_session.completed_at
            else None
        )

        results.append({
            "module_type":         mt,
            "label":               label,
            "sessions_completed":  total,
            "avg_accuracy":        rolling,
            "accuracy_trend":      trend,
            "current_difficulty":  diff_prog.get("current_difficulty", "beginner"),
            "promotion_readiness": readiness,
            "recommended_focus":   focus,
            "last_practiced":      last_practiced,
        })

    return results
