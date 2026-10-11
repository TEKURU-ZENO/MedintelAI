"""
app/services/free_writing/motor_quality_analyzer.py

Analyzes raw stroke telemetry for motor quality signals.
Reuses core algorithms from stroke_analyzer.py — NO duplication.

Returns MotorQualityMetrics TypedDict.
"""

import math
from typing import TypedDict

# Reuse the proven smoothness + velocity algorithms
from app.services.analysis.stroke_analyzer import (
    compute_smoothness_score,
    compute_velocity_variance,
)


class MotorQualityMetrics(TypedDict):
    smoothness_score:     float   # 0-1: 1 = perfectly smooth strokes
    velocity_variance:    float   # 0-1: 0 = steady, 1 = erratic
    hesitation_ratio:     float   # 0-1: proportion of strokes with long pre-stroke pauses
    stroke_confidence:    float   # 0-1: inverse of tremor/micro-jitter
    avg_stroke_length:    float   # average arc length in canvas units
    stroke_count:         int


# ── Constants ─────────────────────────────────────────────────────────────────
HESITATION_THRESHOLD_MS = 800   # pause > 800ms before a stroke = hesitation
JITTER_WINDOW = 5               # points to sample for micro-jitter detection


# ── Helpers ───────────────────────────────────────────────────────────────────

def _arc_length(points: list) -> float:
    """Total arc length of a stroke's point array."""
    total = 0.0
    for i in range(1, len(points)):
        dx = points[i][0] - points[i-1][0]
        dy = points[i][1] - points[i-1][1]
        total += math.sqrt(dx*dx + dy*dy)
    return total


def _detect_hesitation(strokes: list[dict]) -> float:
    """
    Returns the proportion of strokes where the pause before drawing
    exceeded HESITATION_THRESHOLD_MS.
    Requires stroke timestamps (stroke['start_time'] or points[0][2]).
    Falls back to 0.0 if no timestamp data available.
    """
    if len(strokes) < 2:
        return 0.0

    hesitations = 0
    total_gaps = 0

    for i in range(1, len(strokes)):
        prev = strokes[i-1]
        curr = strokes[i]

        # Try to get timestamps from start_time fields or last/first point [2]
        prev_end_t = None
        curr_start_t = None

        try:
            prev_pts = prev.get("points", [])
            curr_pts = curr.get("points", [])
            if prev_pts and len(prev_pts[-1]) >= 3:
                prev_end_t = prev_pts[-1][2]
            if curr_pts and len(curr_pts[0]) >= 3:
                curr_start_t = curr_pts[0][2]
        except (IndexError, TypeError):
            pass

        if prev_end_t is not None and curr_start_t is not None:
            gap_ms = curr_start_t - prev_end_t
            total_gaps += 1
            if gap_ms > HESITATION_THRESHOLD_MS:
                hesitations += 1

    if total_gaps == 0:
        return 0.0

    return round(hesitations / total_gaps, 4)


def _compute_stroke_confidence(strokes: list[dict]) -> float:
    """
    Confidence = 1 - average micro-jitter across all strokes.
    Micro-jitter: short-window direction reversal rate.
    High confidence = strokes flow without sudden direction reversals.
    """
    if not strokes:
        return 1.0

    jitter_scores = []
    for stroke in strokes:
        pts = stroke.get("points", [])
        if len(pts) < JITTER_WINDOW + 1:
            jitter_scores.append(1.0)
            continue

        reversals = 0
        checks = 0
        for i in range(1, len(pts) - JITTER_WINDOW):
            dx1 = pts[i][0] - pts[i-1][0]
            dy1 = pts[i][1] - pts[i-1][1]
            dx2 = pts[i+JITTER_WINDOW][0] - pts[i][0]
            dy2 = pts[i+JITTER_WINDOW][1] - pts[i][1]
            dot = dx1*dx2 + dy1*dy2
            checks += 1
            if dot < 0:  # direction reversal
                reversals += 1

        reversal_rate = reversals / checks if checks > 0 else 0
        jitter_scores.append(1.0 - reversal_rate)

    return round(sum(jitter_scores) / len(jitter_scores), 4)


# ── Main analyzer ─────────────────────────────────────────────────────────────

def analyze_motor_quality(strokes: list[dict]) -> MotorQualityMetrics:
    """
    Args:
        strokes: List of stroke dicts with 'points' key.
                 Each point is [x, y] or [x, y, timestamp_ms].

    Returns:
        MotorQualityMetrics with all scores in [0, 1].
    """
    if not strokes:
        return MotorQualityMetrics(
            smoothness_score=0.0,
            velocity_variance=0.0,
            hesitation_ratio=0.0,
            stroke_confidence=0.0,
            avg_stroke_length=0.0,
            stroke_count=0,
        )

    all_points_flat = []
    arc_lengths = []

    for stroke in strokes:
        pts = stroke.get("points", [])
        if len(pts) >= 2:
            all_points_flat.extend(pts)
            arc_lengths.append(_arc_length(pts))

    # Smoothness: average across all strokes individually
    smooth_scores = []
    for stroke in strokes:
        pts = stroke.get("points", [])
        if len(pts) >= 3:
            smooth_scores.append(compute_smoothness_score(pts))
    smoothness = round(sum(smooth_scores) / len(smooth_scores), 4) if smooth_scores else 1.0

    # Velocity variance: on the full flattened stroke sequence
    velocity_var = compute_velocity_variance(all_points_flat) if len(all_points_flat) >= 3 else 0.0

    hesitation = _detect_hesitation(strokes)
    confidence = _compute_stroke_confidence(strokes)
    avg_len = round(sum(arc_lengths) / len(arc_lengths), 2) if arc_lengths else 0.0

    return MotorQualityMetrics(
        smoothness_score=smoothness,
        velocity_variance=velocity_var,
        hesitation_ratio=hesitation,
        stroke_confidence=confidence,
        avg_stroke_length=avg_len,
        stroke_count=len(strokes),
    )
