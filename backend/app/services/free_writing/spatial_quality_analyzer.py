"""
app/services/free_writing/spatial_quality_analyzer.py

Analyzes the spatial layout of free-form strokes on the canvas.
No reference path needed — this is purely about layout intelligence.

Returns SpatialQualityMetrics TypedDict.
"""

import math
import statistics
from typing import TypedDict


class SpatialQualityMetrics(TypedDict):
    baseline_consistency:   float   # 0-1: how aligned strokes are horizontally
    slant_consistency:      float   # 0-1: how consistent the writing angle is
    spacing_regularity:     float   # 0-1: how even horizontal gaps between clusters are
    canvas_utilization:     float   # 0-1: fraction of canvas actively used
    vertical_compression:   float   # 0-1: ratio of used height to canvas height


# ── Constants ─────────────────────────────────────────────────────────────────
CLUSTER_GAP_THRESHOLD = 0.08     # fraction of canvas width → clusters words
MIN_STROKE_POINTS = 3


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stroke_bounds(pts: list) -> dict | None:
    """Bounding box of a stroke: {x_min, y_min, x_max, y_max}."""
    if len(pts) < 2:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return {"x_min": min(xs), "y_min": min(ys), "x_max": max(xs), "y_max": max(ys)}


def _dominant_angle(pts: list) -> float | None:
    """Dominant direction angle of a stroke in degrees [-90, 90]."""
    if len(pts) < 2:
        return None
    dx = pts[-1][0] - pts[0][0]
    dy = pts[-1][1] - pts[0][1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    return math.degrees(math.atan2(dy, dx))


def _cluster_strokes(bounds_list: list[dict], canvas_width: float) -> list[list[dict]]:
    """
    Groups strokes into horizontal clusters (approximate 'words').
    Gap threshold = CLUSTER_GAP_THRESHOLD * canvas_width.
    """
    if not bounds_list:
        return []

    sorted_bounds = sorted(bounds_list, key=lambda b: b["x_min"])
    gap = CLUSTER_GAP_THRESHOLD * canvas_width
    clusters: list[list[dict]] = [[sorted_bounds[0]]]

    for b in sorted_bounds[1:]:
        last_cluster = clusters[-1]
        last_x_max = max(s["x_max"] for s in last_cluster)
        if b["x_min"] - last_x_max > gap:
            clusters.append([b])
        else:
            last_cluster.append(b)

    return clusters


def _variance_normalized(values: list[float]) -> float:
    """1 - normalized standard deviation. 1 = perfectly consistent.
    Normalizes std by the value range (max - min), not the mean,
    so large absolute spreads correctly reduce consistency even when mean is large.
    """
    if len(values) < 2:
        return 1.0
    value_range = max(values) - min(values)
    if value_range < 1e-9:
        return 1.0  # all identical → perfectly consistent
    std = statistics.stdev(values)
    # normalized_std in [0, 1]: full-range std → 0.0 consistency
    normalized_std = min(1.0, std / value_range)
    return round(1.0 - normalized_std, 4)


# ── Main analyzer ─────────────────────────────────────────────────────────────

def analyze_spatial_quality(
    strokes: list[dict],
    canvas_width: float = 400.0,
    canvas_height: float = 400.0,
) -> SpatialQualityMetrics:
    """
    Args:
        strokes:       List of stroke dicts with 'points' key.
        canvas_width:  Canvas pixel width (for normalization).
        canvas_height: Canvas pixel height (for normalization).

    Returns:
        SpatialQualityMetrics with all scores in [0, 1].
    """
    default = SpatialQualityMetrics(
        baseline_consistency=1.0,
        slant_consistency=1.0,
        spacing_regularity=1.0,
        canvas_utilization=0.0,
        vertical_compression=0.0,
    )

    valid_strokes = [s for s in strokes if len(s.get("points", [])) >= MIN_STROKE_POINTS]
    if not valid_strokes:
        return default

    bounds_list = [b for s in valid_strokes if (b := _stroke_bounds(s["points"]))]

    if not bounds_list:
        return default

    # ── Baseline Consistency ────────────────────────────────────────────────
    # Measure variance of each stroke's y_max (bottom of stroke = "baseline" position)
    y_bottoms = [b["y_max"] for b in bounds_list]
    baseline_consistency = _variance_normalized(y_bottoms)

    # ── Slant Consistency ───────────────────────────────────────────────────
    angles = [a for s in valid_strokes if (a := _dominant_angle(s["points"])) is not None]
    slant_consistency = _variance_normalized(angles) if len(angles) >= 2 else 1.0

    # ── Spacing Regularity ──────────────────────────────────────────────────
    clusters = _cluster_strokes(bounds_list, canvas_width)
    if len(clusters) >= 2:
        cluster_centers = [
            sum(b["x_min"] + b["x_max"] for b in c) / (2 * len(c))
            for c in clusters
        ]
        gaps = [cluster_centers[i+1] - cluster_centers[i] for i in range(len(cluster_centers)-1)]
        spacing_regularity = _variance_normalized(gaps) if len(gaps) >= 2 else 1.0
    else:
        spacing_regularity = 1.0  # single cluster: trivially regular

    # ── Canvas Utilization ──────────────────────────────────────────────────
    all_x = [p[0] for s in valid_strokes for p in s["points"]]
    all_y = [p[1] for s in valid_strokes for p in s["points"]]
    used_width  = (max(all_x) - min(all_x)) / max(canvas_width,  1.0)
    used_height = (max(all_y) - min(all_y)) / max(canvas_height, 1.0)
    canvas_utilization = round(min(1.0, (used_width * used_height) ** 0.5), 4)

    # ── Vertical Compression ─────────────────────────────────────────────────
    vertical_compression = round(min(1.0, used_height), 4)

    return SpatialQualityMetrics(
        baseline_consistency=baseline_consistency,
        slant_consistency=slant_consistency,
        spacing_regularity=spacing_regularity,
        canvas_utilization=canvas_utilization,
        vertical_compression=vertical_compression,
    )
