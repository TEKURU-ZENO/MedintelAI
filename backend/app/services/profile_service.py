"""
profile_service.py — V2 Adaptive Profile Engine

This service is the single source of truth for all profile-type-driven
adaptive behavior. All other services (feedback, gamification, difficulty)
should call get_learning_profile() to get the full adaptive config rather
than duplicating profile-type logic.
"""

from datetime import date
from typing import Literal

ProfileType = Literal["early_learner", "child", "adult"]

# ──────────────────────────────────────────────────────────────────────────────
# Profile derivation — pure functions, fully testable without DB
# ──────────────────────────────────────────────────────────────────────────────

def calculate_age(date_of_birth: date | None) -> int | None:
    """Return current age in full years from a date_of_birth."""
    if date_of_birth is None:
        return None
    today = date.today()
    return (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )


def get_profile_type_from_age(age: int | None) -> ProfileType:
    """
    Derive profile type purely from numeric age.
    Used as a fallback when preferred_learning_mode is not set.
    """
    if age is None:
        return "adult"
    if age <= 5:
        return "early_learner"
    if age <= 15:
        return "child"
    return "adult"


def get_effective_profile_type(
    date_of_birth: date | None,
    preferred_learning_mode: str | None,
) -> ProfileType:
    """
    Compute the effective profile type used for adaptive rendering.

    Decision order:
    1. preferred_learning_mode (user/teacher override) — highest priority
    2. Age derived from date_of_birth — fallback
    3. "adult" — safe default when no data available
    """
    VALID_TYPES = {"early_learner", "child", "adult"}
    if preferred_learning_mode and preferred_learning_mode in VALID_TYPES:
        return preferred_learning_mode  # type: ignore[return-value]
    age = calculate_age(date_of_birth)
    return get_profile_type_from_age(age)


# ──────────────────────────────────────────────────────────────────────────────
# Full adaptive learning profile — the main API for all other services
# ──────────────────────────────────────────────────────────────────────────────

def get_learning_profile(user) -> dict:
    """
    Return a complete adaptive configuration dict for a user.
    This is the single object that drives:
      - Frontend shell selection
      - Feedback tone (Phases 4 & 5)
      - Gamification intensity (Phase 6)
      - TTS speed (Phase 7)
      - Difficulty defaults (Phase 11)

    Args:
        user: SQLAlchemy User ORM instance (or any object with .date_of_birth
              and .preferred_learning_mode attributes)
    """
    profile_type = get_effective_profile_type(
        date_of_birth=user.date_of_birth,
        preferred_learning_mode=user.preferred_learning_mode,
    )
    return _build_profile_config(profile_type)


def _build_profile_config(profile_type: ProfileType) -> dict:
    """Build the full adaptive config dict for a given profile type."""
    base = {
        "profile_type": profile_type,
    }

    if profile_type == "early_learner":
        return {
            **base,
            "theme": "cartoon",
            "font_size": "xl",
            "animations": True,
            "sounds": True,
            "confetti": True,
            "tts_speed": "slow",
            "difficulty_default": "beginner",
            "feedback_tone": "very_encouraging",
            "gamification": "full",          # stars, confetti, music
        }

    if profile_type == "child":
        return {
            **base,
            "theme": "motivational",
            "font_size": "lg",
            "animations": True,
            "sounds": False,
            "confetti": False,
            "tts_speed": "normal",
            "difficulty_default": "beginner",
            "feedback_tone": "encouraging",
            "gamification": "standard",       # XP bars, streaks, badges
        }

    # adult (default)
    return {
        **base,
        "theme": "minimal",
        "font_size": "base",
        "animations": False,
        "sounds": False,
        "confetti": False,
        "tts_speed": "normal",
        "difficulty_default": "intermediate",
        "feedback_tone": "professional",
        "gamification": "summary",            # achievement summaries only
    }


# ──────────────────────────────────────────────────────────────────────────────
# Feedback tone helper (used by Phase 5 adaptive feedback engine)
# ──────────────────────────────────────────────────────────────────────────────

FEEDBACK_TEMPLATES = {
    "very_encouraging": {
        "spacing_bad":   "Great try! Let's make the letters a little further apart ✨",
        "slant_bad":     "Wow, so close! Let's try to keep the letters more upright 🌟",
        "baseline_bad":  "Amazing effort! Let's try to keep the letters on the line 🎉",
        "perfect":       "PERFECT! You're a handwriting superstar! 🏆🎊",
    },
    "encouraging": {
        "spacing_bad":   "Nice work! Try leaving a little more space between letters 👍",
        "slant_bad":     "Good try! Try to keep your letters more upright 📐",
        "baseline_bad":  "Getting there! Keep your letters sitting on the baseline 📏",
        "perfect":       "Excellent! Perfect handwriting! 🌟",
    },
    "professional": {
        "spacing_bad":   "Letter spacing consistency can be improved for better readability.",
        "slant_bad":     "Slant consistency should be maintained throughout.",
        "baseline_bad":  "Baseline alignment requires attention.",
        "perfect":       "Excellent formation. All metrics within acceptable range.",
    },
}


def get_feedback_message(profile_type: ProfileType, issue_key: str) -> str:
    """
    Get an adaptive feedback message for a given profile type and issue.

    Args:
        profile_type: "early_learner" | "child" | "adult"
        issue_key: "spacing_bad" | "slant_bad" | "baseline_bad" | "perfect"
    """
    tone_map = {
        "early_learner": "very_encouraging",
        "child": "encouraging",
        "adult": "professional",
    }
    tone = tone_map.get(profile_type, "professional")
    templates = FEEDBACK_TEMPLATES.get(tone, FEEDBACK_TEMPLATES["professional"])
    return templates.get(issue_key, "Keep practicing!")
