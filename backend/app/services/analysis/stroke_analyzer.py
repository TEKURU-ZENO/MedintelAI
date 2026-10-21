"""
app/services/analysis/stroke_analyzer.py — Geometric Stroke Analysis Engine

Compares a drawn stroke against a reference path and returns a full set
of normalized metrics. These metrics are:
  - Used immediately for authoritative scoring (Phase 3)
  - Stored in PracticeSession.detailed_scores (Phase 4 analytics)
  - Future ML feature vectors (Phase 11 personalization)

All functions are pure — no DB, no I/O. Fast to unit-test.

Coordinate system: all points are in [0, 100] space (the reference grid).
The canvas normalizes drawn points before sending to the backend.

Metrics returned:
  direction_score        — cosine similarity of stroke direction vectors [0,1]
  coverage_score         — % of reference path covered within tolerance [0,1]
  smoothness_score       — consistency of angular changes (1=smooth, 0=jerky) [0,1]
  normalized_path_error  — avg perpendicular distance to reference, normalized [0,1]
  overshoot_ratio        — fraction of drawn points past the reference endpoints [0,1]
  stroke_velocity_variance — variance in inter-point speed (lower = steadier) [0,1]
  combined_score         — weighted composite for final accuracy [0,1]
"""

import math
from typing import TypedDict


# ── Types ─────────────────────────────────────────────────────────────────────

Point = list[float]   # [x, y]  (optionally [x, y, t] with timestamp)

class StrokeMetrics(TypedDict):
    direction_score:         float
    coverage_score:          float
    smoothness_score:        float
    normalized_path_error:   float
    overshoot_ratio:         float
    stroke_velocity_variance: float
    combined_score:          float


# ── Weights for combined_score ─────────────────────────────────────────────────
WEIGHTS = {
    "direction":  0.30,
    "coverage":   0.35,
    "smoothness": 0.20,
    "path_error": 0.15,   # penalizes deviation from reference line
}


# ──────────────────────────────────────────────────────────────────────────────
# Vector utilities
# ──────────────────────────────────────────────────────────────────────────────

def _vec(a: Point, b: Point) -> tuple[float, float]:
    return (b[0] - a[0], b[1] - a[1])


def _magnitude(v: tuple[float, float]) -> float:
    return math.sqrt(v[0] ** 2 + v[1] ** 2)


def _dot(a: tuple[float, float], b: tuple[float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1]


def _cosine_similarity(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Cosine similarity in [0, 1]. Returns 0.5 if either vector is zero."""
    mag_a = _magnitude(a)
    mag_b = _magnitude(b)
    if mag_a < 1e-9 or mag_b < 1e-9:
        return 0.5
    cos = _dot(a, b) / (mag_a * mag_b)
    # Map [-1, 1] → [0, 1]
    return (cos + 1.0) / 2.0


def _resample(points: list[Point], n: int) -> list[Point]:
    """Resample a polyline to exactly n evenly-spaced points."""
    if len(points) < 2:
        return [points[0]] * n if points else [[0, 0]] * n

    # Build cumulative arc lengths
    dists = [0.0]
    for i in range(1, len(points)):
        d = math.dist(points[i - 1][:2], points[i][:2])
        dists.append(dists[-1] + d)
    total = dists[-1]

    if total < 1e-9:
        return [points[0][:2]] * n

    step = total / (n - 1)
    result: list[Point] = []
    j = 0
    for i in range(n):
        target = i * step
        while j < len(dists) - 1 and dists[j + 1] < target:
            j += 1
        if j >= len(points) - 1:
            result.append(list(points[-1][:2]))
        else:
            seg = dists[j + 1] - dists[j]
            t = (target - dists[j]) / seg if seg > 1e-9 else 0.0
            x = points[j][0] + t * (points[j + 1][0] - points[j][0])
            y = points[j][1] + t * (points[j + 1][1] - points[j][1])
            result.append([x, y])
    return result


def _perpendicular_distance(p: Point, a: Point, b: Point) -> float:
    """Perpendicular distance from point p to line segment a→b."""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq < 1e-9:
        return math.dist(p[:2], a[:2])
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / seg_len_sq))
    proj = [a[0] + t * dx, a[1] + t * dy]
    return math.dist(p[:2], proj)


# ──────────────────────────────────────────────────────────────────────────────
# Individual metric computations
# ──────────────────────────────────────────────────────────────────────────────

def compute_direction_score(drawn: list[Point], reference: list[Point]) -> float:
    """
    Cosine similarity between the overall drawn direction and reference direction.
    Uses the net displacement vector (start → end) for both.
    For multi-segment references, also computes segment-level similarity and averages.
    """
    if len(drawn) < 2 or len(reference) < 2:
        return 0.5

    # Overall direction
    drawn_dir = _vec(drawn[0], drawn[-1])
    ref_dir   = _vec(reference[0], reference[-1])
    overall   = _cosine_similarity(drawn_dir, ref_dir)

    # Segment-level: sample N segments from each, compare pairwise
    n_segs = min(8, len(drawn) - 1, len(reference) - 1)
    if n_segs < 2:
        return overall

    d_resampled = _resample(drawn, n_segs + 1)
    r_resampled = _resample(reference, n_segs + 1)

    seg_sims = []
    for i in range(n_segs):
        d_seg = _vec(d_resampled[i], d_resampled[i + 1])
        r_seg = _vec(r_resampled[i], r_resampled[i + 1])
        seg_sims.append(_cosine_similarity(d_seg, r_seg))

    segment_avg = sum(seg_sims) / len(seg_sims)
    # Weight: 60% overall direction, 40% segment agreement
    return round(0.6 * overall + 0.4 * segment_avg, 4)


def compute_coverage_score(
    drawn: list[Point],
    reference: list[Point],
    tolerance: float = 8.0,  # in reference-space units (0–100 grid)
) -> float:
    """
    Fraction of reference path points within `tolerance` of any drawn point.
    Tolerance of 8 units in a 0–100 grid ≈ 8% of the letter width.
    """
    if not drawn or not reference:
        return 0.0

    n_samples = max(20, len(reference))
    ref_sampled = _resample(reference, n_samples)

    covered = 0
    for ref_pt in ref_sampled:
        for d_pt in drawn:
            if math.dist(ref_pt, d_pt[:2]) <= tolerance:
                covered += 1
                break
    return round(covered / n_samples, 4)


def compute_smoothness_score(drawn: list[Point]) -> float:
    """
    Measures consistency of direction changes in the drawn stroke.
    Computed as 1 - (std_dev of angular velocity / π).
    A perfectly smooth arc → score ≈ 1.0. A jagged line → score closer to 0.
    """
    if len(drawn) < 3:
        return 1.0  # too short to measure jerkiness

    angles = []
    for i in range(1, len(drawn) - 1):
        v1 = _vec(drawn[i - 1], drawn[i])
        v2 = _vec(drawn[i], drawn[i + 1])
        m1, m2 = _magnitude(v1), _magnitude(v2)
        if m1 < 1e-9 or m2 < 1e-9:
            continue
        cos_a = max(-1.0, min(1.0, _dot(v1, v2) / (m1 * m2)))
        angles.append(math.acos(cos_a))

    if not angles:
        return 1.0

    mean   = sum(angles) / len(angles)
    variance = sum((a - mean) ** 2 for a in angles) / len(angles)
    std_dev  = math.sqrt(variance)
    # Normalize: std_dev of π means maximally jerky
    return round(max(0.0, 1.0 - std_dev / math.pi), 4)


def compute_normalized_path_error(drawn: list[Point], reference: list[Point]) -> float:
    """
    Average perpendicular distance from drawn points to the reference polyline,
    normalized by the bounding-box diagonal of the reference (so letter size doesn't matter).
    Returns 0 = perfect alignment, 1 = very far off.
    """
    if not drawn or len(reference) < 2:
        return 1.0

    # Reference bounding box diagonal for normalization
    xs = [p[0] for p in reference]
    ys = [p[1] for p in reference]
    diag = math.dist([min(xs), min(ys)], [max(xs), max(ys)])
    if diag < 1e-9:
        diag = 10.0  # fallback

    # For each drawn point, find closest perpendicular dist to any ref segment
    total_dist = 0.0
    for pt in drawn:
        min_dist = float("inf")
        for i in range(len(reference) - 1):
            d = _perpendicular_distance(pt, reference[i], reference[i + 1])
            min_dist = min(min_dist, d)
        total_dist += min_dist

    avg_dist = total_dist / len(drawn)
    normalized = avg_dist / diag
    return round(min(1.0, normalized), 4)


def compute_overshoot_ratio(drawn: list[Point], reference: list[Point]) -> float:
    """
    Fraction of drawn points that lie beyond the reference endpoints.
    High overshoot → user is drawing past the endpoint of the stroke.
    """
    if not drawn or len(reference) < 2:
        return 0.0

    ref_start = reference[0]
    ref_end   = reference[-1]
    ref_dir   = _vec(ref_start, ref_end)
    ref_len   = _magnitude(ref_dir)

    if ref_len < 1e-9:
        return 0.0

    overshoot_count = 0
    for pt in drawn:
        # Project pt onto ref direction
        to_pt = _vec(ref_start, pt)
        proj  = _dot(to_pt, ref_dir) / (ref_len * ref_len)
        # proj < 0 means before start, proj > 1 means past end
        if proj < -0.05 or proj > 1.05:  # 5% tolerance
            overshoot_count += 1

    return round(overshoot_count / len(drawn), 4)


def compute_velocity_variance(drawn: list[Point]) -> float:
    """
    Variance in inter-point speed (using timestamps if available).
    Returns a [0, 1] normalized value: 0 = steady, 1 = very erratic.
    Requires drawn points as [x, y, t] where t is millisecond timestamp.
    Falls back to Euclidean distances between consecutive points if no timestamp.
    """
    if len(drawn) < 3:
        return 0.0

    has_timestamps = len(drawn[0]) >= 3

    speeds = []
    for i in range(1, len(drawn)):
        dist = math.dist(drawn[i - 1][:2], drawn[i][:2])
        if has_timestamps:
            dt = max(1.0, drawn[i][2] - drawn[i - 1][2])  # ms
            speeds.append(dist / dt)
        else:
            speeds.append(dist)  # pixel distance per step

    if not speeds:
        return 0.0

    mean     = sum(speeds) / len(speeds)
    variance = sum((s - mean) ** 2 for s in speeds) / len(speeds)
    std_dev  = math.sqrt(variance)

    # Normalize: cap at mean*3 so outliers don't break the scale
    reference_scale = max(mean * 3, 1e-9)
    return round(min(1.0, std_dev / reference_scale), 4)


# ──────────────────────────────────────────────────────────────────────────────
# Combined analysis
# ──────────────────────────────────────────────────────────────────────────────

def analyze_stroke(
    drawn: list[Point],
    reference: list[Point],
    tolerance: float = 8.0,
) -> StrokeMetrics:
    """
    Full geometric analysis of a single drawn stroke vs its reference.

    Args:
        drawn:      List of [x, y] or [x, y, timestamp_ms] points from the canvas
        reference:  List of [x, y] points from alphabet_en.py stroke data
        tolerance:  Coverage tolerance in grid units (default 8 out of 100)

    Returns:
        StrokeMetrics dict with all normalized metrics in [0, 1].
    """
    direction  = compute_direction_score(drawn, reference)
    coverage   = compute_coverage_score(drawn, reference, tolerance)
    smoothness = compute_smoothness_score(drawn)
    path_error = compute_normalized_path_error(drawn, reference)
    overshoot  = compute_overshoot_ratio(drawn, reference)
    vel_var    = compute_velocity_variance(drawn)

    # Path error is "lower is better" — invert for scoring
    path_score = 1.0 - path_error

    combined = (
        WEIGHTS["direction"]  * direction  +
        WEIGHTS["coverage"]   * coverage   +
        WEIGHTS["smoothness"] * smoothness +
        WEIGHTS["path_error"] * path_score
    )

    return StrokeMetrics(
        direction_score         = direction,
        coverage_score          = coverage,
        smoothness_score        = smoothness,
        normalized_path_error   = path_error,
        overshoot_ratio         = overshoot,
        stroke_velocity_variance = vel_var,
        combined_score          = round(min(1.0, combined), 4),
    )


def analyze_letter(
    drawn_strokes: list[list[Point]],
    reference_strokes: list[dict],  # from alphabet_en.py: {"points": [...], ...}
) -> dict:
    """
    Analyze all strokes of a drawn letter against the reference.
    Pairs drawn strokes with reference strokes by index (best-effort if counts differ).

    Returns per-stroke metrics + overall letter score.
    """
    stroke_results = []
    n = max(len(drawn_strokes), len(reference_strokes))

    for i in range(n):
        if i >= len(drawn_strokes):
            # Missing drawn stroke — zero scores
            stroke_results.append({
                "stroke_id": i + 1,
                "status": "missing",
                **StrokeMetrics(
                    direction_score=0.0, coverage_score=0.0, smoothness_score=0.0,
                    normalized_path_error=1.0, overshoot_ratio=0.0,
                    stroke_velocity_variance=0.0, combined_score=0.0,
                ),
            })
        elif i >= len(reference_strokes):
            # Extra drawn stroke — ignored
            continue
        else:
            ref_pts = reference_strokes[i].get("points", [])
            metrics = analyze_stroke(drawn_strokes[i], ref_pts)
            stroke_results.append({
                "stroke_id": i + 1,
                "status": "analyzed",
                **metrics,
            })

    if not stroke_results:
        overall = 0.0
    else:
        overall = sum(s["combined_score"] for s in stroke_results) / len(stroke_results)

    return {
        "strokes":       stroke_results,
        "overall_score": round(overall, 4),
        "stroke_count":  {"drawn": len(drawn_strokes), "expected": len(reference_strokes)},
    }
