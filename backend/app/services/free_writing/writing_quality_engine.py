"""
app/services/free_writing/writing_quality_engine.py

Master orchestrator. Combines motor + spatial metrics into a unified
WritingQualityReport. Includes emotional state snapshot (Addition 2).
"""

from typing import TypedDict, Literal
from app.services.free_writing.motor_quality_analyzer import analyze_motor_quality, MotorQualityMetrics
from app.services.free_writing.spatial_quality_analyzer import analyze_spatial_quality, SpatialQualityMetrics
from app.services.free_writing.quality_feedback_generator import (
    generate_feedback, derive_quality_band
)

QualityBand = Literal["developing", "building", "strong", "exceptional"]


class EmotionalStateSnapshot(TypedDict):
    """Addition 2 — captured at session completion."""
    frustration_index:    float   # 0-1 (from hesitation + velocity variance)
    confidence_level:     float   # 0-1 (from stroke confidence + smoothness)
    fatigue_estimate:     float   # 0-1 (quality drop in last 3rd of session)
    focus_score:          float   # 0-1 (consistency of stroke length/spacing)


class WritingQualityReport(TypedDict):
    """Full quality report returned from /studio/{id}/complete."""
    session_id:              str
    motor:                   MotorQualityMetrics
    spatial:                 SpatialQualityMetrics
    overall_quality_score:   float
    quality_band:            QualityBand
    primary_strength:        str
    primary_focus_area:      str
    emotional_snapshot:      EmotionalStateSnapshot
    feedback_messages:       list[str]


# ── Weights ───────────────────────────────────────────────────────────────────
QUALITY_WEIGHTS = {
    "smoothness":         0.30,
    "velocity_stability": 0.15,   # 1 - velocity_variance
    "stroke_confidence":  0.15,
    "baseline":           0.20,
    "spacing":            0.15,
    "canvas_use":         0.05,
}


def _compute_emotional_snapshot(
    motor: MotorQualityMetrics,
    strokes: list[dict],
    canvas_height: float,
) -> EmotionalStateSnapshot:
    """
    Derives emotional state at session end.
    Frustration = hesitation + erratic velocity.
    Confidence = stroke_confidence + smoothness.
    Fatigue = quality drop in final third of session.
    """
    frustration = round(
        0.6 * motor["hesitation_ratio"] + 0.4 * motor["velocity_variance"], 4
    )
    confidence = round(
        0.5 * motor["stroke_confidence"] + 0.5 * motor["smoothness_score"], 4
    )

    # Fatigue: compare smoothness of first vs last third of strokes
    n = len(strokes)
    fatigue = 0.0
    if n >= 6:
        from app.services.analysis.stroke_analyzer import compute_smoothness_score
        first_third = strokes[:n // 3]
        last_third  = strokes[-(n // 3):]

        def avg_smooth(s_list):
            scores = [compute_smoothness_score(s.get("points", [])) for s in s_list
                      if len(s.get("points", [])) >= 3]
            return sum(scores) / len(scores) if scores else 0.5

        first_smooth = avg_smooth(first_third)
        last_smooth  = avg_smooth(last_third)
        drop = first_smooth - last_smooth
        fatigue = round(min(1.0, max(0.0, drop * 2.0)), 4)  # 50% drop = 1.0 fatigue

    # Focus: consistency of stroke count per cluster (placeholder — spatial proxy)
    focus = round(1.0 - motor["velocity_variance"] * 0.5, 4)

    return EmotionalStateSnapshot(
        frustration_index=frustration,
        confidence_level=confidence,
        fatigue_estimate=fatigue,
        focus_score=focus,
    )


def _derive_strengths(motor: MotorQualityMetrics, spatial: SpatialQualityMetrics) -> tuple[str, str]:
    """Returns (primary_strength_key, primary_focus_area_key)."""
    all_scores = {
        "smoothness":  motor["smoothness_score"],
        "confidence":  motor["stroke_confidence"],
        "spacing":     spatial["spacing_regularity"],
        "baseline":    spatial["baseline_consistency"],
    }
    sorted_keys = sorted(all_scores, key=lambda k: all_scores[k], reverse=True)
    strength = sorted_keys[0]
    focus = sorted_keys[-1]
    return strength, focus


def normalize_strokes(strokes: list[dict]) -> list[dict]:
    """
    Normalizes strokes from frontend format where points are dicts:
      [{"x": ..., "y": ..., "t": ...}, ...]
    to backend format where points are lists:
      [[x, y, t], ...]
    """
    normalized = []
    for s in strokes:
        pts = s.get("points", []) or []
        norm_pts = []
        for p in pts:
            if isinstance(p, dict):
                x = p.get("x", 0.0)
                y = p.get("y", 0.0)
                t = p.get("t")
                if t is not None:
                    norm_pts.append([x, y, t])
                else:
                    norm_pts.append([x, y])
            elif isinstance(p, (list, tuple)):
                norm_pts.append(list(p))
            else:
                norm_pts.append(p)
        
        normalized_stroke = {
            "points": norm_pts,
        }
        if "startTime" in s:
            normalized_stroke["startTime"] = s["startTime"]
        if "start_time" in s:
            normalized_stroke["start_time"] = s["start_time"]
        normalized.append(normalized_stroke)
    return normalized


# ── Main engine ───────────────────────────────────────────────────────────────

def generate_quality_report(
    session_id: str,
    strokes: list[dict],
    canvas_width: float = 400.0,
    canvas_height: float = 400.0,
    profile_type: str = "child",
    is_improving: bool = False,
    streak_days: int = 0,
) -> WritingQualityReport:
    """
    Full pipeline: strokes → motor analysis → spatial analysis → report.

    Args:
        session_id:    UUID of the FreeWritingSession
        strokes:       Raw stroke list from canvas
        canvas_width:  Canvas dimensions for normalization
        canvas_height:
        profile_type:  "early_learner" | "child" | "adult"
        is_improving:  From WritingProgressTracker (trend)
        streak_days:   Current session streak for encouragement

    Returns:
        WritingQualityReport dict
    """
    strokes = normalize_strokes(strokes)
    motor   = analyze_motor_quality(strokes)
    spatial = analyze_spatial_quality(strokes, canvas_width, canvas_height)

    # Composite quality score
    overall = (
        QUALITY_WEIGHTS["smoothness"]         * motor["smoothness_score"] +
        QUALITY_WEIGHTS["velocity_stability"] * (1.0 - motor["velocity_variance"]) +
        QUALITY_WEIGHTS["stroke_confidence"]  * motor["stroke_confidence"] +
        QUALITY_WEIGHTS["baseline"]           * spatial["baseline_consistency"] +
        QUALITY_WEIGHTS["spacing"]            * spatial["spacing_regularity"] +
        QUALITY_WEIGHTS["canvas_use"]         * spatial["canvas_utilization"]
    )
    overall = round(min(1.0, overall), 4)

    quality_band = derive_quality_band(overall)
    strength, focus = _derive_strengths(motor, spatial)
    emotional = _compute_emotional_snapshot(motor, strokes, canvas_height)

    feedback = generate_feedback(
        motor=motor,
        spatial=spatial,
        quality_band=quality_band,
        profile_type=profile_type,  # type: ignore
        is_improving=is_improving,
        streak_days=streak_days,
    )

    return WritingQualityReport(
        session_id=session_id,
        motor=motor,
        spatial=spatial,
        overall_quality_score=overall,
        quality_band=quality_band,
        primary_strength=strength,
        primary_focus_area=focus,
        emotional_snapshot=emotional,
        feedback_messages=feedback,
    )
