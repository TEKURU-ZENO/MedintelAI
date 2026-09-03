"""
app/services/free_writing/quality_feedback_generator.py

Generates emotionally intelligent, non-correctness feedback messages.

Philosophy: Never say "wrong." Always say "becoming."
Profile-aware: early_learner gets emoji-heavy, adult gets analytical phrasing.
"""

from typing import Literal
from app.services.free_writing.motor_quality_analyzer import MotorQualityMetrics
from app.services.free_writing.spatial_quality_analyzer import SpatialQualityMetrics

ProfileType = Literal["early_learner", "child", "adult"]
QualityBand = Literal["developing", "building", "strong", "exceptional"]


# ── Feedback Templates ─────────────────────────────────────────────────────────
# Each key maps to (early_learner_msg, child_msg, adult_msg)

SMOOTHNESS_HIGH = (
    "Your strokes are so smooth! ✨",
    "Your writing is flowing really nicely ✨",
    "Stroke smoothness is strong today.",
)
SMOOTHNESS_BUILDING = (
    "You're getting smoother! Keep going 🌊",
    "Your strokes are getting steadier — keep building ✍️",
    "Smoothness is improving. Maintain steady pen speed.",
)
SMOOTHNESS_LOW = (
    "Try moving your hand slowly like a snail 🐌",
    "Slow down a little — let your hand glide ✍️",
    "Reduce pen speed slightly for cleaner strokes.",
)

SPACING_HIGH = (
    "Your letters have nice breathing room! 🌸",
    "Your spacing looks much more even today 🌱",
    "Spacing consistency is excellent.",
)
SPACING_BUILDING = (
    "Good spacing! You're getting better at it 👍",
    "Spacing is improving — keep that rhythm going",
    "Spacing regularity is building well.",
)
SPACING_LOW = (
    "Try leaving a little gap between your words 💭",
    "A little more breathing room between words would help 💭",
    "Work on consistent inter-word spacing.",
)

CONFIDENCE_HIGH = (
    "You wrote with so much confidence! 💪",
    "You wrote with real confidence today 💪",
    "High stroke confidence detected — excellent session.",
)
HESITATION_DETECTED = (
    "Take your time! No rush at all 🐢",
    "Take a breath before each stroke — no rush 🍃",
    "Hesitation detected. Pause, breathe, then commit to the stroke.",
)

BASELINE_HIGH = (
    "Your writing stays on the line so well! 📏",
    "Your writing is staying nice and level 📏",
    "Baseline alignment is very consistent.",
)
BASELINE_BUILDING = (
    "You're keeping your letters on the line — great! 📐",
    "Your baseline alignment is improving 📐",
    "Baseline consistency is developing well.",
)

BAND_MESSAGES: dict[QualityBand, tuple[str, str, str]] = {
    "developing": (
        "You're just getting started — and that's amazing! 🌱",
        "Every session builds your writing foundation 🌱",
        "Foundation-building session. Consistency is the goal.",
    ),
    "building": (
        "You're building really good writing habits! 🔨",
        "You're building real writing strength 🔨",
        "Quality is building steadily. Keep the sessions consistent.",
    ),
    "strong": (
        "Your writing is so strong today! ⭐",
        "Strong writing session today ⭐",
        "Strong session. Quality metrics above target.",
    ),
    "exceptional": (
        "WOW! Your writing is amazing today! 🏆",
        "Exceptional writing today — you should be proud! 🏆",
        "Exceptional quality. All metrics are high.",
    ),
}

IMPROVEMENT_MESSAGE = (
    "You're getting better every time! 🚀",
    "You're improving! Keep building that habit 🔥",
    "Consistent improvement trend detected.",
)

STREAK_MESSAGE = (
    "Day {n} of writing — you're doing it! 🎉",
    "Day {n} in a row — your consistency is your superpower 🏆",
    "Session {n} this week — excellent consistency.",
)


# ── Selector ──────────────────────────────────────────────────────────────────

def _pick(msgs: tuple[str, str, str], profile: ProfileType) -> str:
    if profile == "early_learner":
        return msgs[0]
    elif profile == "child":
        return msgs[1]
    return msgs[2]


# ── Main Generator ─────────────────────────────────────────────────────────────

def generate_feedback(
    motor: MotorQualityMetrics,
    spatial: SpatialQualityMetrics,
    quality_band: QualityBand,
    profile_type: ProfileType,
    is_improving: bool = False,
    streak_days: int = 0,
) -> list[str]:
    """
    Returns a list of 2–4 emotionally intelligent feedback strings.

    Rules:
    - Always starts with the band message (sets emotional tone)
    - Never surfaces more than ONE focus area (not two negatives)
    - Strength is mentioned before focus area
    - Streak is always mentioned if > 1
    """
    messages: list[str] = []

    # 1. Band message (tone setter)
    messages.append(_pick(BAND_MESSAGES[quality_band], profile_type))

    # 2. Identify primary strength
    strength_scores = {
        "smoothness":  motor["smoothness_score"],
        "confidence":  motor["stroke_confidence"],
        "spacing":     spatial["spacing_regularity"],
        "baseline":    spatial["baseline_consistency"],
    }
    primary_strength = max(strength_scores, key=lambda k: strength_scores[k])

    if primary_strength == "smoothness" and motor["smoothness_score"] >= 0.7:
        messages.append(_pick(SMOOTHNESS_HIGH, profile_type))
    elif primary_strength == "spacing" and spatial["spacing_regularity"] >= 0.7:
        messages.append(_pick(SPACING_HIGH, profile_type))
    elif primary_strength == "baseline" and spatial["baseline_consistency"] >= 0.7:
        messages.append(_pick(BASELINE_HIGH, profile_type))
    elif primary_strength == "confidence" and motor["stroke_confidence"] >= 0.7:
        messages.append(_pick(CONFIDENCE_HIGH, profile_type))

    # 3. Identify ONE focus area (lowest score, only if meaningfully low)
    focus_scores = {
        "smoothness":  motor["smoothness_score"],
        "spacing":     spatial["spacing_regularity"],
        "baseline":    spatial["baseline_consistency"],
    }
    # Remove already-mentioned strength from focus candidates
    focus_scores.pop(primary_strength, None)

    primary_focus = min(focus_scores, key=lambda k: focus_scores[k])
    focus_value = focus_scores[primary_focus]

    if focus_value < 0.5:  # Only mention if clearly below threshold
        if primary_focus == "smoothness":
            if motor["smoothness_score"] < 0.4:
                messages.append(_pick(SMOOTHNESS_LOW, profile_type))
            else:
                messages.append(_pick(SMOOTHNESS_BUILDING, profile_type))
        elif primary_focus == "spacing":
            if spatial["spacing_regularity"] < 0.4:
                messages.append(_pick(SPACING_LOW, profile_type))
            else:
                messages.append(_pick(SPACING_BUILDING, profile_type))
        elif primary_focus == "baseline":
            messages.append(_pick(BASELINE_BUILDING, profile_type))

    # 4. Hesitation coaching (independent of focus area)
    if motor["hesitation_ratio"] > 0.4:
        messages.append(_pick(HESITATION_DETECTED, profile_type))

    # 5. Improvement trend
    if is_improving:
        messages.append(_pick(IMPROVEMENT_MESSAGE, profile_type))

    # 6. Streak callout (caps at max 4 messages including streak)
    if streak_days > 1 and len(messages) < 4:
        template = _pick(STREAK_MESSAGE, profile_type)
        messages.append(template.format(n=streak_days))

    return messages[:4]  # never overwhelm — cap at 4


def derive_quality_band(overall_score: float) -> QualityBand:
    """Maps composite [0-1] score to quality band."""
    if overall_score >= 0.82:
        return "exceptional"
    elif overall_score >= 0.65:
        return "strong"
    elif overall_score >= 0.42:
        return "building"
    return "developing"
