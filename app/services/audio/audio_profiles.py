"""
app/services/audio/audio_profiles.py — Audio Priority Levels

Determines how much audio guidance a user should receive based
on their behavioral learning style (Phase 5).
"""

from typing import Dict, Any

def get_audio_profile(learning_style: str) -> Dict[str, Any]:
    """
    Returns the audio configuration for a specific learning style.
    - replay_dependent: Needs high guidance, lots of audio, high celebration.
    - methodical: Lower verbosity, might get annoyed by too much audio.
    - visual: Needs visual + auditory mapping (autoplay on).
    - impulsive: Needs pacing audio (slower down prompts).
    """
    if learning_style == "replay_dependent":
        return {
            "verbosity": "high",
            "autoplay": True,
            "celebration_frequency": 1.0,
            "coaching_enabled": True
        }
    elif learning_style == "methodical":
        return {
            "verbosity": "low",
            "autoplay": False,
            "celebration_frequency": 0.3,
            "coaching_enabled": False
        }
    elif learning_style == "visual":
        return {
            "verbosity": "medium",
            "autoplay": True,
            "celebration_frequency": 0.5,
            "coaching_enabled": True
        }
    elif learning_style == "impulsive":
        return {
            "verbosity": "medium",
            "autoplay": False,  # Make them trigger it deliberately
            "celebration_frequency": 0.7,
            "coaching_enabled": True
        }
    else:
        # Default
        return {
            "verbosity": "medium",
            "autoplay": True,
            "celebration_frequency": 0.5,
            "coaching_enabled": True
        }
