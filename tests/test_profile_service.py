"""
tests/test_profile_service.py — Phase 1 Unit Tests

Tests for the ProfileService pure functions.
These run without a database — they are pure Python logic tests.

Run: pytest tests/test_profile_service.py -v
"""

import pytest
from datetime import date, timedelta
from app.services.profile_service import (
    calculate_age,
    get_profile_type_from_age,
    get_effective_profile_type,
    get_learning_profile,
    get_feedback_message,
)


# ──────────────────────────────────────────────────────────────────────────────
# calculate_age()
# ──────────────────────────────────────────────────────────────────────────────

class TestCalculateAge:
    def test_none_dob_returns_none(self):
        assert calculate_age(None) is None

    def test_age_3(self):
        dob = date(date.today().year - 3, date.today().month, date.today().day)
        assert calculate_age(dob) == 3

    def test_birthday_today_counts_as_full_year(self):
        """On your birthday, you have exactly turned N years old."""
        today = date.today()
        dob = date(today.year - 10, today.month, today.day)
        assert calculate_age(dob) == 10

    def test_birthday_tomorrow_is_one_year_less(self):
        """One day before birthday, you have not yet turned N."""
        tomorrow = date.today() + timedelta(days=1)
        dob = date(date.today().year - 10, tomorrow.month, tomorrow.day)
        assert calculate_age(dob) == 9

    def test_adult_age(self):
        dob = date(date.today().year - 30, 1, 1)
        assert calculate_age(dob) == 30 or calculate_age(dob) == 29  # depending on month


# ──────────────────────────────────────────────────────────────────────────────
# get_profile_type_from_age()
# ──────────────────────────────────────────────────────────────────────────────

class TestProfileTypeFromAge:
    def test_none_age_defaults_to_adult(self):
        assert get_profile_type_from_age(None) == "adult"

    def test_age_0_is_early_learner(self):
        assert get_profile_type_from_age(0) == "early_learner"

    def test_age_3_is_early_learner(self):
        assert get_profile_type_from_age(3) == "early_learner"

    def test_age_5_boundary_is_early_learner(self):
        """Exact boundary: age 5 is still early_learner."""
        assert get_profile_type_from_age(5) == "early_learner"

    def test_age_6_boundary_is_child(self):
        """Exact boundary: age 6 flips to child."""
        assert get_profile_type_from_age(6) == "child"

    def test_age_12_is_child(self):
        assert get_profile_type_from_age(12) == "child"

    def test_age_15_boundary_is_child(self):
        """Exact boundary: age 15 is still child."""
        assert get_profile_type_from_age(15) == "child"

    def test_age_16_boundary_is_adult(self):
        """Exact boundary: age 16 flips to adult."""
        assert get_profile_type_from_age(16) == "adult"

    def test_age_25_is_adult(self):
        assert get_profile_type_from_age(25) == "adult"

    def test_age_60_is_adult(self):
        assert get_profile_type_from_age(60) == "adult"


# ──────────────────────────────────────────────────────────────────────────────
# get_effective_profile_type() — override logic
# ──────────────────────────────────────────────────────────────────────────────

class TestEffectiveProfileType:
    def test_no_dob_no_override_defaults_to_adult(self):
        """Existing users with NULL DOB get adult safely."""
        result = get_effective_profile_type(None, None)
        assert result == "adult"

    def test_age_derived_when_no_override(self):
        dob = date(date.today().year - 8, 1, 1)
        result = get_effective_profile_type(dob, None)
        assert result == "child"

    def test_preferred_mode_overrides_age(self):
        """Adult DOB but preferred_learning_mode=early_learner → early_learner shell."""
        dob = date(date.today().year - 30, 1, 1)
        result = get_effective_profile_type(dob, "early_learner")
        assert result == "early_learner"

    def test_child_dob_but_adult_override(self):
        """A 10-year-old with adult mode override → adult shell."""
        dob = date(date.today().year - 10, 1, 1)
        result = get_effective_profile_type(dob, "adult")
        assert result == "adult"

    def test_invalid_override_falls_back_to_age(self):
        """Invalid preferred_learning_mode value is ignored, falls back to age."""
        dob = date(date.today().year - 8, 1, 1)
        result = get_effective_profile_type(dob, "invalid_value")
        assert result == "child"

    def test_empty_string_override_falls_back_to_age(self):
        dob = date(date.today().year - 4, 1, 1)
        result = get_effective_profile_type(dob, "")
        assert result == "early_learner"


# ──────────────────────────────────────────────────────────────────────────────
# get_learning_profile() — config dict completeness
# ──────────────────────────────────────────────────────────────────────────────

class MockUser:
    """Minimal mock to test get_learning_profile without a DB."""
    def __init__(self, dob, mode=None):
        self.date_of_birth = dob
        self.preferred_learning_mode = mode


class TestGetLearningProfile:
    REQUIRED_KEYS = {
        "profile_type", "theme", "font_size", "animations",
        "sounds", "confetti", "tts_speed", "difficulty_default",
        "feedback_tone", "gamification",
    }

    def test_early_learner_profile_has_all_keys(self):
        user = MockUser(date(date.today().year - 3, 1, 1))
        profile = get_learning_profile(user)
        assert self.REQUIRED_KEYS.issubset(profile.keys())

    def test_early_learner_has_sounds_and_confetti(self):
        user = MockUser(date(date.today().year - 3, 1, 1))
        profile = get_learning_profile(user)
        assert profile["sounds"] is True
        assert profile["confetti"] is True
        assert profile["tts_speed"] == "slow"

    def test_child_profile_no_confetti(self):
        user = MockUser(date(date.today().year - 10, 1, 1))
        profile = get_learning_profile(user)
        assert profile["confetti"] is False
        assert profile["animations"] is True

    def test_adult_profile_minimal(self):
        user = MockUser(date(date.today().year - 30, 1, 1))
        profile = get_learning_profile(user)
        assert profile["animations"] is False
        assert profile["sounds"] is False
        assert profile["gamification"] == "summary"

    def test_override_applied_in_full_profile(self):
        """Adult DOB with early_learner override gets cartoon theme."""
        user = MockUser(date(date.today().year - 30, 1, 1), mode="early_learner")
        profile = get_learning_profile(user)
        assert profile["profile_type"] == "early_learner"
        assert profile["theme"] == "cartoon"


# ──────────────────────────────────────────────────────────────────────────────
# get_feedback_message() — Phase 5 readiness
# ──────────────────────────────────────────────────────────────────────────────

class TestFeedbackMessage:
    def test_early_learner_gets_encouraging_spacing_message(self):
        msg = get_feedback_message("early_learner", "spacing_bad")
        assert "✨" in msg or "great" in msg.lower() or "let's" in msg.lower()

    def test_adult_gets_professional_message(self):
        msg = get_feedback_message("adult", "spacing_bad")
        assert "readability" in msg.lower() or "consistency" in msg.lower()

    def test_unknown_issue_returns_default(self):
        msg = get_feedback_message("child", "unknown_issue_xyz")
        assert isinstance(msg, str)
        assert len(msg) > 0
