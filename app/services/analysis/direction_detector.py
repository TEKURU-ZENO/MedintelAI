"""
app/services/analysis/direction_detector.py — Direction Classification

Classifies the dominant direction of a drawn stroke and returns a
confidence score. Confidence is critical for:
  - Curved strokes (ambiguous between curve-left and down-right)
  - Tamil / cursive scripts (Phase 10)
  - Uncertainty-aware feedback ("It looks like you went right — try curving left")

Returns:
  { "direction": "right", "confidence": 0.88 }

Supported directions (12 classes):
  Cardinal:   up, down, left, right
  Diagonal:   up-left, up-right, down-left, down-right
  Curves:     curve-left, curve-right, clockwise-oval, s-curve
"""

import math
from typing import TypedDict

Point = list[float]   # [x, y] or [x, y, t]


class DirectionResult(TypedDict):
    direction: str
    confidence: float
    angle_degrees: float    # raw net displacement angle (for debugging / ML)
    displacement: float     # total net displacement in grid units


# ──────────────────────────────────────────────────────────────────────────────
# Direction map — angle ranges → direction label
# Angles are measured from positive-X axis, clockwise (screen coordinates)
# 0° = right, 90° = down, 180°/-180° = left, -90° = up
# ──────────────────────────────────────────────────────────────────────────────

_LINEAR_DIRECTIONS = [
    ( -22.5,   22.5, "right"),
    (  22.5,   67.5, "down-right"),
    (  67.5,  112.5, "down"),
    ( 112.5,  157.5, "down-left"),
    ( 157.5,  180.0, "left"),
    (-180.0, -157.5, "left"),
    (-157.5, -112.5, "up-left"),
    (-112.5,  -67.5, "up"),
    ( -67.5,  -22.5, "up-right"),
]


def _net_angle(points: list[Point]) -> float:
    """Angle of the net displacement vector (start → end), in degrees [-180, 180]."""
    dx = points[-1][0] - points[0][0]
    dy = points[-1][1] - points[0][1]
    return math.degrees(math.atan2(dy, dx))


def _curvature_signature(points: list[Point]) -> tuple[float, float]:
    """
    Returns (mean_curvature, curvature_direction_consistency).
    mean_curvature > 0 → curves to one side
    consistency near 1.0 → uniform curve (circle arc); near 0 → complex shape
    """
    if len(points) < 4:
        return 0.0, 0.0

    cross_products = []
    for i in range(1, len(points) - 1):
        v1 = (points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
        v2 = (points[i+1][0] - points[i][0], points[i+1][1] - points[i][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        cross_products.append(cross)

    if not cross_products:
        return 0.0, 0.0

    mean_cross = sum(cross_products) / len(cross_products)
    # Consistency: what fraction have the same sign as the mean?
    same_sign = sum(1 for c in cross_products if c * mean_cross > 0)
    consistency = same_sign / len(cross_products)
    return mean_cross, consistency


def _is_oval(points: list[Point]) -> tuple[bool, float]:
    """
    Detect if a stroke is a closed-ish oval (for letter O, Q).
    Returns (is_oval, confidence).
    """
    if len(points) < 6:
        return False, 0.0

    start, end = points[0][:2], points[-1][:2]
    closure_dist = math.dist(start, end)

    # Total arc length
    arc_len = sum(
        math.dist(points[i][:2], points[i-1][:2])
        for i in range(1, len(points))
    )
    if arc_len < 1e-9:
        return False, 0.0

    closure_ratio = closure_dist / arc_len
    # An oval stroke: start and end are close relative to total path length
    is_oval = closure_ratio < 0.25
    confidence = max(0.0, 1.0 - closure_ratio / 0.25)
    return is_oval, round(confidence, 3)


def _is_s_curve(points: list[Point]) -> tuple[bool, float]:
    """
    Detect S-curve: curvature changes sign at least once.
    Returns (is_s_curve, confidence).
    """
    if len(points) < 6:
        return False, 0.0

    crosses = []
    for i in range(1, len(points) - 1):
        v1 = (points[i][0] - points[i-1][0], points[i][1] - points[i-1][1])
        v2 = (points[i+1][0] - points[i][0], points[i+1][1] - points[i][1])
        cross = v1[0] * v2[1] - v1[1] * v2[0]
        crosses.append(cross)

    if len(crosses) < 4:
        return False, 0.0

    # Count sign changes
    sign_changes = sum(
        1 for i in range(1, len(crosses))
        if crosses[i] * crosses[i-1] < 0
    )
    # S-curve: roughly half the points change curvature direction
    change_ratio = sign_changes / (len(crosses) - 1)
    is_s = 0.2 < change_ratio < 0.7
    confidence = 0.0
    if is_s:
        # Higher confidence the closer change_ratio is to 0.4–0.6
        confidence = 1.0 - abs(change_ratio - 0.4) / 0.4
    return is_s, round(max(0.0, confidence), 3)


# ──────────────────────────────────────────────────────────────────────────────
# Main detection function
# ──────────────────────────────────────────────────────────────────────────────

def detect_direction(points: list[Point]) -> DirectionResult:
    """
    Classify the dominant direction of a drawn stroke.

    Detection order (most specific first):
      1. Oval (closed curve)
      2. S-curve (sign-change curve)
      3. Uniform curve (curve-left / curve-right)
      4. Linear direction (8 cardinal / diagonal classes)

    Confidence reflects how unambiguous the classification is:
      - High confidence (>0.85): clearly one direction
      - Medium (0.6–0.85): reasonable guess
      - Low (<0.6): ambiguous (especially for curves)
    """
    if len(points) < 2:
        return DirectionResult(
            direction="unknown", confidence=0.0,
            angle_degrees=0.0, displacement=0.0,
        )

    net_angle     = _net_angle(points)
    displacement  = math.dist(points[0][:2], points[-1][:2])
    mean_curv, consistency = _curvature_signature(points)

    # ── 1. Oval detection ─────────────────────────────────────────────────────
    is_oval, oval_conf = _is_oval(points)
    if is_oval and oval_conf > 0.5:
        return DirectionResult(
            direction="clockwise-oval" if mean_curv > 0 else "clockwise-oval",
            confidence=oval_conf,
            angle_degrees=round(net_angle, 2),
            displacement=round(displacement, 2),
        )

    # ── 2. S-curve detection ──────────────────────────────────────────────────
    is_s, s_conf = _is_s_curve(points)
    if is_s and s_conf > 0.5:
        return DirectionResult(
            direction="s-curve",
            confidence=s_conf,
            angle_degrees=round(net_angle, 2),
            displacement=round(displacement, 2),
        )

    # ── 3. Uniform curve (curve-left / curve-right) ───────────────────────────
    # High curvature consistency AND significant total curvature → curved stroke
    curvature_magnitude = abs(mean_curv)
    if consistency > 0.7 and curvature_magnitude > 20:
        direction    = "curve-right" if mean_curv > 0 else "curve-left"
        # Confidence: how consistent and how curved
        curve_conf   = min(1.0, consistency * (curvature_magnitude / 200))
        return DirectionResult(
            direction=direction,
            confidence=round(curve_conf, 3),
            angle_degrees=round(net_angle, 2),
            displacement=round(displacement, 2),
        )

    # ── 4. Linear direction ───────────────────────────────────────────────────
    for lo, hi, label in _LINEAR_DIRECTIONS:
        if lo <= net_angle <= hi:
            # Confidence: how centered in the angle band (22.5° per band)
            band_center = (lo + hi) / 2
            deviation   = abs(net_angle - band_center)
            confidence  = 1.0 - (deviation / 22.5)
            # Reduce confidence if it was actually quite curved
            if consistency > 0.6 and curvature_magnitude > 10:
                confidence *= 0.75  # was probably a curve, not a straight line

            return DirectionResult(
                direction=direction if 'direction' in dir() else label,
                confidence=round(max(0.0, confidence), 3),
                angle_degrees=round(net_angle, 2),
                displacement=round(displacement, 2),
            )

    # Fallback — should never reach here
    return DirectionResult(
        direction="unknown", confidence=0.0,
        angle_degrees=round(net_angle, 2),
        displacement=round(displacement, 2),
    )


def matches_expected(
    drawn: list[Point],
    expected_direction: str,
    min_confidence: float = 0.5,
) -> tuple[bool, DirectionResult]:
    """
    Convenience: check if drawn stroke matches the expected direction string.

    Returns:
        (is_match, result_dict)
    """
    result = detect_direction(drawn)
    is_match = (
        result["direction"] == expected_direction
        and result["confidence"] >= min_confidence
    )
    return is_match, result
