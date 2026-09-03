"""
app/services/audio/audio_orchestrator.py — Audio Session Orchestrator

Responsible for generating the complete audio payload for a session plan.
Ensures that the frontend doesn't need to make network requests during practice.
"""

from typing import Dict, Any, List
from app.services.audio.audio_profiles import get_audio_profile
from app.services.audio.pronunciation_service import get_item_pronunciation_url
from app.services.audio.coaching_audio_service import get_coaching_audio_url, COACHING_PHRASES
from app.services.audio.celebration_audio import get_celebration_audio_url
from app.services.audio.coaching_policy import get_coaching_policy
from app.services.audio.coaching_event_mapper import EVENT_TO_AUDIO_MAP

def generate_session_audio_metadata(
    items: List[str],
    learning_style: str,
    frustration_level: str = "low"
) -> Dict[str, Any]:
    """
    Generates a complete audio payload for the session, pre-computing
    pronunciation, coaching, and celebration URLs based on learning style.
    """
    profile = get_audio_profile(learning_style)
    
    # 1. Pronunciations for all items
    item_audio = {}
    for item in items:
        item_audio[item] = get_item_pronunciation_url(item)
        
    # 2. Coaching policy & phrases based on frustration
    policy = get_coaching_policy(learning_style, frustration_level)
    intensity = policy["intensity"]
    
    coach_audio = {}
    if profile.get("coaching_enabled"):
        for intent in COACHING_PHRASES.keys():
            coach_audio[intent] = get_coaching_audio_url(intent, intensity)
        
    # 3. Celebrations (preload one of each tier)
    celebration_audio = {
        "minor": get_celebration_audio_url("minor"),
        "strong": get_celebration_audio_url("strong"),
        "streak": get_celebration_audio_url("streak")
    }
    
    return {
        "profile": profile,
        "policy": policy,
        "event_map": EVENT_TO_AUDIO_MAP,
        "item_audio": item_audio,
        "coach_audio": coach_audio,
        "celebration_audio": celebration_audio
    }
