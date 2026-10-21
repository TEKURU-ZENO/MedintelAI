"""
app/services/analytics/difficulty_trends.py — Difficulty Progression Analysis

Tracks difficulty level history, promotion readiness, and
counts promotions/demotions from session records.
All functions snapshot-ready.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.practice_session import PracticeSession
from app.services.difficulty_adapter import DIFFICULTY_ORDER, PROMOTE_THRESHOLD


# ──────────────────────────────────────────────────────────────────────────────

def get_current_level_summary(
    user_id: int,
    module_type: str,
    db: Session,
    snapshot: dict | None = None,
) -> dict:
    """Current difficulty, sessions at that level, avg accuracy at that level."""
    if snapshot:
        return snapshot.get("level_summary", _empty_level())

    # Most recent completed session determines current difficulty
    latest = (
        db.query(PracticeSession.difficulty)
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.module_type  == module_type,
            PracticeSession.is_completed == True,       # noqa: E712
        )
        .order_by(PracticeSession.completed_at.desc())
        .first()
    )
    if not latest:
        return _empty_level()

    current = latest.difficulty

    stats = (
        db.query(
            func.count(PracticeSession.id).label("cnt"),
            func.avg(PracticeSession.accuracy_score).label("avg"),
        )
        .filter(
            PracticeSession.user_id       == user_id,
            PracticeSession.module_type   == module_type,
            PracticeSession.difficulty    == current,
            PracticeSession.is_completed  == True,      # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
        )
        .first()
    )
    return {
        "current_difficulty":      current,
        "sessions_at_level":       stats.cnt if stats else 0,
        "avg_accuracy_at_level":   round(float(stats.avg), 4) if stats and stats.avg else 0.0,
    }


def _empty_level() -> dict:
    return {"current_difficulty": "beginner",
            "sessions_at_level": 0, "avg_accuracy_at_level": 0.0}


def get_promotion_readiness(
    user_id: int,
    module_type: str,
    db: Session,
    snapshot: dict | None = None,
) -> float:
    """
    0.0–1.0: how close the user is to promotion threshold.
    = (avg_accuracy_last_5 / PROMOTE_THRESHOLD), capped at 1.0.
    """
    if snapshot:
        return snapshot.get("promotion_readiness", 0.0)

    recent = (
        db.query(PracticeSession.accuracy_score)
        .filter(
            PracticeSession.user_id       == user_id,
            PracticeSession.module_type   == module_type,
            PracticeSession.is_completed  == True,      # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(5)
        .all()
    )
    if not recent:
        return 0.0
    avg = sum(r.accuracy_score for r in recent) / len(recent)
    return round(min(1.0, avg / PROMOTE_THRESHOLD), 4)


def get_difficulty_history(
    user_id: int,
    module_type: str,
    db: Session,
    limit: int = 20,
    snapshot: dict | None = None,
) -> list[dict]:
    """Last N sessions showing difficulty + accuracy for trend chart."""
    if snapshot:
        return snapshot.get("difficulty_history", [])

    rows = (
        db.query(
            PracticeSession.completed_at,
            PracticeSession.difficulty,
            PracticeSession.accuracy_score,
        )
        .filter(
            PracticeSession.user_id      == user_id,
            PracticeSession.module_type  == module_type,
            PracticeSession.is_completed == True,       # noqa: E712
        )
        .order_by(PracticeSession.completed_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "date":       r.completed_at.date().isoformat() if r.completed_at else None,
            "difficulty": r.difficulty,
            "accuracy":   round(float(r.accuracy_score), 4) if r.accuracy_score else None,
        }
        for r in rows
    ]


def count_promotions_demotions(history: list[dict]) -> dict:
    """
    Count difficulty level changes from a history list.
    Derived purely from data — no extra DB call.
    """
    promotions = demotions = 0
    for i in range(1, len(history)):
        prev = history[i - 1].get("difficulty", "beginner")
        curr = history[i].get("difficulty", "beginner")
        if prev in DIFFICULTY_ORDER and curr in DIFFICULTY_ORDER:
            pi, ci = DIFFICULTY_ORDER.index(prev), DIFFICULTY_ORDER.index(curr)
            if ci > pi:
                promotions += 1
            elif ci < pi:
                demotions += 1
    return {"promotions_count": promotions, "demotions_count": demotions}


def get_difficulty_progression_summary(
    user_id: int,
    module_type: str,
    db: Session,
    snapshot: dict | None = None,
) -> dict:
    """Full difficulty summary for analytics_service."""
    if snapshot:
        return snapshot.get("difficulty_progression", {})

    level    = get_current_level_summary(user_id, module_type, db)
    readiness = get_promotion_readiness(user_id, module_type, db)
    history   = get_difficulty_history(user_id, module_type, db)
    changes   = count_promotions_demotions(history)

    return {
        "current_difficulty":  level["current_difficulty"],
        "sessions_at_level":   level["sessions_at_level"],
        "avg_accuracy_at_level": level["avg_accuracy_at_level"],
        "promotion_readiness": readiness,
        **changes,
        "history":             history,
    }
