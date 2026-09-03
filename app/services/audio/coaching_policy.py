"""
app/services/audio/coaching_policy.py — Coaching Audio Policy

Controls when audio triggers, handling cooldowns, intensity,
replay frequency, and interruption rules based on frustration and style.
"""

from typing import Dict, Any

def get_coaching_policy(learning_style: str, frustration_level: str) -> Dict[str, Any]:
    """
    Returns the frontend configuration for coaching audio behavior.
    """
    # 1. Determine intensity based on frustration
    intensity = "medium"
    if frustration_level == "high":
        intensity = "high"
    elif frustration_level == "low":
        intensity = "low"
        
    # 2. Base policy overrides per learning style
    cooldown_multiplier = 1.0
    if learning_style == "methodical":
        cooldown_multiplier = 1.5  # Need more quiet time
    elif learning_style == "replay_dependent":
        cooldown_multiplier = 0.7  # Wants more frequent audio

    return {
        "intensity": intensity,
        "cooldown_multiplier": cooldown_multiplier,
        "global_cooldown_ms": int(2000 * cooldown_multiplier),
        "allow_interruptions": learning_style != "methodical"
    }
