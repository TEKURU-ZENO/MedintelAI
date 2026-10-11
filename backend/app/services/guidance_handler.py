"""
app/services/guidance_handler.py — Guidance Event Processing

Called by POST /sessions/{id}/guidance-event.
Runs authoritative backend validation of a single drawn stroke.

Responsibilities:
  1. Fetch reference stroke points from module data
  2. Run stroke analyzer (normalized metrics)
  3. Run direction detector (with confidence)
  4. Determine if stroke unlocks the next (with failsafe)
  5. Select feedback type + message (profile-aware)
  6. Track stroke attempt counts in session metadata

This is intentionally separate from LearningEngine (which handles full
session lifecycle). GuidanceHandler handles per-stroke mid-session events.
"""

from app.services.analysis.stroke_analyzer import analyze_stroke
from app.services.analysis.direction_detector import detect_direction, matches_expected

# Thresholds
UNLOCK_THRESHOLD       = 0.60   # combined_score >= this → unlock next stroke
MAX_ATTEMPTS_FAILSAFE  = 3      # unlock regardless after this many attempts

# Weighted trace percent formula (from user spec):
# trace_percent = coverage*0.5 + direction*0.3 + smoothness*0.2
def compute_trace_percent(direction: float, coverage: float, smoothness: float) -> float:
    return round((coverage * 0.5 + direction * 0.3 + smoothness * 0.2) * 100, 1)


def _get_reference_points(module_type: str, target_item: str, stroke_id: int) -> list:
    """Load reference stroke points from module data."""
    if module_type == "alphabet_practice":
        from app.data.modules.alphabet_en import ALPHABET
        letter_data = ALPHABET.get(target_item.upper(), {})
        strokes = letter_data.get("strokes", [])
        for s in strokes:
            if s["id"] == stroke_id:
                return s["points"]
    return []


def _select_feedback(
    scores: dict,
    direction_match: bool,
    attempt_number: int,
    failsafe: bool,
    profile_type: str = "child",
) -> tuple[str, str]:
    """
    Return (feedback_type, feedback_message) based on scores + context.

    Feedback is profile-aware:
      early_learner → warm, encouraging, emoji-heavy
      child         → motivational, brief
      adult         → precise, professional
    """
    combined   = scores["combined_score"]
    coverage   = scores["coverage_score"]
    smoothness = scores["smoothness_score"]

    is_early   = profile_type == "early_learner"
    is_child   = profile_type == "child"

    if failsafe:
        return ("correction",
                "Great try! Let's move to the next stroke. 🌟" if is_early
                else "Moving on — keep practicing this one later!" if is_child
                else "Failsafe: advancing to next stroke. Review this stroke later.")

    if combined >= 0.90:
        msg = "🎉 Perfect!" if is_early else "Perfect trace!" if is_child else "Excellent — all metrics optimal."
        return ("celebration", msg)

    if combined >= 0.75:
        if not direction_match:
            msg = "Almost! Check the direction ✨" if is_early else "Good — watch the direction" if is_child else "Good score, direction slightly off."
        elif smoothness < 0.5:
            msg = "Slow down a little! 🐢" if is_early else "Try to be a bit smoother" if is_child else "Reduce speed variance for smoother strokes."
        else:
            msg = "Great job! 👍" if is_early else "Nice work!" if is_child else "Well executed."
        return ("encouragement", msg)

    if combined >= 0.50:
        if coverage < 0.5:
            msg = "Follow the dotted line! 🖊️" if is_early else "Cover more of the path" if is_child else "Coverage is low — trace closer to the guide."
        elif not direction_match:
            msg = "Wrong way! Try again 🔄" if is_early else "Check the direction and retry" if is_child else "Direction mismatch — review the stroke hint."
        else:
            msg = "Getting closer! 💪" if is_early else "Decent — try once more" if is_child else "Marginal — retry for a cleaner result."
        return ("correction", msg)

    # Combined < 0.50
    if attempt_number >= 2:
        msg = "Let me show you how! 👀" if is_early else "Watch the ghost guide" if is_child else "Below threshold — ghost replay available."
        return ("warning", msg)

    msg = "Try again! You've got this 🌈" if is_early else "Try again" if is_child else "Below threshold — retry."
    return ("warning", msg)


def process_guidance_event(
    session_id: int,
    module_type: str,
    target_item: str,
    event: dict,                  # GuidanceEvent-shaped dict
    stroke_attempt_counts: dict,  # {"1": 2, "2": 1, ...} — mutable, caller persists
    profile_type: str = "child",
) -> dict:
    """
    Process a single stroke guidance event.

    Args:
        session_id:           ID of the active PracticeSession
        module_type:          e.g. "alphabet_practice"
        target_item:          e.g. "A"
        event:                GuidanceEvent data
        stroke_attempt_counts: mutable dict tracking per-stroke attempt count
        profile_type:         for feedback tone selection

    Returns dict matching GuidanceResponse schema.
    """
    stroke_id   = event["stroke_id"]
    drawn       = event["drawn_points"]
    ref_id      = event.get("reference_stroke_id") or stroke_id
    hesitation  = event.get("hesitation_ms")

    # Track attempt count for this stroke
    key = str(stroke_id)
    stroke_attempt_counts[key] = stroke_attempt_counts.get(key, 0) + 1
    attempt_number = stroke_attempt_counts[key]
    failsafe = attempt_number > MAX_ATTEMPTS_FAILSAFE

    # Get reference stroke
    ref_points = _get_reference_points(module_type, target_item, ref_id)

    if not ref_points or len(drawn) < 2:
        # Can't score — give a neutral response
        return {
            "stroke_id":          stroke_id,
            "scores":             {
                "direction_score": 0.5, "coverage_score": 0.0, "smoothness_score": 0.5,
                "normalized_path_error": 1.0, "overshoot_ratio": 0.0,
                "stroke_velocity_variance": 0.0, "combined_score": 0.0,
            },
            "direction_detected":  {"direction": "unknown", "confidence": 0.0,
                                    "angle_degrees": 0.0, "displacement": 0.0},
            "direction_match":     False,
            "feedback_type":       "idle",
            "feedback_message":    "Draw the stroke to receive feedback.",
            "unlock_next_stroke":  failsafe,
            "failsafe_unlock":     failsafe,
            "attempt_number":      attempt_number,
            "trace_percent":       0.0,
            "hesitation_ms":       hesitation,
        }

    # ── Authoritative scoring ─────────────────────────────────────────────────
    scores = analyze_stroke(drawn, ref_points)

    # ── Direction detection ───────────────────────────────────────────────────
    direction_result = detect_direction(drawn)

    # Get expected direction from reference stroke (if module provides it)
    expected_dir = None
    if module_type == "alphabet_practice":
        from app.data.modules.alphabet_en import ALPHABET
        strokes = ALPHABET.get(target_item.upper(), {}).get("strokes", [])
        for s in strokes:
            if s["id"] == ref_id:
                expected_dir = s.get("direction")
                break

    direction_match = (
        expected_dir is None or          # no expected direction specified
        direction_result["direction"] == expected_dir or
        direction_result["confidence"] < 0.5  # ambiguous — don't penalize
    )

    # ── Unlock logic ──────────────────────────────────────────────────────────
    unlock = scores["combined_score"] >= UNLOCK_THRESHOLD or failsafe

    # ── Weighted trace percent ────────────────────────────────────────────────
    trace_pct = compute_trace_percent(
        scores["direction_score"],
        scores["coverage_score"],
        scores["smoothness_score"],
    )

    # ── Feedback ──────────────────────────────────────────────────────────────
    fb_type, fb_message = _select_feedback(
        scores, direction_match, attempt_number, failsafe, profile_type
    )

    return {
        "stroke_id":          stroke_id,
        "scores":             scores,
        "direction_detected": direction_result,
        "direction_match":    direction_match,
        "feedback_type":      fb_type,
        "feedback_message":   fb_message,
        "unlock_next_stroke": unlock,
        "failsafe_unlock":    failsafe,
        "attempt_number":     attempt_number,
        "trace_percent":      trace_pct,
        "hesitation_ms":      hesitation,
    }
