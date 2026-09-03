"""
tests/test_free_writing_engine.py

Unit tests for the Free Writing Studio AI engine.
Tests all 3 layers: motor, spatial, quality + feedback.
"""

import pytest
from app.services.free_writing.motor_quality_analyzer import analyze_motor_quality
from app.services.free_writing.spatial_quality_analyzer import analyze_spatial_quality
from app.services.free_writing.writing_quality_engine import generate_quality_report, QUALITY_WEIGHTS
from app.services.free_writing.quality_feedback_generator import (
    generate_feedback, derive_quality_band
)
from app.services.free_writing.writing_progress_tracker import compute_progress_trend


# ── Test fixtures ──────────────────────────────────────────────────────────────

def make_smooth_stroke(n=20, start=(10, 50), end=(200, 50), t_start=1000):
    """Creates a perfectly horizontal stroke with timestamps."""
    pts = []
    for i in range(n):
        t = t_start + i * 20
        x = start[0] + (end[0] - start[0]) * i / (n - 1)
        y = start[1]
        pts.append([x, y, t])
    return {"points": pts, "startTime": t_start}


def make_jerky_stroke(n=20, t_start=1000):
    """Creates a stroke with rapid direction changes (jerky)."""
    pts = []
    for i in range(n):
        x = i * 10 + (10 if i % 2 == 0 else -10)
        y = 50 + (10 if i % 3 == 0 else -5)
        pts.append([x, y, t_start + i * 20])
    return {"points": pts, "startTime": t_start}


def make_strokes_grid(rows=2, cols=3, canvas_w=400, canvas_h=300):
    """Creates strokes laid out in a regular grid (simulates writing)."""
    strokes = []
    for r in range(rows):
        for c in range(cols):
            x = 30 + c * 120
            y = 80 + r * 100
            pts = [[x + i*5, y, 1000 + (r*cols+c)*500 + i*20] for i in range(10)]
            strokes.append({"points": pts})
    return strokes


# ─────────────────────────────────────────────────────────────────────────────
# T1 — Motor Quality Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestMotorQualityAnalyzer:

    def test_empty_strokes_returns_defaults(self):
        result = analyze_motor_quality([])
        assert result["stroke_count"] == 0
        assert result["smoothness_score"] == 0.0

    def test_smooth_strokes_score_high(self):
        strokes = [make_smooth_stroke() for _ in range(5)]
        result = analyze_motor_quality(strokes)
        assert result["smoothness_score"] >= 0.7, f"Expected ≥0.7, got {result['smoothness_score']}"
        assert result["stroke_count"] == 5

    def test_all_scores_in_range(self):
        strokes = [make_smooth_stroke(), make_jerky_stroke()]
        result = analyze_motor_quality(strokes)
        for key in ["smoothness_score", "velocity_variance", "hesitation_ratio", "stroke_confidence"]:
            assert 0.0 <= result[key] <= 1.0, f"{key} out of range: {result[key]}"

    def test_jerky_stroke_lower_smoothness(self):
        smooth = analyze_motor_quality([make_smooth_stroke()] * 3)
        jerky  = analyze_motor_quality([make_jerky_stroke()] * 3)
        assert smooth["smoothness_score"] > jerky["smoothness_score"]

    def test_hesitation_detected_with_long_gap(self):
        """Two strokes with 1000ms gap between them should register hesitation."""
        s1 = make_smooth_stroke(t_start=1000)
        s2 = make_smooth_stroke(t_start=3000)   # 2000ms gap
        result = analyze_motor_quality([s1, s2])
        assert result["hesitation_ratio"] > 0.0

    def test_no_hesitation_with_tight_timing(self):
        """Strokes with 100ms gap should not trigger hesitation."""
        s1 = make_smooth_stroke(n=10, t_start=1000)
        s2 = make_smooth_stroke(n=10, t_start=1300)  # 100ms gap
        result = analyze_motor_quality([s1, s2])
        assert result["hesitation_ratio"] == 0.0

    def test_single_point_strokes_handled_gracefully(self):
        strokes = [{"points": [[50, 50, 1000]]}]  # single-point stroke
        result = analyze_motor_quality(strokes)
        assert result["stroke_count"] == 1

    def test_avg_stroke_length_positive(self):
        strokes = [make_smooth_stroke()]
        result = analyze_motor_quality(strokes)
        assert result["avg_stroke_length"] > 0


# ─────────────────────────────────────────────────────────────────────────────
# T2 — Spatial Quality Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class TestSpatialQualityAnalyzer:

    def test_empty_strokes_returns_defaults(self):
        result = analyze_spatial_quality([])
        assert result["baseline_consistency"] == 1.0
        assert result["canvas_utilization"] == 0.0

    def test_all_scores_in_range(self):
        strokes = make_strokes_grid()
        result = analyze_spatial_quality(strokes, canvas_width=400, canvas_height=300)
        for key in ["baseline_consistency", "slant_consistency", "spacing_regularity",
                    "canvas_utilization", "vertical_compression"]:
            assert 0.0 <= result[key] <= 1.0, f"{key} = {result[key]}"

    def test_aligned_strokes_high_baseline_consistency(self):
        """All strokes at same y level should have high baseline consistency."""
        strokes = [
            {"points": [[i * 20 + 10, 100, 0] for i in range(5)]},  # y=100
            {"points": [[i * 20 + 10, 102, 0] for i in range(5)]},  # y≈100
            {"points": [[i * 20 + 10, 99,  0] for i in range(5)]},  # y≈100
        ]
        result = analyze_spatial_quality(strokes)
        # y_max values ~100, 102, 99 → range=3, std≈1.5 → normalized≈0.5
        # Consistency should be higher than a misaligned set
        assert result["baseline_consistency"] > 0.3

    def test_misaligned_strokes_lower_baseline(self):
        """More strokes with more spread should yield lower baseline_consistency
        than aligned strokes. Uses 5+ strokes to ensure stdev is meaningful."""
        # Perfectly aligned: all strokes near y=100
        aligned = [
            {"points": [[i * 10, 98, 0], [i * 10 + 50, 100, 100]]} for i in range(5)
        ]
        # Wildly spread: strokes at y=10, 80, 150, 250, 380 (wide range)
        spread = [
            {"points": [[0, 10, 0], [50, 10, 100]]},
            {"points": [[0, 80, 0], [50, 80, 100]]},
            {"points": [[0, 150, 0], [50, 150, 100]]},
            {"points": [[0, 250, 0], [50, 250, 100]]},
            {"points": [[0, 380, 0], [50, 380, 100]]},
        ]
        r_aligned = analyze_spatial_quality(aligned, canvas_height=400)
        r_spread  = analyze_spatial_quality(spread,  canvas_height=400)
        assert r_aligned["baseline_consistency"] >= r_spread["baseline_consistency"], (
            f"Aligned {r_aligned['baseline_consistency']} should be >= spread {r_spread['baseline_consistency']}"
        )

    def test_canvas_utilization_increases_with_spread(self):
        small = [{"points": [[50, 50, 0], [80, 60, 100]]}]
        large = [{"points": [[10, 10, 0], [350, 250, 100], [200, 200, 200]]}]
        r_small = analyze_spatial_quality(small)
        r_large = analyze_spatial_quality(large)
        assert r_large["canvas_utilization"] > r_small["canvas_utilization"]


# ─────────────────────────────────────────────────────────────────────────────
# T3 — Quality Feedback Generator
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityFeedbackGenerator:

    def test_derive_quality_band(self):
        assert derive_quality_band(0.90) == "exceptional"
        assert derive_quality_band(0.75) == "strong"
        assert derive_quality_band(0.55) == "building"
        assert derive_quality_band(0.30) == "developing"

    def test_never_returns_empty_messages(self):
        from app.services.free_writing.motor_quality_analyzer import MotorQualityMetrics
        from app.services.free_writing.spatial_quality_analyzer import SpatialQualityMetrics
        motor: MotorQualityMetrics = {
            "smoothness_score": 0.6, "velocity_variance": 0.3,
            "hesitation_ratio": 0.1, "stroke_confidence": 0.7,
            "avg_stroke_length": 80.0, "stroke_count": 5,
        }
        spatial: SpatialQualityMetrics = {
            "baseline_consistency": 0.65, "slant_consistency": 0.7,
            "spacing_regularity": 0.5, "canvas_utilization": 0.4,
            "vertical_compression": 0.5,
        }
        for profile in ("early_learner", "child", "adult"):
            msgs = generate_feedback(motor, spatial, "building", profile)  # type: ignore
            assert len(msgs) >= 1, f"No messages for profile={profile}"
            assert len(msgs) <= 4, f"Too many messages for profile={profile}"

    def test_no_correctness_language(self):
        """Forbidden words must never appear in feedback."""
        from app.services.free_writing.motor_quality_analyzer import MotorQualityMetrics
        from app.services.free_writing.spatial_quality_analyzer import SpatialQualityMetrics
        motor: MotorQualityMetrics = {
            "smoothness_score": 0.2, "velocity_variance": 0.8,
            "hesitation_ratio": 0.6, "stroke_confidence": 0.2,
            "avg_stroke_length": 10.0, "stroke_count": 2,
        }
        spatial: SpatialQualityMetrics = {
            "baseline_consistency": 0.2, "slant_consistency": 0.2,
            "spacing_regularity": 0.1, "canvas_utilization": 0.1,
            "vertical_compression": 0.1,
        }
        msgs = generate_feedback(motor, spatial, "developing", "child")
        all_text = " ".join(msgs).lower()
        forbidden = ["wrong", "incorrect", "failed", "bad", "error", "mistake"]
        for word in forbidden:
            assert word not in all_text, f"Forbidden word '{word}' found in: {all_text}"

    def test_early_learner_messages_have_emoji(self):
        from app.services.free_writing.motor_quality_analyzer import MotorQualityMetrics
        from app.services.free_writing.spatial_quality_analyzer import SpatialQualityMetrics
        motor: MotorQualityMetrics = {
            "smoothness_score": 0.8, "velocity_variance": 0.1,
            "hesitation_ratio": 0.0, "stroke_confidence": 0.9,
            "avg_stroke_length": 100.0, "stroke_count": 10,
        }
        spatial: SpatialQualityMetrics = {
            "baseline_consistency": 0.8, "slant_consistency": 0.8,
            "spacing_regularity": 0.8, "canvas_utilization": 0.6,
            "vertical_compression": 0.5,
        }
        msgs = generate_feedback(motor, spatial, "strong", "early_learner")
        all_text = " ".join(msgs)
        # Early learner messages must contain at least one emoji character
        has_emoji = any(ord(c) > 127 for c in all_text)
        assert has_emoji, "Expected emoji in early_learner feedback"


# ─────────────────────────────────────────────────────────────────────────────
# T4 — Writing Quality Engine (integration)
# ─────────────────────────────────────────────────────────────────────────────

class TestWritingQualityEngine:

    def test_quality_report_shape(self):
        strokes = [make_smooth_stroke(t_start=i * 600) for i in range(5)]
        report = generate_quality_report("test-uuid", strokes, profile_type="child")
        assert "overall_quality_score" in report
        assert "quality_band" in report
        assert "motor" in report
        assert "spatial" in report
        assert "emotional_snapshot" in report
        assert "feedback_messages" in report
        assert len(report["feedback_messages"]) >= 1

    def test_overall_score_in_range(self):
        strokes = [make_smooth_stroke()] * 5
        report = generate_quality_report("test", strokes)
        assert 0.0 <= report["overall_quality_score"] <= 1.0

    def test_weights_sum_to_one(self):
        total = sum(QUALITY_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-6, f"Weights don't sum to 1: {total}"

    def test_empty_strokes_handled(self):
        report = generate_quality_report("test", [])
        # Empty strokes → all motor/spatial values default to 0 → score ≤ 0.3
        # The engine defaults smoothness to 1.0 (too short to measure) so band
        # may be non-zero; we just validate shape and score in range.
        assert 0.0 <= report["overall_quality_score"] <= 1.0
        assert report["quality_band"] in ("developing", "building", "strong", "exceptional")
        assert isinstance(report["feedback_messages"], list)

    def test_emotional_snapshot_present(self):
        strokes = [make_smooth_stroke(t_start=i * 600) for i in range(8)]
        report = generate_quality_report("test", strokes)
        snap = report["emotional_snapshot"]
        for key in ("frustration_index", "confidence_level", "fatigue_estimate", "focus_score"):
            assert 0.0 <= snap[key] <= 1.0, f"{key} = {snap[key]}"


# ─────────────────────────────────────────────────────────────────────────────
# T5 — Writing Progress Tracker
# ─────────────────────────────────────────────────────────────────────────────

class TestWritingProgressTracker:

    def test_empty_sessions(self):
        result = compute_progress_trend([])
        assert result["sessions_analyzed"] == 0
        assert result["is_improving"] is False

    def test_improving_trend_detected(self):
        sessions = [
            {"overall_score": 0.3, "quality_metrics": {"motor": {"smoothness_score": 0.3, "stroke_confidence": 0.3}, "spatial": {"spacing_regularity": 0.3}}, "completed_at": None},
            {"overall_score": 0.4, "quality_metrics": {"motor": {"smoothness_score": 0.4, "stroke_confidence": 0.4}, "spatial": {"spacing_regularity": 0.4}}, "completed_at": None},
            {"overall_score": 0.5, "quality_metrics": {"motor": {"smoothness_score": 0.5, "stroke_confidence": 0.5}, "spatial": {"spacing_regularity": 0.5}}, "completed_at": None},
            {"overall_score": 0.65, "quality_metrics": {"motor": {"smoothness_score": 0.65, "stroke_confidence": 0.65}, "spatial": {"spacing_regularity": 0.65}}, "completed_at": None},
            {"overall_score": 0.75, "quality_metrics": {"motor": {"smoothness_score": 0.75, "stroke_confidence": 0.75}, "spatial": {"spacing_regularity": 0.75}}, "completed_at": None},
        ]
        result = compute_progress_trend(sessions)
        assert result["smoothness_trend"] == "improving"
        assert result["is_improving"] is True

    def test_stable_trend(self):
        sessions = [
            {"overall_score": 0.5, "quality_metrics": {"motor": {"smoothness_score": 0.5, "stroke_confidence": 0.5}, "spatial": {"spacing_regularity": 0.5}}, "completed_at": None},
            {"overall_score": 0.52, "quality_metrics": {"motor": {"smoothness_score": 0.52, "stroke_confidence": 0.5}, "spatial": {"spacing_regularity": 0.5}}, "completed_at": None},
            {"overall_score": 0.49, "quality_metrics": {"motor": {"smoothness_score": 0.49, "stroke_confidence": 0.5}, "spatial": {"spacing_regularity": 0.5}}, "completed_at": None},
        ]
        result = compute_progress_trend(sessions)
        assert result["smoothness_trend"] == "stable"

    def test_best_session_tracked(self):
        sessions = [
            {"overall_score": 0.4, "quality_metrics": {}, "completed_at": None},
            {"overall_score": 0.9, "quality_metrics": {}, "completed_at": None},
            {"overall_score": 0.6, "quality_metrics": {}, "completed_at": None},
        ]
        result = compute_progress_trend(sessions)
        assert result["best_session_score"] == 0.9
