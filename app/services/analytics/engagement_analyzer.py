"""
app/services/analytics/engagement_analyzer.py — Practice Engagement Analysis

Tracks how consistently and sustainably a user practices.
All functions snapshot-ready.
"""

from datetime import datetime, timedelta, timezone, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Literal

from app.models.practice_session import PracticeSession, SessionStatus
from app.models.user import User


# ──────────────────────────────────────────────────────────────────────────────

def get_streak_context(
    user: User,
    snapshot: dict | None = None,
) -> dict:
    """
    Returns streak metadata including at-risk detection.
    at_risk = last active date was yesterday (will break tonight).
    """
    if snapshot:
        return snapshot.get("streak_context", _empty_streak())

    today      = date.today()
    last_active = user.last_active_date
    streak      = user.user_streak or 0
    longest     = getattr(user, "longest_streak", streak)

    at_risk = (
        last_active is not None and
        (today - last_active).days == 1
    )
    if last_active is None or (today - last_active).days > 1:
        status = "broken" if streak == 0 else "broken"
    elif (today - last_active).days == 0:
        status = "active"
    else:
        status = "at_risk"

    # Recalculate: if last_active is today → active, yesterday → at_risk
    if last_active is None:
        status = "broken"
    elif (today - last_active).days == 0:
        status = "active"
    elif (today - last_active).days == 1:
        status = "at_risk"
    else:
        status = "broken"

    return {
        "current_streak": streak,
        "longest_streak": longest,
        "streak_status":  status,
        "at_risk":        at_risk,
    }


def _empty_streak() -> dict:
    return {"current_streak": 0, "longest_streak": 0,
            "streak_status": "broken", "at_risk": False}


def get_session_duration_stats(
    user_id: int,
    db: Session,
    window: int = 10,
    snapshot: dict | None = None,
) -> dict:
    """Average, min, max duration in seconds over last N sessions."""
    if snapshot:
        return snapshot.get("duration_stats", {"avg_seconds": 0.0, "min": 0, "max": 0})

    rows = (
        db.query(PracticeSession.duration_seconds)
        .filter(
            PracticeSession.user_id          == user_id,
            PracticeSession.is_completed     == True,       # noqa: E712
            PracticeSession.duration_seconds.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(window)
        .all()
    )
    durations = [r.duration_seconds for r in rows]
    if not durations:
        return {"avg_seconds": 0.0, "min": 0, "max": 0}
    return {
        "avg_seconds": round(sum(durations) / len(durations), 1),
        "min":         min(durations),
        "max":         max(durations),
    }


def get_abandon_rate(
    user_id: int,
    db: Session,
    days: int = 30,
    snapshot: dict | None = None,
) -> float:
    """Abandoned sessions / total sessions in last N days."""
    if snapshot:
        return snapshot.get("abandon_rate", 0.0)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    total = (
        db.query(func.count(PracticeSession.id))
        .filter(PracticeSession.user_id == user_id,
                PracticeSession.started_at >= since)
        .scalar() or 0
    )
    if total == 0:
        return 0.0
    abandoned = (
        db.query(func.count(PracticeSession.id))
        .filter(
            PracticeSession.user_id    == user_id,
            PracticeSession.started_at >= since,
            PracticeSession.status     == SessionStatus.ABANDONED,
        )
        .scalar() or 0
    )
    return round(abandoned / total, 4)


def get_practice_consistency(
    user_id: int,
    db: Session,
    days: int = 14,
    snapshot: dict | None = None,
) -> dict:
    """
    Measures how many days in the last `days` the user practiced.
    Also detects practice pattern (weekday_only / weekend_heavy / consistent / irregular).
    """
    if snapshot:
        return snapshot.get("consistency", _empty_consistency(days))

    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows  = (
        db.query(func.date(PracticeSession.started_at).label("day"),
                 func.extract("dow", PracticeSession.started_at).label("dow"))
        .filter(PracticeSession.user_id    == user_id,
                PracticeSession.started_at >= since)
        .distinct()
        .all()
    )

    active_days = len({r.day for r in rows})
    score = round(active_days / days, 4)

    # Day-of-week distribution (0=Sun, 6=Sat in PostgreSQL)
    weekend_days = sum(1 for r in rows if r.dow in (0, 6))
    weekday_days = active_days - weekend_days

    if active_days == 0:
        pattern = "irregular"
    elif weekend_days == 0 and weekday_days > 0:
        pattern = "weekday_only"
    elif weekday_days == 0 and weekend_days > 0:
        pattern = "weekend_heavy"
    elif score >= 0.70:
        pattern = "consistent"
    else:
        pattern = "irregular"

    return {
        "active_days":        active_days,
        "total_days":         days,
        "consistency_score":  score,
        "pattern":            pattern,
    }


def _empty_consistency(days: int) -> dict:
    return {"active_days": 0, "total_days": days,
            "consistency_score": 0.0, "pattern": "irregular"}


def get_engagement_level(
    consistency: dict,
    abandon_rate: float,
    streak: int,
) -> Literal["high", "medium", "low"]:
    """
    Composite engagement classification.
      high:   consistency >= 0.70 AND abandon_rate < 0.15 AND streak >= 3
      low:    consistency < 0.35 OR abandon_rate > 0.40
      medium: otherwise
    """
    score = consistency.get("consistency_score", 0.0)
    if score >= 0.70 and abandon_rate < 0.15 and streak >= 3:
        return "high"
    if score < 0.35 or abandon_rate > 0.40:
        return "low"
    return "medium"
