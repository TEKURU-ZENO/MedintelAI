"""
app/services/learning_engine.py — Learning Engine

The single orchestration layer for all session lifecycle events.
All other services (reward, profile, difficulty) are called FROM here.
Route handlers call the Learning Engine — never the sub-services directly.

This prevents:
  - Gamification logic leaking into API routes
  - Duplicated XP / streak calculations
  - Inconsistent state on partial failures
  - Pain when adding ML personalisation in Phase 11

Public API:
  start_session(...)     → PracticeSession
  update_session(...)    → PracticeSession   (in-progress stroke save)
  complete_session(...)  → dict (full reward payload)
  abandon_session(...)   → PracticeSession
  get_module_item(...)   → dict (letter/word data)
  get_modules_for_user(...)  → list[dict]
"""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.practice_session import PracticeSession, SessionStatus
from app.data.modules.registry import get_module, get_modules_for_profile
from app.services.reward_service import (
    calculate_xp,
    award_xp,
    update_streak,
)
from app.services.profile_service import get_learning_profile


# ──────────────────────────────────────────────────────────────────────────────
# Session lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def start_session(
    user: User,
    module_type: str,
    target_item: str | None,
    language: str,
    difficulty: str,
    db: Session,
) -> PracticeSession:
    """
    Create and persist a new PracticeSession.

    Also computes attempt_number: counts how many times this user has
    previously attempted the same (module_type + target_item) pair.
    """
    module_def = get_module(module_type)

    # Count prior attempts for this exact item (retry tracking)
    attempt_number = (
        db.query(PracticeSession)
        .filter(
            PracticeSession.user_id   == user.id,
            PracticeSession.module_type == module_type,
            PracticeSession.target_item == target_item,
        )
        .count()
    ) + 1

    session = PracticeSession(
        user_id        = user.id,
        module_type    = module_type,
        target_item    = target_item,
        module_version = module_def["version"],
        language       = language,
        difficulty     = difficulty,
        attempt_number = attempt_number,
        status         = SessionStatus.STARTED,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def update_session_strokes(
    session: PracticeSession,
    stroke_data: list[dict] | None,
    db: Session,
) -> PracticeSession:
    """
    Save in-progress stroke data without completing the session.
    Called periodically from the frontend (auto-save).
    """
    if stroke_data is not None:
        session.stroke_data   = stroke_data
        session.total_strokes = len(stroke_data)
        session.total_points  = sum(
            len(s.get("points", [])) for s in stroke_data
        )
    session.status = SessionStatus.IN_PROGRESS
    db.commit()
    db.refresh(session)
    return session


def complete_session(
    session: PracticeSession,
    user: User,
    accuracy_score: float,
    detailed_scores: dict | None,
    duration_seconds: int,
    stroke_data: list[dict] | None,
    total_strokes: int | None,
    total_points: int | None,
    db: Session,
) -> dict:
    """
    Mark a session complete, award XP, update streak.

    Returns the full reward payload consumed by SessionCompleteResponse.
    """
    now = datetime.now(timezone.utc)

    # ── Update session record ────────────────────────────────────────────────
    session.status           = SessionStatus.COMPLETED
    session.is_completed     = True
    session.completed_at     = now
    session.duration_seconds = duration_seconds
    session.accuracy_score   = accuracy_score
    session.detailed_scores  = detailed_scores
    session.attempts         = (session.attempts or 0) + 1

    if stroke_data is not None:
        session.stroke_data   = stroke_data
        session.total_strokes = len(stroke_data)
        session.total_points  = sum(len(s.get("points", [])) for s in stroke_data)
    elif total_strokes is not None:
        session.total_strokes = total_strokes
        session.total_points  = total_points

    # ── Calculate raw XP ─────────────────────────────────────────────────────
    raw_xp = calculate_xp(accuracy_score, session.module_type)

    # ── Award XP with daily cap ───────────────────────────────────────────────
    reward = award_xp(user, raw_xp, db)
    session.xp_earned = reward["xp_earned"]

    # ── Update streak ─────────────────────────────────────────────────────────
    new_streak = update_streak(user)

    db.commit()
    db.refresh(session)
    db.refresh(user)

    return {
        "session":            session,
        "xp_earned":          reward["xp_earned"],
        "total_xp":           reward["total_xp"],
        "new_level":          reward["new_level"],
        "level_up":           reward["level_up"],
        "new_streak":         new_streak,
        "daily_xp_remaining": reward["daily_xp_remaining"],
    }


def abandon_session(
    session: PracticeSession,
    stroke_data: list[dict] | None,
    reason: str | None,
    db: Session,
) -> PracticeSession:
    """
    Mark a session abandoned.
    Partial stroke data is saved (valuable for dropout analytics + ML).
    No XP is awarded. Streak is NOT broken by abandonment.
    """
    session.status = SessionStatus.ABANDONED
    if stroke_data is not None:
        session.stroke_data   = stroke_data
        session.total_strokes = len(stroke_data)
        session.total_points  = sum(len(s.get("points", [])) for s in stroke_data)
    db.commit()
    db.refresh(session)
    return session


# ──────────────────────────────────────────────────────────────────────────────
# Module data retrieval
# ──────────────────────────────────────────────────────────────────────────────

def get_module_item(module_type: str, item: str, language: str = "english") -> dict:
    """
    Retrieve the tracing/practice data for a specific item.
    Raises KeyError if module or item not found.
    """
    if module_type == "alphabet_practice" and language == "english":
        from app.data.modules.alphabet_en import get_letter
        return {"module_type": module_type, "item": item, **get_letter(item)}

    if module_type == "word_practice" and language == "english":
        from app.data.modules.words_en import get_word
        data = get_word(item)
        if data is None:
            raise KeyError(f"Word '{item}' not found in English word data.")
        return {"module_type": module_type, "item": item, **data}

    raise KeyError(
        f"No data available for module='{module_type}', language='{language}'."
    )


def get_modules_for_user(user: User) -> list[dict]:
    """
    Return the ordered, filtered module list for a user's profile type.
    Used by the module selection screens in all shells.
    """
    profile = get_learning_profile(user)
    return get_modules_for_profile(profile["profile_type"])


def get_next_item(
    module_type: str,
    difficulty: str,
    user_id: int,
    db: Session,
    language: str = "english",
) -> str:
    """
    Select the next practice item for a session.
    Simple strategy for Phase 2: round-robin through items the user
    has practiced least. Phase 11 will replace with ML recommendations.
    """
    if module_type == "alphabet_practice":
        from app.data.modules.alphabet_en import get_all_letters
        all_items = get_all_letters()
    elif module_type == "word_practice":
        from app.data.modules.words_en import get_words
        all_items = [w["word"] for w in get_words(difficulty)]
    else:
        return ""   # free_draw and others don't need an item

    # Find the item with the fewest completed sessions
    from sqlalchemy import func as sqlfunc
    counts = (
        db.query(
            PracticeSession.target_item,
            sqlfunc.count(PracticeSession.id).label("cnt"),
        )
        .filter(
            PracticeSession.user_id     == user_id,
            PracticeSession.module_type == module_type,
            PracticeSession.is_completed == True,  # noqa: E712
        )
        .group_by(PracticeSession.target_item)
        .all()
    )
    practiced = {row.target_item: row.cnt for row in counts}

    # Sort all items by how often they've been practiced (least first)
    all_items_sorted = sorted(all_items, key=lambda i: practiced.get(i, 0))
    return all_items_sorted[0] if all_items_sorted else ""
