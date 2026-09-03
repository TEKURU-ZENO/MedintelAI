"""
app/services/reward_service.py — XP & Reward Engine

Centralised XP calculation, daily cap enforcement, level-up detection.
All reward logic flows through here — never scattered in route handlers.

Constants:
  XP_PER_LEVEL   = 100   — XP needed to advance one level
  MAX_DAILY_XP   = 250   — prevents gamification abuse / infinite grinding
"""

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User
from app.models.practice_session import PracticeSession
from app.data.modules.registry import get_module

XP_PER_LEVEL  = 100
MAX_DAILY_XP  = 250


# ──────────────────────────────────────────────────────────────────────────────
# XP calculation
# ──────────────────────────────────────────────────────────────────────────────

def calculate_xp(accuracy: float, module_type: str) -> int:
    """
    Calculate raw XP earned for a session.

    Tiers:
      ≥ 0.90 → 2× base XP  (perfect / near-perfect)
      ≥ 0.70 → 1× base XP  (good)
      ≥ 0.50 → ½ base XP   (okay)
      < 0.50 → 1 XP         (always reward effort)
    """
    try:
        base = get_module(module_type)["xp_per_session"]
    except KeyError:
        base = 5  # safe default for unknown modules

    if accuracy >= 0.90:
        return base * 2
    if accuracy >= 0.70:
        return base
    if accuracy >= 0.50:
        return max(1, base // 2)
    return 1


def calculate_level(total_xp: int) -> int:
    """Derive level from total XP. Level 1 starts at 0 XP."""
    return 1 + (total_xp // XP_PER_LEVEL)


def xp_to_next_level(total_xp: int) -> int:
    """XP remaining until the next level."""
    return XP_PER_LEVEL - (total_xp % XP_PER_LEVEL)


# ──────────────────────────────────────────────────────────────────────────────
# Daily XP cap
# ──────────────────────────────────────────────────────────────────────────────

def get_daily_xp_earned(user_id: int, db: Session) -> int:
    """
    Return total XP the user has earned in completed sessions today.
    Used to enforce the daily cap before awarding new XP.
    """
    today_start = date.today()
    result = (
        db.query(func.coalesce(func.sum(PracticeSession.xp_earned), 0))
        .filter(
            PracticeSession.user_id == user_id,
            PracticeSession.is_completed == True,  # noqa: E712
            func.date(PracticeSession.completed_at) == today_start,
        )
        .scalar()
    )
    return int(result)


def apply_daily_cap(raw_xp: int, user_id: int, db: Session) -> tuple[int, int]:
    """
    Apply the daily XP cap and return (capped_xp, daily_remaining_after).

    Returns:
        (actual_xp_to_award, remaining_daily_xp_after_award)
    """
    already_earned  = get_daily_xp_earned(user_id, db)
    remaining       = max(0, MAX_DAILY_XP - already_earned)
    actual_xp       = min(raw_xp, remaining)
    remaining_after = max(0, remaining - actual_xp)
    return actual_xp, remaining_after


# ──────────────────────────────────────────────────────────────────────────────
# Award XP + level-up
# ──────────────────────────────────────────────────────────────────────────────

def award_xp(
    user: User,
    raw_xp: int,
    db: Session,
) -> dict:
    """
    Award XP to a user with daily cap enforcement.
    Updates User.xp_points, User.level in-place.

    Returns a dict with reward metadata for the API response:
      {
        "xp_earned":          actual XP awarded (after cap),
        "total_xp":           user's new total,
        "new_level":          user's level after award,
        "level_up":           True if level boundary was crossed,
        "daily_xp_remaining": remaining cap for today,
      }
    """
    level_before = calculate_level(user.xp_points)

    actual_xp, daily_remaining = apply_daily_cap(raw_xp, user.id, db)

    user.xp_points += actual_xp
    new_level = calculate_level(user.xp_points)
    user.level = new_level

    db.flush()   # write to DB without committing (caller commits)

    return {
        "xp_earned":          actual_xp,
        "total_xp":           user.xp_points,
        "new_level":          new_level,
        "level_up":           new_level > level_before,
        "daily_xp_remaining": daily_remaining,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Streak management
# ──────────────────────────────────────────────────────────────────────────────

def update_streak(user: User) -> int:
    """
    Update user's streak based on today's date vs last_active_date.

    Rules:
      - Same day   → streak unchanged (already counted today)
      - Yesterday  → streak + 1
      - Any gap    → streak resets to 1
    Updates longest_streak if new streak exceeds it.
    Returns the new streak count.
    """
    today = date.today()

    if user.last_active_date == today:
        return user.user_streak                    # already practiced today

    if user.last_active_date is not None:
        delta = (today - user.last_active_date).days
        user.user_streak = user.user_streak + 1 if delta == 1 else 1
    else:
        user.user_streak = 1

    # Track all-time best streak
    if user.user_streak > (user.longest_streak or 0):
        user.longest_streak = user.user_streak

    user.last_active_date = today
    return user.user_streak
