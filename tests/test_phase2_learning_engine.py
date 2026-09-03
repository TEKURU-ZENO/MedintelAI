"""
tests/test_phase2_learning_engine.py — Phase 2 Unit Tests

Tests reward_service and module data — all pure-function, no DB required.
Learning engine DB-dependent tests use mocks.

Run: pytest tests/test_phase2_learning_engine.py -v
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import date


# ──────────────────────────────────────────────────────────────────────────────
# Reward Service: XP formula
# ──────────────────────────────────────────────────────────────────────────────

class TestCalculateXP:
    from app.services.reward_service import calculate_xp

    def test_perfect_score_doubles_xp(self):
        from app.services.reward_service import calculate_xp
        # alphabet_practice base = 10, perfect = 2x = 20
        assert calculate_xp(1.0, "alphabet_practice") == 20

    def test_near_perfect_doubles_xp(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.90, "alphabet_practice") == 20

    def test_good_score_gives_base_xp(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.70, "alphabet_practice") == 10

    def test_good_score_upper_bound(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.89, "alphabet_practice") == 10

    def test_okay_score_gives_half_xp(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.50, "alphabet_practice") == 5

    def test_okay_score_upper_bound(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.69, "alphabet_practice") == 5

    def test_poor_score_always_gives_1_xp(self):
        from app.services.reward_service import calculate_xp
        assert calculate_xp(0.10, "alphabet_practice") == 1
        assert calculate_xp(0.0,  "alphabet_practice") == 1
        assert calculate_xp(0.49, "alphabet_practice") == 1

    def test_word_practice_higher_base(self):
        from app.services.reward_service import calculate_xp
        # word_practice base = 15, perfect = 30
        assert calculate_xp(1.0, "word_practice") == 30

    def test_free_draw_base(self):
        from app.services.reward_service import calculate_xp
        # free_draw base = 5, perfect = 10
        assert calculate_xp(1.0, "free_draw") == 10

    def test_unknown_module_safe_default(self):
        from app.services.reward_service import calculate_xp
        # Unknown module: base=5, perfect=10
        assert calculate_xp(1.0, "nonexistent_module") == 10


# ──────────────────────────────────────────────────────────────────────────────
# Reward Service: level calculation
# ──────────────────────────────────────────────────────────────────────────────

class TestLevelCalculation:
    def test_zero_xp_is_level_1(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(0) == 1

    def test_99_xp_still_level_1(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(99) == 1

    def test_100_xp_is_level_2(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(100) == 2

    def test_199_xp_is_level_2(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(199) == 2

    def test_200_xp_is_level_3(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(200) == 3

    def test_500_xp_is_level_6(self):
        from app.services.reward_service import calculate_level
        assert calculate_level(500) == 6

    def test_xp_to_next_level_from_zero(self):
        from app.services.reward_service import xp_to_next_level
        assert xp_to_next_level(0) == 100

    def test_xp_to_next_level_midway(self):
        from app.services.reward_service import xp_to_next_level
        assert xp_to_next_level(50) == 50

    def test_xp_to_next_level_at_boundary(self):
        from app.services.reward_service import xp_to_next_level
        assert xp_to_next_level(100) == 100


# ──────────────────────────────────────────────────────────────────────────────
# Reward Service: daily XP cap
# ──────────────────────────────────────────────────────────────────────────────

class TestDailyXPCap:
    def test_cap_not_exceeded(self):
        from app.services.reward_service import apply_daily_cap
        mock_db = MagicMock()
        with patch(
            "app.services.reward_service.get_daily_xp_earned",
            return_value=0
        ):
            actual, remaining = apply_daily_cap(20, 1, mock_db)
        assert actual == 20
        assert remaining == 230  # 250 - 20

    def test_cap_partially_exceeded(self):
        from app.services.reward_service import apply_daily_cap
        mock_db = MagicMock()
        with patch(
            "app.services.reward_service.get_daily_xp_earned",
            return_value=240
        ):
            # Only 10 XP remaining, trying to award 20
            actual, remaining = apply_daily_cap(20, 1, mock_db)
        assert actual == 10
        assert remaining == 0

    def test_cap_fully_exhausted(self):
        from app.services.reward_service import apply_daily_cap
        mock_db = MagicMock()
        with patch(
            "app.services.reward_service.get_daily_xp_earned",
            return_value=250
        ):
            actual, remaining = apply_daily_cap(20, 1, mock_db)
        assert actual == 0
        assert remaining == 0


# ──────────────────────────────────────────────────────────────────────────────
# Reward Service: streak logic
# ──────────────────────────────────────────────────────────────────────────────

class TestStreakLogic:
    def _make_user(self, streak: int, last_active: date | None) -> MagicMock:
        user = MagicMock()
        user.user_streak     = streak
        user.longest_streak  = 0         # Phase 3.5: required by update_streak
        user.last_active_date = last_active
        return user


    def test_first_ever_session_starts_streak_at_1(self):
        from app.services.reward_service import update_streak
        user = self._make_user(0, None)
        result = update_streak(user)
        assert result == 1

    def test_consecutive_day_increments_streak(self):
        from app.services.reward_service import update_streak
        yesterday = date.fromordinal(date.today().toordinal() - 1)
        user = self._make_user(5, yesterday)
        result = update_streak(user)
        assert result == 6

    def test_same_day_does_not_change_streak(self):
        from app.services.reward_service import update_streak
        user = self._make_user(5, date.today())
        result = update_streak(user)
        assert result == 5  # unchanged

    def test_missed_day_resets_streak(self):
        from app.services.reward_service import update_streak
        two_days_ago = date.fromordinal(date.today().toordinal() - 2)
        user = self._make_user(10, two_days_ago)
        result = update_streak(user)
        assert result == 1   # reset


# ──────────────────────────────────────────────────────────────────────────────
# Module Registry
# ──────────────────────────────────────────────────────────────────────────────

class TestModuleRegistry:
    def test_all_seven_modules_defined(self):
        from app.data.modules.registry import MODULES
        expected = {
            "alphabet_practice", "word_practice", "sentence_practice",
            "shape_practice", "pronunciation_practice", "spell_correction",
            "free_draw",
        }
        assert expected.issubset(MODULES.keys())

    def test_early_learner_cannot_access_spell_correction(self):
        from app.data.modules.registry import get_modules_for_profile
        mods = get_modules_for_profile("early_learner")
        types = {m["module_type"] for m in mods}
        assert "spell_correction" not in types

    def test_adult_can_access_all_non_shape_modules(self):
        from app.data.modules.registry import get_modules_for_profile
        mods = get_modules_for_profile("adult")
        types = {m["module_type"] for m in mods}
        assert "alphabet_practice" in types
        assert "word_practice"     in types
        assert "spell_correction"  in types

    def test_get_module_raises_for_unknown(self):
        from app.data.modules.registry import get_module
        with pytest.raises(KeyError):
            get_module("nonexistent_module_xyz")

    def test_each_module_has_required_keys(self):
        from app.data.modules.registry import MODULES
        required = {"label", "icon", "difficulty_levels",
                    "profile_types", "xp_per_session", "version"}
        for name, mod in MODULES.items():
            assert required.issubset(mod.keys()), f"Module '{name}' missing keys"


# ──────────────────────────────────────────────────────────────────────────────
# Alphabet data
# ──────────────────────────────────────────────────────────────────────────────

class TestAlphabetData:
    def test_all_26_letters_defined(self):
        from app.data.modules.alphabet_en import get_all_letters
        assert len(get_all_letters()) == 26

    def test_every_letter_has_required_keys(self):
        from app.data.modules.alphabet_en import ALPHABET
        required = {"svg_path", "strokes", "difficulty_modifier",
                    "stroke_order_required", "start_point"}
        for letter, data in ALPHABET.items():
            assert required.issubset(data.keys()), f"Letter '{letter}' missing keys"

    def test_every_stroke_has_required_keys(self):
        from app.data.modules.alphabet_en import ALPHABET
        for letter, data in ALPHABET.items():
            for stroke in data["strokes"]:
                assert "id" in stroke, f"{letter}: stroke missing 'id'"
                assert "points" in stroke, f"{letter}: stroke missing 'points'"
                assert "direction" in stroke, f"{letter}: stroke missing 'direction'"
                assert "hint" in stroke, f"{letter}: stroke missing 'hint'"

    def test_get_letter_returns_version(self):
        from app.data.modules.alphabet_en import get_letter
        data = get_letter("A")
        assert data["version"] == "v1"
        assert data["letter"] == "A"

    def test_get_letter_raises_for_invalid(self):
        from app.data.modules.alphabet_en import get_letter
        with pytest.raises(KeyError):
            get_letter("!")

    def test_difficulty_modifier_is_float(self):
        from app.data.modules.alphabet_en import ALPHABET
        for letter, data in ALPHABET.items():
            assert isinstance(data["difficulty_modifier"], float), \
                f"{letter}: difficulty_modifier must be float"

    def test_easy_letters_filter(self):
        from app.data.modules.alphabet_en import get_letters_by_difficulty
        easy = get_letters_by_difficulty(0.9)
        # L (0.7), I (0.7), T (0.8), X (0.8), F (0.9), C (0.9) should be included
        assert "L" in easy
        assert "I" in easy
        # S (1.4) should NOT be in easy
        assert "S" not in easy


# ──────────────────────────────────────────────────────────────────────────────
# Word data
# ──────────────────────────────────────────────────────────────────────────────

class TestWordData:
    def test_three_difficulty_tiers_exist(self):
        from app.data.modules.words_en import WORDS
        assert set(WORDS.keys()) == {"beginner", "intermediate", "advanced"}

    def test_beginner_has_at_least_10_words(self):
        from app.data.modules.words_en import get_words
        assert len(get_words("beginner")) >= 10

    def test_every_word_has_required_keys(self):
        from app.data.modules.words_en import WORDS
        required = {"word", "phonetic", "syllables", "category"}
        for tier, words in WORDS.items():
            for entry in words:
                assert required.issubset(entry.keys()), \
                    f"Tier '{tier}', word '{entry.get('word')}' missing keys"

    def test_get_words_returns_version(self):
        from app.data.modules.words_en import get_words
        words = get_words("beginner")
        assert all(w["version"] == "v1" for w in words)

    def test_get_word_finds_across_tiers(self):
        from app.data.modules.words_en import get_word
        result = get_word("Wednesday")
        assert result is not None
        assert result["syllables"] == 3

    def test_get_word_returns_none_for_unknown(self):
        from app.data.modules.words_en import get_word
        assert get_word("xyznotaword") is None

    def test_invalid_difficulty_raises(self):
        from app.data.modules.words_en import get_words
        with pytest.raises(KeyError):
            get_words("expert")

    def test_random_words_returns_correct_count(self):
        from app.data.modules.words_en import get_random_words
        sample = get_random_words("beginner", 5)
        assert len(sample) == 5
        # All items are unique words
        words = [w["word"] for w in sample]
        assert len(words) == len(set(words))
