"""
app/services/analytics/progress_aggregator.py — Learning Progress Analysis

Computes accuracy trends, learning velocity, and item-level performance.
All functions are pure where possible.
All functions accept `snapshot: dict | None` for future caching (Phase 6+).
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Literal

from app.models.practice_session import PracticeSession

WEEK_WINDOW   = 4    # how many weeks to analyse
VELOCITY_MIN  = 1.0  # sessions/week below this → "slow"
VELOCITY_FAST = 3.0  # sessions/week above this AND improving → "fast"


# ──────────────────────────────────────────────────────────────────────────────

def get_weekly_accuracy(
    user_id: int,
    module_type: str | None,
    db: Session,
    weeks: int = WEEK_WINDOW,
    snapshot: dict | None = None,
) -> list[float]:
    """
    Return average accuracy per week for the last `weeks` weeks.
    Most recent week is LAST in the list.
    Returns 0.0 for weeks with no sessions.
    """
    if snapshot:
        return snapshot.get("weekly_accuracy", [0.0] * weeks)

    now   = datetime.now(timezone.utc)
    result = []
    for i in range(weeks - 1, -1, -1):
        week_start = now - timedelta(weeks=i + 1)
        week_end   = now - timedelta(weeks=i)
        q = (
            db.query(func.avg(PracticeSession.accuracy_score))
            .filter(
                PracticeSession.user_id       == user_id,
                PracticeSession.is_completed  == True,          # noqa: E712
                PracticeSession.accuracy_score.isnot(None),
                PracticeSession.completed_at  >= week_start,
                PracticeSession.completed_at  <  week_end,
            )
        )
        if module_type:
            q = q.filter(PracticeSession.module_type == module_type)
        avg = q.scalar()
        result.append(round(float(avg), 4) if avg else 0.0)
    return result


def get_accuracy_trend(
    weekly: list[float],
) -> Literal["improving", "stable", "declining"]:
    """
    Classify the direction of accuracy change.
    Uses only non-zero weeks to avoid distortion from inactive periods.
    """
    non_zero = [w for w in weekly if w > 0]
    if len(non_zero) < 2:
        return "stable"
    delta = non_zero[-1] - non_zero[0]
    if delta > 0.05:
        return "improving"
    if delta < -0.05:
        return "declining"
    return "stable"


def get_learning_velocity(
    user_id: int,
    module_type: str | None,
    db: Session,
    snapshot: dict | None = None,
) -> Literal["fast", "steady", "slow"]:
    """Sessions per week over last 4 weeks, crossed with trend."""
    if snapshot:
        return snapshot.get("velocity", "steady")

    now        = datetime.now(timezone.utc)
    four_weeks = now - timedelta(weeks=4)
    q = (
        db.query(func.count(PracticeSession.id))
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.is_completed == True,       # noqa: E712
            PracticeSession.completed_at >= four_weeks,
        )
    )
    if module_type:
        q = q.filter(PracticeSession.module_type == module_type)
    total = q.scalar() or 0
    per_week = total / 4.0

    if per_week >= VELOCITY_FAST:
        return "fast"
    if per_week < VELOCITY_MIN:
        return "slow"
    return "steady"


def get_rolling_average(
    user_id: int,
    module_type: str | None,
    db: Session,
    window: int = 5,
    snapshot: dict | None = None,
) -> float:
    """Average accuracy over the last `window` completed sessions."""
    if snapshot:
        return snapshot.get("rolling_average", 0.0)

    recent = (
        db.query(PracticeSession.accuracy_score)
        .filter(
            PracticeSession.user_id       == user_id,
            PracticeSession.is_completed  == True,      # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
        )
    )
    if module_type:
        recent = recent.filter(PracticeSession.module_type == module_type)
    scores = [
        r.accuracy_score
        for r in recent.order_by(PracticeSession.completed_at.desc()).limit(window).all()
    ]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 4)


def get_best_and_worst_letters(
    user_id: int,
    db: Session,
    top_n: int = 3,
    snapshot: dict | None = None,
) -> dict:
    """
    Return best and worst letters by average accuracy.
    Only considers alphabet_practice sessions with ≥2 completions.
    """
    if snapshot:
        return snapshot.get("best_worst_letters", {"best": [], "worst": []})

    rows = (
        db.query(
            PracticeSession.target_item,
            func.avg(PracticeSession.accuracy_score).label("avg_acc"),
            func.count(PracticeSession.id).label("cnt"),
        )
        .filter(
            PracticeSession.user_id       == user_id,
            PracticeSession.module_type   == "alphabet_practice",
            PracticeSession.is_completed  == True,          # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
            PracticeSession.target_item.isnot(None),
        )
        .group_by(PracticeSession.target_item)
        .having(func.count(PracticeSession.id) >= 2)
        .all()
    )

    if not rows:
        return {"best": [], "worst": []}

    sorted_rows = sorted(rows, key=lambda r: r.avg_acc, reverse=True)
    best  = [r.target_item for r in sorted_rows[:top_n]]
    worst = [r.target_item for r in sorted_rows[-top_n:] if r.target_item not in best]
    return {"best": best, "worst": worst}


def get_total_sessions(
    user_id: int,
    db: Session,
    snapshot: dict | None = None,
) -> int:
    if snapshot:
        return snapshot.get("total_sessions", 0)
    return (
        db.query(func.count(PracticeSession.id))
        .filter(PracticeSession.user_id == user_id)
        .scalar() or 0
    )


def get_active_days_this_week(
    user_id: int,
    db: Session,
    snapshot: dict | None = None,
) -> int:
    if snapshot:
        return snapshot.get("active_days_this_week", 0)
    now        = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    rows = (
        db.query(func.date(PracticeSession.started_at))
        .filter(
            PracticeSession.user_id    == user_id,
            PracticeSession.started_at >= week_start,
        )
        .distinct()
        .all()
    )
    return len(rows)
