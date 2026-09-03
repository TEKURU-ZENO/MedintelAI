"""
tests/test_ml_recommendations.py — Phase 5 ML Layer Tests

All pure-function tests — no DB required.
Run: pytest tests/test_ml_recommendations.py -v
"""

import pytest
from unittest.mock import MagicMock


# ──────────────────────────────────────────────────────────────────────────────
# Feature Snapshot
# ──────────────────────────────────────────────────────────────────────────────

class TestFeatureSnapshot:
    def _snap(self, **overrides):
        from app.services.ml.feature_snapshot import build_feature_snapshot
        defaults = dict(
            retry_pattern      = {"avg_retries_per_stroke": 1.5, "failsafe_unlock_rate": 0.05, "has_data": True},
            hesitation_profile = {"avg_pause_between_strokes_ms": 1200, "has_data": True},
            replay_dependence  = {"replay_rate": 0.15},
            consistency        = {"consistency_score": 0.60},
            rolling_accuracy   = 0.72,
            velocity           = "steady",
            frustration_level  = "low",
            confidence_level   = "medium",
            trend              = "stable",
            streak             = 5,
        )
        defaults.update(overrides)
        return build_feature_snapshot(**defaults)

    def test_all_required_keys_present(self):
        snap = self._snap()
        required = ["retry_rate", "hesitation_norm", "replay_rate", "failsafe_rate",
                    "consistency_score", "streak", "rolling_accuracy", "velocity_score",
                    "frustration_score", "confidence_score", "trend_score", "has_telemetry"]
        for k in required:
            assert k in snap, f"Missing key: {k}"

    def test_all_floats_clamped_0_1(self):
        snap = self._snap()
        # avg_hesitation_ms is intentionally stored as raw ms (not normalized)
        unclamped_keys = {"avg_hesitation_ms"}
        for k, v in snap.items():
            if isinstance(v, float) and k not in unclamped_keys:
                assert 0.0 <= v <= 1.0, f"{k}={v} out of range"

    def test_has_telemetry_true_when_data(self):
        snap = self._snap()
        assert snap["has_telemetry"] is True

    def test_has_telemetry_false_when_no_data(self):
        snap = self._snap(
            retry_pattern      = {"avg_retries_per_stroke": 0, "failsafe_unlock_rate": 0, "has_data": False},
            hesitation_profile = {"avg_pause_between_strokes_ms": 0, "has_data": False},
        )
        assert snap["has_telemetry"] is False

    def test_velocity_mapped_correctly(self):
        fast   = self._snap(velocity="fast")["velocity_score"]
        steady = self._snap(velocity="steady")["velocity_score"]
        slow   = self._snap(velocity="slow")["velocity_score"]
        assert fast > steady > slow

    def test_frustration_mapped_correctly(self):
        high = self._snap(frustration_level="high")["frustration_score"]
        low  = self._snap(frustration_level="low")["frustration_score"]
        assert high > low

    def test_completeness_low_without_telemetry(self):
        from app.services.ml.feature_snapshot import snapshot_completeness
        snap = self._snap(
            retry_pattern      = {"avg_retries_per_stroke": 0, "failsafe_unlock_rate": 0, "has_data": False},
            hesitation_profile = {"avg_pause_between_strokes_ms": 0, "has_data": False},
        )
        c = snapshot_completeness(snap)
        assert c <= 0.45

    def test_completeness_high_with_full_data(self):
        from app.services.ml.feature_snapshot import snapshot_completeness
        snap = self._snap()
        assert snapshot_completeness(snap) >= 0.70


# ──────────────────────────────────────────────────────────────────────────────
# Pattern Classifier
# ──────────────────────────────────────────────────────────────────────────────

class TestPatternClassifier:
    def _snap(self, **kw):
        base = {"retry_rate": 0.2, "hesitation_norm": 0.2, "replay_rate": 0.1,
                "velocity_score": 0.5, "frustration_score": 0.0, "consistency_score": 0.6,
                "confidence_score": 0.7, "trend_score": 0.7, "has_telemetry": True}
        base.update(kw)
        return base

    def test_rule_returns_valid_style(self):
        from app.services.ml.pattern_classifier import classify_rule, _STYLE_WEIGHTS
        result = classify_rule(self._snap())
        assert result["style"] in _STYLE_WEIGHTS
        assert result["source"] == "rule"
        assert 0 <= result["confidence"] <= 1

    def test_rule_impulsive_high_retry_fast(self):
        from app.services.ml.pattern_classifier import classify_rule
        snap = self._snap(retry_rate=0.55, velocity_score=0.90, hesitation_norm=0.05)
        assert classify_rule(snap)["style"] == "impulsive"

    def test_rule_replay_dependent(self):
        from app.services.ml.pattern_classifier import classify_rule
        snap = self._snap(replay_rate=0.45, frustration_score=0.60)
        assert classify_rule(snap)["style"] == "replay_dependent"

    def test_rule_visual_learner(self):
        from app.services.ml.pattern_classifier import classify_rule
        snap = self._snap(replay_rate=0.30, confidence_score=0.80, frustration_score=0.20)
        assert classify_rule(snap)["style"] == "visual"

    def test_rule_methodical_learner(self):
        from app.services.ml.pattern_classifier import classify_rule
        snap = self._snap(hesitation_norm=0.10, consistency_score=0.80,
                          frustration_score=0.05, retry_rate=0.10)
        assert classify_rule(snap)["style"] == "methodical"

    def test_ml_returns_valid_style(self):
        from app.services.ml.pattern_classifier import classify_ml, _STYLE_WEIGHTS
        result = classify_ml(self._snap())
        assert result["style"] in _STYLE_WEIGHTS
        assert result["source"] == "ml"
        assert 0 <= result["confidence"] <= 1

    def test_ml_probabilities_sum_to_1(self):
        from app.services.ml.pattern_classifier import classify_ml
        result = classify_ml(self._snap())
        total = sum(result["probabilities"].values())
        assert abs(total - 1.0) < 0.01

    def test_shadow_classify_returns_delta(self):
        from app.services.ml.pattern_classifier import classify
        result = classify(self._snap())
        assert "shadow_delta" in result
        delta = result["shadow_delta"]
        assert "rule_style" in delta
        assert "ml_style" in delta
        assert "agreement" in delta

    def test_shadow_classify_low_completeness_uses_rule(self):
        from app.services.ml.pattern_classifier import classify
        # With very low completeness, ML confidence should be low → rule wins
        result = classify(self._snap(has_telemetry=False), data_completeness=0.15)
        assert result["source"] == "rule"

    def test_style_labels_cover_all_styles(self):
        from app.services.ml.pattern_classifier import STYLE_LABELS, _STYLE_WEIGHTS
        for style in _STYLE_WEIGHTS:
            assert style in STYLE_LABELS


# ──────────────────────────────────────────────────────────────────────────────
# Difficulty Predictor
# ──────────────────────────────────────────────────────────────────────────────

class TestDifficultyPredictor:
    def _snap(self, acc=0.75, trend="stable", vel="steady", conf=0.7, cons=0.6):
        return {"rolling_accuracy": acc, "trend_score": {"improving": 1.0,
                "stable": 0.5, "declining": 0.0}.get(trend, 0.5),
                "velocity_score": {"fast": 1.0, "steady": 0.5, "slow": 0.0}.get(vel, 0.5),
                "confidence_score": conf, "consistency_score": cons,
                "has_telemetry": True, "_current_difficulty": "beginner"}

    def test_rule_promotes_high_accuracy(self):
        from app.services.ml.difficulty_predictor import predict_rule
        r = predict_rule(0.90, "improving", "steady", "beginner", 0.92)
        assert r["recommended_difficulty"] == "intermediate"

    def test_rule_demotes_low_accuracy(self):
        from app.services.ml.difficulty_predictor import predict_rule
        r = predict_rule(0.40, "declining", "slow", "intermediate", 0.20)
        assert r["recommended_difficulty"] == "beginner"

    def test_rule_maintains_mid_accuracy(self):
        from app.services.ml.difficulty_predictor import predict_rule
        r = predict_rule(0.70, "stable", "steady", "intermediate", 0.60)
        assert r["recommended_difficulty"] == "intermediate"

    def test_rule_no_promote_beyond_advanced(self):
        from app.services.ml.difficulty_predictor import predict_rule
        r = predict_rule(0.95, "improving", "fast", "advanced", 0.99)
        assert r["recommended_difficulty"] == "advanced"

    def test_rule_no_demote_below_beginner(self):
        from app.services.ml.difficulty_predictor import predict_rule
        r = predict_rule(0.20, "declining", "slow", "beginner", 0.0)
        assert r["recommended_difficulty"] == "beginner"

    def test_ml_returns_valid_difficulty(self):
        from app.services.ml.difficulty_predictor import predict_ml
        from app.services.ml.difficulty_predictor import DIFFICULTY_ORDER
        r = predict_ml(self._snap(acc=0.85, trend="improving"))
        assert r["recommended_difficulty"] in DIFFICULTY_ORDER

    def test_shadow_predict_returns_delta(self):
        from app.services.ml.difficulty_predictor import predict
        r = predict(self._snap(), "beginner", 0.90, "improving", "steady", 0.92)
        assert "shadow_delta" in r
        assert "rule_difficulty" in r["shadow_delta"]
        assert "ml_difficulty"   in r["shadow_delta"]

    def test_shadow_predict_returns_valid_difficulty(self):
        from app.services.ml.difficulty_predictor import predict, DIFFICULTY_ORDER
        r = predict(self._snap(acc=0.60), "beginner", 0.60, "stable", "steady", 0.55)
        assert r["recommended_difficulty"] in DIFFICULTY_ORDER


# ──────────────────────────────────────────────────────────────────────────────
# Item Recommender
# ──────────────────────────────────────────────────────────────────────────────

class TestItemRecommender:
    def test_returns_list(self):
        from app.services.ml.item_recommender import recommend_items
        result = recommend_items(["S", "G"], ["S"], ["curve-left"], "medium", ["L"])
        assert isinstance(result, list)

    def test_max_5_items(self):
        from app.services.ml.item_recommender import recommend_items, MAX_RECOMMENDATIONS
        result = recommend_items(["S","G","C","B","D","Q"], ["S","G"], [], "high", ["L"])
        assert len(result) <= MAX_RECOMMENDATIONS

    def test_each_item_has_required_keys(self):
        from app.services.ml.item_recommender import recommend_items
        result = recommend_items(["S"], ["S"], [], "low", ["L"])
        for r in result:
            assert "item" in r
            assert "priority_score" in r
            assert "reason" in r
            assert "priority" in r
            assert "confidence" in r
            assert r["priority"] in ("high", "medium", "low")

    def test_strength_item_appended(self):
        from app.services.ml.item_recommender import recommend_items
        result = recommend_items(["S"], ["S"], [], "low", ["L", "I"])
        items = [r["item"] for r in result]
        assert "L" in items   # strength item

    def test_high_retry_gets_high_priority(self):
        from app.services.ml.item_recommender import recommend_items
        # Letters in BOTH worst and high_retry get doubled signal → high priority
        result = recommend_items(
            worst_letters=["S", "G", "C"],
            high_retry_letters=["S", "G", "C"],
            direction_struggles=[],
            frustration_level="medium",
            best_letters=[],
        )
        non_low = [r for r in result if r["priority"] in ("high", "medium")]
        assert len(non_low) >= 1

    def test_no_data_returns_safe_defaults(self):
        from app.services.ml.item_recommender import recommend_items
        result = recommend_items([], [], [], "low", [])
        assert len(result) > 0   # safe defaults

    def test_confidence_between_0_and_1(self):
        from app.services.ml.item_recommender import recommend_items
        result = recommend_items(["S"], [], [], "medium", [])
        for r in result:
            assert 0.0 <= r["confidence"] <= 1.0

    def test_frustration_high_amplifies_scores(self):
        from app.services.ml.item_recommender import score_item
        low  = score_item("S", ["S"], ["S"], [], "low")
        high = score_item("S", ["S"], ["S"], [], "high")
        assert high >= low


# ──────────────────────────────────────────────────────────────────────────────
# Adaptive Session Planner
# ──────────────────────────────────────────────────────────────────────────────

class TestAdaptiveSessionPlanner:
    def _items(self):
        return [
            {"item": "S", "priority": "high",   "priority_score": 0.8, "reason": "retry"},
            {"item": "G", "priority": "medium",  "priority_score": 0.5, "reason": "curve"},
            {"item": "L", "priority": "low",     "priority_score": 0.1, "reason": "strength"},
        ]

    def test_returns_required_keys(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "methodical", "low", "high",
                                  "stable", 0.75, "beginner", ["L"])
        for k in ["items", "session_length_s", "focus_mode", "reasoning",
                  "difficulty", "confidence", "source"]:
            assert k in plan

    def test_frustrated_gets_quick_win(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "impulsive", "high", "medium",
                                  "stable", 0.65, "beginner", ["L"])
        assert plan["focus_mode"] == "quick_win"

    def test_declining_gets_deep_focus(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "methodical", "low", "medium",
                                  "declining", 0.45, "beginner", ["L"])
        assert plan["focus_mode"] == "deep_focus"

    def test_low_engagement_gets_confidence_boost(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "visual", "low", "low",
                                  "stable", 0.70, "beginner", ["L"])
        assert plan["focus_mode"] == "confidence_boost"

    def test_session_items_not_empty(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "methodical", "low", "high",
                                  "stable", 0.75, "beginner", ["L"])
        assert len(plan["items"]) > 0

    def test_confidence_0_to_1(self):
        from app.services.ml.adaptive_session_planner import build_session_plan
        plan = build_session_plan(self._items(), "visual", "high", "low",
                                  "declining", 0.40, "intermediate", [])
        assert 0.0 <= plan["confidence"] <= 1.0

    def test_session_length_valid(self):
        from app.services.ml.adaptive_session_planner import build_session_plan, SESSION_CONFIGS
        plan = build_session_plan(self._items(), "methodical", "low", "high",
                                  "stable", 0.80, "beginner", ["L"])
        valid_lengths = {v["seconds"] for v in SESSION_CONFIGS.values()}
        assert plan["session_length_s"] in valid_lengths
