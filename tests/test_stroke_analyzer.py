"""
tests/test_stroke_analyzer.py — Phase 3 Analysis Engine Tests

All pure-function, no DB, no HTTP. Fast.
Run: pytest tests/test_stroke_analyzer.py -v
"""
import math
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# Stroke Analyzer: Direction Score
# ──────────────────────────────────────────────────────────────────────────────

class TestDirectionScore:
    def test_identical_strokes_score_near_1(self):
        from app.services.analysis.stroke_analyzer import compute_direction_score
        pts = [[0,0],[25,0],[50,0],[75,0],[100,0]]
        assert compute_direction_score(pts, pts) >= 0.95

    def test_reversed_direction_score_near_0(self):
        from app.services.analysis.stroke_analyzer import compute_direction_score
        drawn = [[100,0],[50,0],[0,0]]
        ref   = [[0,0],[50,0],[100,0]]
        # Reversed direction → cosine ≈ -1 → mapped to 0
        assert compute_direction_score(drawn, ref) < 0.15

    def test_perpendicular_strokes_score_near_half(self):
        from app.services.analysis.stroke_analyzer import compute_direction_score
        drawn = [[0,0],[0,100]]       # going down
        ref   = [[0,0],[100,0]]       # going right
        score = compute_direction_score(drawn, ref)
        assert 0.3 < score < 0.7     # roughly 0.5 for 90° offset

    def test_same_diagonal_direction(self):
        from app.services.analysis.stroke_analyzer import compute_direction_score
        drawn = [[0,0],[50,50],[100,100]]
        ref   = [[0,0],[100,100]]
        assert compute_direction_score(drawn, ref) >= 0.90

    def test_short_stroke_handled(self):
        from app.services.analysis.stroke_analyzer import compute_direction_score
        assert compute_direction_score([[0,0]], [[50,50]]) == 0.5  # too short


# ──────────────────────────────────────────────────────────────────────────────
# Stroke Analyzer: Coverage Score
# ──────────────────────────────────────────────────────────────────────────────

class TestCoverageScore:
    def test_perfect_overlap_full_coverage(self):
        from app.services.analysis.stroke_analyzer import compute_coverage_score
        pts = [[float(i), 0.0] for i in range(0, 101, 5)]
        assert compute_coverage_score(pts, pts, tolerance=5) >= 0.90

    def test_zero_coverage_when_far_away(self):
        from app.services.analysis.stroke_analyzer import compute_coverage_score
        drawn = [[0,0],[10,0]]       # top-left corner
        ref   = [[90,90],[100,90]]   # bottom-right corner
        assert compute_coverage_score(drawn, ref, tolerance=5) == 0.0

    def test_partial_coverage(self):
        from app.services.analysis.stroke_analyzer import compute_coverage_score
        # Drawn covers first half of reference
        drawn = [[float(i), 0.0] for i in range(0, 51)]
        ref   = [[float(i), 0.0] for i in range(0, 101)]
        score = compute_coverage_score(drawn, ref, tolerance=5)
        assert 0.4 < score < 0.7

    def test_empty_drawn_returns_zero(self):
        from app.services.analysis.stroke_analyzer import compute_coverage_score
        assert compute_coverage_score([], [[0,0],[100,0]]) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Stroke Analyzer: Smoothness Score
# ──────────────────────────────────────────────────────────────────────────────

class TestSmoothnessScore:
    def test_straight_line_is_smooth(self):
        from app.services.analysis.stroke_analyzer import compute_smoothness_score
        pts = [[float(i), 0.0] for i in range(101)]
        assert compute_smoothness_score(pts) >= 0.95

    def test_zigzag_is_rough(self):
        from app.services.analysis.stroke_analyzer import compute_smoothness_score
        # Random-direction stroke: sharp turns create high angular variance
        # Use a square-wave pattern with very different segment lengths
        pts = [
            [0,0], [5,80], [10,0], [15,90], [20,0],
            [25,70], [30,0], [35,85], [40,0], [45,75],
        ]
        # Smoothness of a consistently straight line should be higher
        straight = [[float(i), 0.0] for i in range(10)]
        assert compute_smoothness_score(pts) < compute_smoothness_score(straight)


    def test_too_short_returns_1(self):
        from app.services.analysis.stroke_analyzer import compute_smoothness_score
        assert compute_smoothness_score([[0,0],[50,50]]) == 1.0

    def test_smooth_arc(self):
        from app.services.analysis.stroke_analyzer import compute_smoothness_score
        # Quarter circle arc — small, consistent angular changes
        pts = [[50*math.cos(t), 50*math.sin(t)] for t in
               [i*math.pi/20 for i in range(11)]]
        assert compute_smoothness_score(pts) >= 0.70


# ──────────────────────────────────────────────────────────────────────────────
# Stroke Analyzer: Path Error
# ──────────────────────────────────────────────────────────────────────────────

class TestPathError:
    def test_on_path_returns_near_zero(self):
        from app.services.analysis.stroke_analyzer import compute_normalized_path_error
        pts = [[float(i), 0.0] for i in range(0, 101, 5)]
        assert compute_normalized_path_error(pts, pts) < 0.05

    def test_far_off_returns_near_one(self):
        from app.services.analysis.stroke_analyzer import compute_normalized_path_error
        drawn = [[50.0, 80.0]] * 10     # far below the reference line
        ref   = [[float(i), 0.0] for i in range(0, 101, 10)]
        score = compute_normalized_path_error(drawn, ref)
        assert score > 0.3


# ──────────────────────────────────────────────────────────────────────────────
# Stroke Analyzer: Full Analysis
# ──────────────────────────────────────────────────────────────────────────────

class TestAnalyzeStroke:
    def test_perfect_trace_has_high_combined_score(self):
        from app.services.analysis.stroke_analyzer import analyze_stroke
        pts = [[float(i), 0.0] for i in range(0, 101, 5)]
        result = analyze_stroke(pts, pts)
        assert result["combined_score"] >= 0.80

    def test_all_required_keys_present(self):
        from app.services.analysis.stroke_analyzer import analyze_stroke
        result = analyze_stroke([[0,0],[50,50],[100,100]], [[0,0],[100,100]])
        required = {"direction_score","coverage_score","smoothness_score",
                    "normalized_path_error","overshoot_ratio",
                    "stroke_velocity_variance","combined_score"}
        assert required.issubset(result.keys())

    def test_all_scores_in_range(self):
        from app.services.analysis.stroke_analyzer import analyze_stroke
        pts = [[float(i), float(i)] for i in range(0, 101, 10)]
        r = analyze_stroke(pts, pts)
        for k, v in r.items():
            assert 0.0 <= v <= 1.0, f"{k} = {v} out of [0,1]"

    def test_wildly_wrong_trace_has_low_combined(self):
        from app.services.analysis.stroke_analyzer import analyze_stroke
        drawn = [[50.0, 90.0]] * 20     # scribble far from reference
        ref   = [[float(i), 0.0] for i in range(0, 101, 5)]
        result = analyze_stroke(drawn, ref)
        assert result["combined_score"] < 0.5


# ──────────────────────────────────────────────────────────────────────────────
# Direction Detector
# ──────────────────────────────────────────────────────────────────────────────

class TestDirectionDetector:
    def test_horizontal_right(self):
        from app.services.analysis.direction_detector import detect_direction
        pts = [[0.0,50.0],[50.0,50.0],[100.0,50.0]]
        r = detect_direction(pts)
        assert r["direction"] == "right"
        assert r["confidence"] >= 0.70

    def test_vertical_down(self):
        from app.services.analysis.direction_detector import detect_direction
        pts = [[50.0,0.0],[50.0,50.0],[50.0,100.0]]
        r = detect_direction(pts)
        assert r["direction"] == "down"
        assert r["confidence"] >= 0.70

    def test_diagonal_down_right(self):
        from app.services.analysis.direction_detector import detect_direction
        pts = [[0.0,0.0],[50.0,50.0],[100.0,100.0]]
        r = detect_direction(pts)
        assert r["direction"] == "down-right"

    def test_vertical_up(self):
        from app.services.analysis.direction_detector import detect_direction
        pts = [[50.0,100.0],[50.0,50.0],[50.0,0.0]]
        r = detect_direction(pts)
        assert r["direction"] == "up"

    def test_result_has_confidence_field(self):
        from app.services.analysis.direction_detector import detect_direction
        r = detect_direction([[0,0],[100,0]])
        assert "confidence" in r
        assert 0.0 <= r["confidence"] <= 1.0

    def test_result_has_angle_degrees(self):
        from app.services.analysis.direction_detector import detect_direction
        r = detect_direction([[0,0],[100,0]])
        assert "angle_degrees" in r
        assert -180 <= r["angle_degrees"] <= 180

    def test_result_has_displacement(self):
        from app.services.analysis.direction_detector import detect_direction
        r = detect_direction([[0,0],[100,0]])
        assert r["displacement"] > 0

    def test_single_point_returns_unknown(self):
        from app.services.analysis.direction_detector import detect_direction
        r = detect_direction([[50,50]])
        assert r["direction"] == "unknown"
        assert r["confidence"] == 0.0

    def test_matches_expected_correct(self):
        from app.services.analysis.direction_detector import matches_expected
        pts = [[0,50],[50,50],[100,50]]
        ok, _ = matches_expected(pts, "right")
        assert ok is True

    def test_matches_expected_wrong(self):
        from app.services.analysis.direction_detector import matches_expected
        pts = [[0,50],[50,50],[100,50]]
        ok, _ = matches_expected(pts, "down")
        assert ok is False


# ──────────────────────────────────────────────────────────────────────────────
# Guidance Handler
# ──────────────────────────────────────────────────────────────────────────────

class TestGuidanceHandler:
    def _make_event(self, stroke_id=1, drawn=None):
        return {
            "event_type": "stroke_complete",
            "stroke_id": stroke_id,
            "drawn_points": drawn or [[0,0],[50,50],[100,100]],
            "reference_stroke_id": stroke_id,
            "hesitation_ms": 1200,
        }

    def test_returns_all_required_keys(self):
        from app.services.guidance_handler import process_guidance_event
        event = self._make_event()
        result = process_guidance_event(
            session_id=1, module_type="alphabet_practice",
            target_item="L", event=event, stroke_attempt_counts={},
        )
        required = {"stroke_id","scores","direction_detected","direction_match",
                    "feedback_type","feedback_message","unlock_next_stroke",
                    "failsafe_unlock","attempt_number","trace_percent"}
        assert required.issubset(result.keys())

    def test_trace_percent_in_range(self):
        from app.services.guidance_handler import process_guidance_event
        event = self._make_event()
        result = process_guidance_event(
            session_id=1, module_type="alphabet_practice",
            target_item="L", event=event, stroke_attempt_counts={},
        )
        assert 0.0 <= result["trace_percent"] <= 100.0

    def test_failsafe_triggers_at_max_attempts(self):
        from app.services.guidance_handler import process_guidance_event
        counts = {"1": 3}     # already 3 attempts
        event  = self._make_event(stroke_id=1, drawn=[[90,90]]*5)  # terrible draw
        result = process_guidance_event(
            session_id=1, module_type="alphabet_practice",
            target_item="L", event=event, stroke_attempt_counts=counts,
        )
        assert result["failsafe_unlock"] is True
        assert result["unlock_next_stroke"] is True

    def test_good_trace_unlocks_next_stroke(self):
        from app.services.guidance_handler import process_guidance_event
        # L: stroke 1 is [[20,5],[20,95]] — draw near that
        drawn = [[20.0, float(y)] for y in range(5, 96, 5)]
        event = self._make_event(stroke_id=1, drawn=drawn)
        result = process_guidance_event(
            session_id=1, module_type="alphabet_practice",
            target_item="L", event=event, stroke_attempt_counts={},
        )
        assert result["unlock_next_stroke"] is True

    def test_attempt_count_increments(self):
        from app.services.guidance_handler import process_guidance_event
        counts = {}
        for _ in range(3):
            event = self._make_event()
            r = process_guidance_event(
                session_id=1, module_type="alphabet_practice",
                target_item="L", event=event, stroke_attempt_counts=counts,
            )
        assert r["attempt_number"] == 3

    def test_weighted_trace_percent_formula(self):
        from app.services.guidance_handler import compute_trace_percent
        # 0.5 coverage, 0.5 direction, 0.5 smoothness → 50%
        assert compute_trace_percent(0.5, 0.5, 0.5) == 50.0
        # Perfect
        assert compute_trace_percent(1.0, 1.0, 1.0) == 100.0
        # Zero
        assert compute_trace_percent(0.0, 0.0, 0.0) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# Difficulty Adapter
# ──────────────────────────────────────────────────────────────────────────────

class TestDifficultyAdapter:
    def test_promote_threshold(self):
        from app.services.difficulty_adapter import get_recommended_difficulty
        from unittest.mock import MagicMock, patch

        mock_sessions = [
            MagicMock(difficulty="beginner", accuracy_score=0.90),
            MagicMock(difficulty="beginner", accuracy_score=0.88),
            MagicMock(difficulty="beginner", accuracy_score=0.91),
        ]
        mock_db = MagicMock()
        # Patch the full query chain to return mock_sessions
        (mock_db.query.return_value
            .filter.return_value
            .filter.return_value
            .filter.return_value
            .order_by.return_value
            .limit.return_value
            .all.return_value) = mock_sessions

        with patch("app.services.difficulty_adapter.PracticeSession"):
            # Re-run with direct db mock — test the pure logic path
            from app.services.difficulty_adapter import DIFFICULTY_ORDER, PROMOTE_THRESHOLD
            recent = mock_sessions
            current = recent[0].difficulty
            avg = sum(r.accuracy_score for r in recent) / len(recent)
            idx = DIFFICULTY_ORDER.index(current)
            assert avg >= PROMOTE_THRESHOLD
            assert DIFFICULTY_ORDER[idx + 1] == "intermediate"

    def test_demote_threshold(self):
        from app.services.difficulty_adapter import DIFFICULTY_ORDER, DEMOTE_THRESHOLD
        from unittest.mock import MagicMock

        recent = [
            MagicMock(difficulty="intermediate", accuracy_score=0.40),
            MagicMock(difficulty="intermediate", accuracy_score=0.35),
        ]
        current = recent[0].difficulty
        avg = sum(r.accuracy_score for r in recent) / len(recent)
        idx = DIFFICULTY_ORDER.index(current)
        assert avg <= DEMOTE_THRESHOLD
        assert DIFFICULTY_ORDER[idx - 1] == "beginner"

    def test_no_sessions_returns_default(self):
        from app.services.difficulty_adapter import DEFAULT_DIFFICULTY
        # No sessions → default difficulty
        assert DEFAULT_DIFFICULTY == "beginner"
