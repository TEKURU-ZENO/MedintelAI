"""
app/services/ml/adaptive_session_planner.py — Personalized Session Plan

"The future AI brain." Generates a personalized practice plan from all signals.
Currently rule-based with weighted scoring — architecture ready for ML insertion.

Plan output:
  {
    "items":            list[str],      ordered practice items
    "session_length_s": int,            recommended seconds
    "focus_mode":       str,            "standard" | "deep_focus" | "confidence_boost" | "quick_win"
    "reasoning":        str,            human-readable explanation
    "difficulty":       str,
    "confidence":       float,
    "source":           "rule",
  }
"""

from __future__ import annotations
from app.services.audio.audio_orchestrator import generate_session_audio_metadata

# ── Session length configs ────────────────────────────────────────────────────

SESSION_CONFIGS = {
    "quick_win":        {"seconds": 180, "items": 4,  "description": "Short focused session"},
    "confidence_boost": {"seconds": 300, "items": 6,  "description": "Mix of easy + challenge"},
    "standard":         {"seconds": 480, "items": 10, "description": "Full practice session"},
    "deep_focus":       {"seconds": 600, "items": 8,  "description": "Extended focus on weak areas"},
}

# ── Focus mode selector ───────────────────────────────────────────────────────

def _select_focus_mode(
    frustration_level: str,
    engagement_level:  str,
    trend:             str,
    rolling_accuracy:  float,
    learning_style:    str,
) -> str:
    """Rule-based focus mode selection."""
    if frustration_level == "high":
        return "quick_win"           # frustrated → short achievable wins
    if rolling_accuracy < 0.50 or trend == "declining":
        return "deep_focus"          # struggling → extended targeted work
    if engagement_level == "low":
        return "confidence_boost"    # disengaged → mix easy + new
    if learning_style == "impulsive":
        return "deep_focus"          # impulsive learner → slow down
    return "standard"


def _session_items(
    recommended_items: list[dict],
    focus_mode:        str,
    best_letters:      list[str],
) -> list[str]:
    """Build ordered item list based on focus mode."""
    config    = SESSION_CONFIGS[focus_mode]
    max_items = config["items"]

    # Extract struggle items (priority high/medium first)
    struggle  = [r["item"] for r in recommended_items if r.get("priority") in ("high", "medium")]
    easy_wins = [r["item"] for r in recommended_items if r.get("priority") == "low"]
    easy_wins += [l for l in best_letters if l not in struggle + easy_wins][:2]

    if focus_mode == "confidence_boost":
        # Lead with 2 easy wins, then hard
        items = easy_wins[:2] + struggle[:max_items - 2]
    elif focus_mode == "quick_win":
        # Only easy wins + one hard item
        items = easy_wins[:2] + struggle[:1] + easy_wins[2:max_items - 3]
    elif focus_mode == "deep_focus":
        # All hard items, no easy padding
        items = struggle[:max_items]
    else:
        # Standard: mix
        items = struggle[:max_items - 1] + easy_wins[:1]

    return items[:max_items]


def _reasoning(
    focus_mode:        str,
    frustration_level: str,
    learning_style:    str,
    trend:             str,
    rolling_accuracy:  float,
) -> str:
    parts = []
    if frustration_level == "high":
        parts.append("Shorter session to reduce frustration")
    if trend == "declining":
        parts.append("Extended focus on weak areas due to declining trend")
    if learning_style == "visual":
        parts.append("Visual learner — replay assistance recommended")
    elif learning_style == "impulsive":
        parts.append("Active learner — slow down between strokes")
    if rolling_accuracy >= 0.85:
        parts.append("Strong accuracy — consider advancing difficulty")
    return "; ".join(parts) if parts else SESSION_CONFIGS[focus_mode]["description"]


# ── Main planner ──────────────────────────────────────────────────────────────

def build_session_plan(
    recommended_items:  list[dict],
    learning_style:     str,
    frustration_level:  str,
    engagement_level:   str,
    trend:              str,
    rolling_accuracy:   float,
    difficulty:         str,
    best_letters:       list[str],
    data_completeness:  float = 1.0,
) -> dict:
    """
    Generates a complete, personalized session plan.
    All signals feed into focus_mode → session config → ordered items.
    """
    focus_mode = _select_focus_mode(
        frustration_level, engagement_level, trend, rolling_accuracy, learning_style,
    )
    config = SESSION_CONFIGS[focus_mode]
    items  = _session_items(recommended_items, focus_mode, best_letters)
    reason = _reasoning(focus_mode, frustration_level, learning_style, trend, rolling_accuracy)

    # Confidence = completeness × how much data drove this decision
    signal_count = sum([
        1 if frustration_level != "low" else 0,
        1 if trend != "stable" else 0,
        1 if engagement_level != "medium" else 0,
        1 if learning_style != "methodical" else 0,
    ])
    confidence = round(data_completeness * (0.60 + signal_count * 0.10), 4)

    # Generate Audio Profile and Metadata (Phase 6)
    audio_metadata = generate_session_audio_metadata(items, learning_style, frustration_level)

    return {
        "items":             items,
        "session_length_s":  config["seconds"],
        "focus_mode":        focus_mode,
        "reasoning":         reason,
        "difficulty":        difficulty,
        "confidence":        min(0.95, confidence),
        "source":            "rule",
        "learning_style":    learning_style,
        "session_config":    config["description"],
        "audio_metadata":    audio_metadata,
    }
