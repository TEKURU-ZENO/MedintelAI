"""
tests/test_analytics_service.py — Phase 3.5 Analytics Foundation Tests

All tests are pure-function where possible.
DB-dependent functions use MagicMock for the db session.
Run: pytest tests/test_analytics_service.py -v
"""

import pytest
from unittest.mock import MagicMock, patch


# ──────────────────────────────────────────────────────────────────────────────
# Progress Aggregator
# ──────────────────────────────────────────────────────────────────────────────

class TestProgressAggregator:

    def test_accuracy_trend_improving(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        assert get_accuracy_trend([0.60, 0.68, 0.75, 0.82]) == "improving"

    def test_accuracy_trend_declining(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        assert get_accuracy_trend([0.85, 0.78, 0.71, 0.64]) == "declining"

    def test_accuracy_trend_stable(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        assert get_accuracy_trend([0.72, 0.74, 0.73, 0.75]) == "stable"

    def test_accuracy_trend_single_week(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        # Only one non-zero week → stable (not enough data)
        assert get_accuracy_trend([0.0, 0.0, 0.0, 0.80]) == "stable"

    def test_accuracy_trend_all_zero(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        assert get_accuracy_trend([0.0, 0.0, 0.0, 0.0]) == "stable"

    def test_accuracy_trend_ignores_zero_weeks(self):
        from app.services.analytics.progress_aggregator import get_accuracy_trend
        # Zero weeks are ignored; 0.60 → 0.85 is improving
        assert get_accuracy_trend([0.0, 0.60, 0.0, 0.85]) == "improving"

    def test_snapshot_returns_cached_weekly(self):
        from app.services.analytics.progress_aggregator import get_weekly_accuracy
        snap = {"weekly_accuracy": [0.5, 0.6, 0.7, 0.8]}
        result = get_weekly_accuracy(1, None, MagicMock(), snapshot=snap)
        assert result == [0.5, 0.6, 0.7, 0.8]

    def test_snapshot_returns_cached_rolling(self):
        from app.services.analytics.progress_aggregator import get_rolling_average
        snap = {"rolling_average": 0.77}
        assert get_rolling_average(1, None, MagicMock(), snapshot=snap) == 0.77

    def test_best_worst_returns_dict_keys(self):
        from app.services.analytics.progress_aggregator import get_best_and_worst_letters
        snap = {"best_worst_letters": {"best": ["L", "I"], "worst": ["S"]}}
        result = get_best_and_worst_letters(1, MagicMock(), snapshot=snap)
        assert "best" in result
        assert "worst" in result


# ──────────────────────────────────────────────────────────────────────────────
# Engagement Analyzer
# ──────────────────────────────────────────────────────────────────────────────

class TestEngagementAnalyzer:

    def _make_user(self, streak=5, last_active=None):
        from datetime import date
        user = MagicMock()
        user.user_streak     = streak
        user.longest_streak  = streak
        user.last_active_date = last_active or date.today()
        return user

    def test_streak_active_when_today(self):
        from app.services.analytics.engagement_analyzer import get_streak_context
        from datetime import date
        user = self._make_user(last_active=date.today())
        ctx = get_streak_context(user)
        assert ctx["streak_status"] == "active"

    def test_streak_at_risk_when_yesterday(self):
        from app.services.analytics.engagement_analyzer import get_streak_context
        from datetime import date, timedelta
        user = self._make_user(last_active=date.today() - timedelta(days=1))
        ctx = get_streak_context(user)
        assert ctx["streak_status"] == "at_risk"
        assert ctx["at_risk"] is True

    def test_streak_broken_when_old(self):
        from app.services.analytics.engagement_analyzer import get_streak_context
        from datetime import date, timedelta
        user = self._make_user(streak=3, last_active=date.today() - timedelta(days=5))
        ctx = get_streak_context(user)
        assert ctx["streak_status"] == "broken"

    def test_engagement_high(self):
        from app.services.analytics.engagement_analyzer import get_engagement_level
        consistency = {"consistency_score": 0.80}
        assert get_engagement_level(consistency, 0.05, streak=7) == "high"

    def test_engagement_low_abandon(self):
        from app.services.analytics.engagement_analyzer import get_engagement_level
        consistency = {"consistency_score": 0.60}
        assert get_engagement_level(consistency, 0.50, streak=5) == "low"

    def test_engagement_low_consistency(self):
        from app.services.analytics.engagement_analyzer import get_engagement_level
        consistency = {"consistency_score": 0.20}
        assert get_engagement_level(consistency, 0.10, streak=2) == "low"

    def test_engagement_medium(self):
        from app.services.analytics.engagement_analyzer import get_engagement_level
        consistency = {"consistency_score": 0.55}
        assert get_engagement_level(consistency, 0.20, streak=2) == "medium"

    def test_consistency_snapshot(self):
        from app.services.analytics.engagement_analyzer import get_practice_consistency
        snap = {"consistency": {"consistency_score": 0.71, "active_days": 10,
                                "total_days": 14, "pattern": "consistent"}}
        result = get_practice_consistency(1, MagicMock(), snapshot=snap)
        assert result["consistency_score"] == 0.71


# ──────────────────────────────────────────────────────────────────────────────
# Difficulty Trends
# ──────────────────────────────────────────────────────────────────────────────

class TestDifficultyTrends:

    def test_promotion_readiness_perfect(self):
        from app.services.analytics.difficulty_trends import get_promotion_readiness
        snap = {"promotion_readiness": 1.0}
        assert get_promotion_readiness(1, "alphabet_practice", MagicMock(), snapshot=snap) == 1.0

    def test_count_promotions_and_demotions(self):
        from app.services.analytics.difficulty_trends import count_promotions_demotions
        history = [
            {"difficulty": "beginner"},
            {"difficulty": "intermediate"},   # promotion
            {"difficulty": "intermediate"},
            {"difficulty": "beginner"},        # demotion
            {"difficulty": "beginner"},
        ]
        result = count_promotions_demotions(history)
        assert result["promotions_count"] == 1
        assert result["demotions_count"] == 1

    def test_no_changes_in_flat_history(self):
        from app.services.analytics.difficulty_trends import count_promotions_demotions
        history = [{"difficulty": "beginner"}] * 5
        result = count_promotions_demotions(history)
        assert result["promotions_count"] == 0
        assert result["demotions_count"] == 0

    def test_empty_history_returns_zero(self):
        from app.services.analytics.difficulty_trends import count_promotions_demotions
        result = count_promotions_demotions([])
        assert result == {"promotions_count": 0, "demotions_count": 0}


# ──────────────────────────────────────────────────────────────────────────────
# Confidence Analyzer
# ──────────────────────────────────────────────────────────────────────────────

class TestConfidenceAnalyzer:

    def test_confidence_high(self):
        from app.services.analytics.confidence_analyzer import get_confidence_level
        h = {"avg_pause_between_strokes_ms": 800, "has_data": True}
        r = {"avg_retries_per_stroke": 1.1, "failsafe_unlock_rate": 0.02, "has_data": True}
        assert get_confidence_level(h, r, "low", {}) == "high"

    def test_confidence_low_high_pause(self):
        from app.services.analytics.confidence_analyzer import get_confidence_level
        h = {"avg_pause_between_strokes_ms": 4000, "has_data": True}
        r = {"avg_retries_per_stroke": 1.0, "failsafe_unlock_rate": 0.01, "has_data": True}
        assert get_confidence_level(h, r, "low", {}) == "low"

    def test_confidence_unknown_no_data(self):
        from app.services.analytics.confidence_analyzer import get_confidence_level
        h = {"has_data": False}
        r = {"has_data": False}
        assert get_confidence_level(h, r, "low", {}) == "unknown"

    def test_frustration_high(self):
        from app.services.analytics.confidence_analyzer import get_frustration_level
        h = {"avg_pause_between_strokes_ms": 3000, "has_data": True}
        r = {"avg_retries_per_stroke": 3.0, "has_data": True}
        rep = {"replay_rate": 0.40}
        assert get_frustration_level(h, r, rep) == "high"

    def test_frustration_low(self):
        from app.services.analytics.confidence_analyzer import get_frustration_level
        h = {"avg_pause_between_strokes_ms": 800, "has_data": True}
        r = {"avg_retries_per_stroke": 1.2, "has_data": True}
        rep = {"replay_rate": 0.05}
        assert get_frustration_level(h, r, rep) == "low"

    def test_frustration_no_telemetry_returns_low(self):
        from app.services.analytics.confidence_analyzer import get_frustration_level
        h = {"has_data": False}
        r = {"has_data": False}
        assert get_frustration_level(h, r, {}) == "low"

    def test_empty_hesitation_snapshot(self):
        from app.services.analytics.confidence_analyzer import get_hesitation_profile
        snap = {"hesitation_profile": {"has_data": False, "avg_pause_before_first_stroke_ms": 0,
                                        "avg_pause_between_strokes_ms": 0,
                                        "high_hesitation_letters": [], "low_hesitation_letters": []}}
        result = get_hesitation_profile(1, MagicMock(), snapshot=snap)
        assert result["has_data"] is False

    def test_empty_retry_snapshot(self):
        from app.services.analytics.confidence_analyzer import get_retry_pattern
        snap = {"retry_pattern": {"avg_retries_per_stroke": 0.0, "high_retry_letters": [],
                                   "failsafe_unlock_rate": 0.0, "has_data": False,
                                   "total_strokes_analyzed": 0}}
        result = get_retry_pattern(1, MagicMock(), snapshot=snap)
        assert result["has_data"] is False


# ──────────────────────────────────────────────────────────────────────────────
# Learning Insight Engine
# ──────────────────────────────────────────────────────────────────────────────

class TestLearningInsightEngine:

    def test_strength_best_letters_generates_insight(self):
        from app.services.analytics.learning_insight_engine import generate_strength_insights
        items = generate_strength_insights(
            best_letters=["L", "I", "T"],
            recovery={"recovers_quickly": False, "avg_improvement_after_retry": 0},
            replay_dependence={"replay_beneficial": False},
            consistency={"consistency_score": 0.50, "pattern": "consistent"},
        )
        assert any(i["code"] == "strong_letters" for i in items)
        assert all(i["severity"] == "positive" for i in items)

    def test_strength_fast_recovery(self):
        from app.services.analytics.learning_insight_engine import generate_strength_insights
        items = generate_strength_insights(
            best_letters=[],
            recovery={"recovers_quickly": True, "avg_improvement_after_retry": 0.12},
            replay_dependence={"replay_beneficial": False},
            consistency={"consistency_score": 0.30},
        )
        assert any(i["code"] == "fast_recovery" for i in items)

    def test_weakness_curved_strokes(self):
        from app.services.analytics.learning_insight_engine import generate_weakness_insights
        items = generate_weakness_insights(
            worst_letters=["S", "G"],
            direction_struggle=["curve-left", "curve-right"],
            retry_pattern={"avg_retries_per_stroke": 1.0, "high_retry_letters": []},
            trend="stable",
        )
        assert any(i["code"] == "curved_strokes" for i in items)

    def test_weakness_declining_trend(self):
        from app.services.analytics.learning_insight_engine import generate_weakness_insights
        items = generate_weakness_insights(
            worst_letters=[], direction_struggle=[],
            retry_pattern={"avg_retries_per_stroke": 0.0, "high_retry_letters": []},
            trend="declining",
        )
        assert any(i["code"] == "declining_accuracy" for i in items)
        assert any(i["severity"] == "high" for i in items)

    def test_behavioral_frustration_high(self):
        from app.services.analytics.learning_insight_engine import generate_behavioral_insights
        items = generate_behavioral_insights(
            hesitation={"has_data": True, "avg_pause_between_strokes_ms": 3000, "high_hesitation_letters": ["S"]},
            frustration_level="high",
            replay_dependence={"replay_rate": 0.10, "replay_beneficial": False},
            consistency={"consistency_score": 0.50, "pattern": "consistent"},
            engagement_level="medium",
        )
        assert any(i["code"] == "frustration_risk" for i in items)
        assert any(i["severity"] == "high" for i in items)

    def test_behavioral_irregular_practice(self):
        from app.services.analytics.learning_insight_engine import generate_behavioral_insights
        items = generate_behavioral_insights(
            hesitation={"has_data": False, "avg_pause_between_strokes_ms": 0, "high_hesitation_letters": []},
            frustration_level="low",
            replay_dependence={"replay_rate": 0.0, "replay_beneficial": False},
            consistency={"consistency_score": 0.20, "pattern": "irregular"},
            engagement_level="medium",
        )
        assert any(i["code"] == "irregular_practice" for i in items)

    def test_recommended_focus_ready_to_advance(self):
        from app.services.analytics.learning_insight_engine import generate_recommended_focus
        result = generate_recommended_focus(
            worst_letters=[], frustration_level="low",
            promotion_readiness=0.90, trend="improving", avg_accuracy=0.87,
        )
        assert result == "ready_to_advance"

    def test_recommended_focus_review_basics(self):
        from app.services.analytics.learning_insight_engine import generate_recommended_focus
        result = generate_recommended_focus(
            worst_letters=["S","G"], frustration_level="medium",
            promotion_readiness=0.30, trend="declining", avg_accuracy=0.40,
        )
        assert result == "review_basics"

    def test_recommended_focus_needs_practice(self):
        from app.services.analytics.learning_insight_engine import generate_recommended_focus
        result = generate_recommended_focus(
            worst_letters=["S"], frustration_level="high",
            promotion_readiness=0.40, trend="stable", avg_accuracy=0.55,
        )
        assert result == "needs_more_practice"

    def test_recommended_focus_maintain(self):
        from app.services.analytics.learning_insight_engine import generate_recommended_focus
        result = generate_recommended_focus(
            worst_letters=[], frustration_level="low",
            promotion_readiness=0.70, trend="stable", avg_accuracy=0.75,
        )
        assert result == "maintain_consistency"

    def test_insight_items_have_required_keys(self):
        from app.services.analytics.learning_insight_engine import generate_strength_insights
        items = generate_strength_insights(
            best_letters=["A"],
            recovery={"recovers_quickly": True, "avg_improvement_after_retry": 0.10},
            replay_dependence={"replay_beneficial": True},
            consistency={"consistency_score": 0.80, "pattern": "consistent"},
        )
        for item in items:
            assert "code"     in item
            assert "severity" in item
            assert "message"  in item
            assert item["severity"] in ("positive", "low", "medium", "high")

    def test_no_best_letters_no_crash(self):
        from app.services.analytics.learning_insight_engine import generate_strength_insights
        # Should not raise even with empty inputs
        items = generate_strength_insights(
            best_letters=[], recovery={}, replay_dependence={}, consistency={},
        )
        assert isinstance(items, list)


# ──────────────────────────────────────────────────────────────────────────────
# Reward service: longest_streak
# ──────────────────────────────────────────────────────────────────────────────

class TestLongestStreak:

    def _make_user(self, streak=0, longest=0, last=None):
        from datetime import date
        u = MagicMock()
        u.user_streak     = streak
        u.longest_streak  = longest
        u.last_active_date = last
        return u

    def test_longest_streak_updated_on_new_record(self):
        from app.services.reward_service import update_streak
        from datetime import date, timedelta
        user = self._make_user(streak=5, longest=5,
                               last=date.today() - timedelta(days=1))
        new_streak = update_streak(user)
        assert new_streak == 6
        assert user.longest_streak == 6

    def test_longest_streak_not_overwritten_if_lower(self):
        from app.services.reward_service import update_streak
        from datetime import date, timedelta
        # Gap → streak resets to 1, longest stays at 10
        user = self._make_user(streak=10, longest=10,
                               last=date.today() - timedelta(days=5))
        update_streak(user)
        assert user.user_streak == 1
        assert user.longest_streak == 10   # preserved

    def test_longest_streak_initialized_from_first_session(self):
        from app.services.reward_service import update_streak
        user = self._make_user(streak=0, longest=0, last=None)
        update_streak(user)
        assert user.user_streak    == 1
        assert user.longest_streak == 1
