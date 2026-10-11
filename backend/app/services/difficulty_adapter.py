"""
app/services/difficulty_adapter.py — Adaptive Difficulty Engine

Queries PracticeSession history to determine the recommended difficulty
for the next session. Progression logic:
  avg_accuracy ≥ 0.85 over last N → promote
  avg_accuracy ≤ 0.50 over last N → demote
  otherwise → maintain

Also stores hesitation analytics from guidance events.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.practice_session import PracticeSession

DIFFICULTY_ORDER = ["beginner", "intermediate", "advanced"]

DEFAULT_DIFFICULTY  = "beginner"
PROMOTE_THRESHOLD   = 0.85
DEMOTE_THRESHOLD    = 0.50
SESSION_WINDOW      = 5     # look at last N completed sessions


def get_recommended_difficulty(
    user_id: int,
    module_type: str,
    db: Session,
    window: int = SESSION_WINDOW,
) -> dict:
    """
    Compute recommended difficulty based on recent session accuracy.

    Returns:
        {
          "difficulty":   "intermediate",
          "current":      "beginner",
          "promoted":     True,
          "avg_accuracy": 0.91,
          "sessions_used": 5
        }
    """
    recent = (
        db.query(PracticeSession.difficulty, PracticeSession.accuracy_score)
        .filter(
            PracticeSession.user_id     == user_id,
            PracticeSession.module_type == module_type,
            PracticeSession.is_completed == True,       # noqa: E712
            PracticeSession.accuracy_score.isnot(None),
        )
        .order_by(PracticeSession.completed_at.desc())
        .limit(window)
        .all()
    )

    if not recent:
        return {
            "difficulty":    DEFAULT_DIFFICULTY,
            "current":       DEFAULT_DIFFICULTY,
            "promoted":      False,
            "demoted":       False,
            "avg_accuracy":  None,
            "sessions_used": 0,
        }

    current_difficulty = recent[0].difficulty
    avg_accuracy = sum(r.accuracy_score for r in recent) / len(recent)
    current_idx  = DIFFICULTY_ORDER.index(current_difficulty) if current_difficulty in DIFFICULTY_ORDER else 0

    if avg_accuracy >= PROMOTE_THRESHOLD and current_idx < len(DIFFICULTY_ORDER) - 1:
        recommended = DIFFICULTY_ORDER[current_idx + 1]
        promoted, demoted = True, False
    elif avg_accuracy <= DEMOTE_THRESHOLD and current_idx > 0:
        recommended = DIFFICULTY_ORDER[current_idx - 1]
        promoted, demoted = False, True
    else:
        recommended = current_difficulty
        promoted, demoted = False, False

    return {
        "difficulty":    recommended,
        "current":       current_difficulty,
        "promoted":      promoted,
        "demoted":       demoted,
        "avg_accuracy":  round(avg_accuracy, 4),
        "sessions_used": len(recent),
    }


def get_item_attempt_count(
    user_id: int,
    module_type: str,
    target_item: str,
    db: Session,
) -> int:
    """Return how many times a user has attempted a specific item."""
    return (
        db.query(func.count(PracticeSession.id))
        .filter(
            PracticeSession.user_id     == user_id,
            PracticeSession.module_type == module_type,
            PracticeSession.target_item == target_item,
        )
        .scalar() or 0
    )
