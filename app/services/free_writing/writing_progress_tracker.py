"""
app/services/free_writing/writing_progress_tracker.py

Computes trend data across multiple FreeWritingSession records.
Used to answer: "Is this learner improving over time?"
"""

from typing import TypedDict, Literal
from datetime import datetime


class WritingProgressTrend(TypedDict):
    smoothness_trend:       Literal["improving", "stable", "declining"]
    spacing_trend:          Literal["improving", "stable", "declining"]
    confidence_trend:       Literal["improving", "stable", "declining"]
    consistency_growth:     float   # % change in overall_score over analyzed sessions
    fatigue_pattern:        bool    # True if quality drops >20% in last third of sessions
    sessions_analyzed:      int
    best_session_score:     float
    best_session_date:      str | None
    is_improving:           bool    # convenience flag for other systems


TREND_WINDOW = 7       # sessions to analyze
IMPROVEMENT_DELTA = 0.05   # >5% change = improving/declining


def _linear_trend(values: list[float]) -> Literal["improving", "stable", "declining"]:
    """Simple linear trend via first-vs-last half comparison."""
    if len(values) < 3:
        return "stable"
    mid = len(values) // 2
    first_avg = sum(values[:mid]) / mid
    second_avg = sum(values[mid:]) / (len(values) - mid)
    delta = second_avg - first_avg
    if delta > IMPROVEMENT_DELTA:
        return "improving"
    elif delta < -IMPROVEMENT_DELTA:
        return "declining"
    return "stable"


def compute_progress_trend(sessions: list[dict]) -> WritingProgressTrend:
    """
    Args:
        sessions: List of FreeWritingSession records as dicts, ordered oldest→newest.
                  Each must have: overall_score, quality_metrics (JSONB), completed_at.

    Returns:
        WritingProgressTrend
    """
    if not sessions:
        return WritingProgressTrend(
            smoothness_trend="stable",
            spacing_trend="stable",
            confidence_trend="stable",
            consistency_growth=0.0,
            fatigue_pattern=False,
            sessions_analyzed=0,
            best_session_score=0.0,
            best_session_date=None,
            is_improving=False,
        )

    recent = sessions[-TREND_WINDOW:]

    # Extract time-series metrics
    overall_scores = [s.get("overall_score") or 0.0 for s in recent]

    smoothness_vals, spacing_vals, confidence_vals = [], [], []
    for s in recent:
        qm = s.get("quality_metrics") or {}
        motor   = qm.get("motor", {})
        spatial = qm.get("spatial", {})
        smoothness_vals.append(motor.get("smoothness_score", 0.5))
        spacing_vals.append(spatial.get("spacing_regularity", 0.5))
        confidence_vals.append(motor.get("stroke_confidence", 0.5))

    # Trends
    smoothness_trend  = _linear_trend(smoothness_vals)
    spacing_trend     = _linear_trend(spacing_vals)
    confidence_trend  = _linear_trend(confidence_vals)

    # Consistency growth (% change from first to last session)
    if len(overall_scores) >= 2 and overall_scores[0] > 0:
        growth = (overall_scores[-1] - overall_scores[0]) / overall_scores[0]
        consistency_growth = round(growth * 100, 1)
    else:
        consistency_growth = 0.0

    # Fatigue pattern: do sessions tend to drop in the second half?
    fatigue_pattern = False
    if len(recent) >= 4:
        mid = len(recent) // 2
        first_avg = sum(overall_scores[:mid]) / mid
        second_avg = sum(overall_scores[mid:]) / (len(overall_scores) - mid)
        fatigue_pattern = (first_avg - second_avg) > 0.15

    # Best session
    best_score = max(overall_scores)
    best_idx = overall_scores.index(best_score)
    best_session = recent[best_idx]
    best_date_raw = best_session.get("completed_at")
    if isinstance(best_date_raw, datetime):
        best_date = best_date_raw.strftime("%B %d, %Y")
    elif isinstance(best_date_raw, str):
        best_date = best_date_raw[:10]
    else:
        best_date = None

    is_improving = (smoothness_trend == "improving" or spacing_trend == "improving") and \
                   confidence_trend != "declining"

    return WritingProgressTrend(
        smoothness_trend=smoothness_trend,
        spacing_trend=spacing_trend,
        confidence_trend=confidence_trend,
        consistency_growth=consistency_growth,
        fatigue_pattern=fatigue_pattern,
        sessions_analyzed=len(recent),
        best_session_score=round(best_score, 4),
        best_session_date=best_date,
        is_improving=is_improving,
    )
