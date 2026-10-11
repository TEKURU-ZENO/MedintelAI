"""
app/services/audio/celebration_audio.py — Success Audio Tiers

Dopamine reinforcement architecture via tiered audio celebrations.
"""

import random
from app.services.audio.audio_cache import get_or_generate_audio

CELEBRATION_TIERS = {
    "minor": [
        "Nice try!",
        "Good effort!",
        "Keep going!"
    ],
    "strong": [
        "Amazing work!",
        "Perfect trace!",
        "You're doing great!"
    ],
    "streak": [
        "You're on fire!",
        "Improving so fast!",
        "Unstoppable!"
    ]
}

def get_celebration_audio_url(tier: str) -> str:
    """
    Returns the URL for a random celebration phrase from the requested tier.
    """
    phrases = CELEBRATION_TIERS.get(tier)
    if not phrases:
        return ""
    
    phrase = random.choice(phrases)
    # create a safe filename
    safe_name = phrase.lower().replace(" ", "_").replace("!", "").replace("'", "")
    return get_or_generate_audio(phrase, f"celebrate_{safe_name}")
