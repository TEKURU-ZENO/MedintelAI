"""
app/services/audio/coaching_audio_service.py — Audio Guidance

Generates coaching instructions like "Start from the top" or "Curve gently".
"""

from app.services.audio.audio_cache import get_or_generate_audio

COACHING_PHRASES = {
    "start_top": {
        "low": "Start from the top.",
        "medium": "Make sure to start from the top.",
        "high": "It's okay, let's start from the top."
    },
    "curve_gently": {
        "low": "Curve gently.",
        "medium": "Curve it gently.",
        "high": "Take your time and curve gently."
    },
    "wrong_way": {
        "low": "Oops, wrong way.",
        "medium": "Try going the other way.",
        "high": "That's okay, let's try going the other way."
    },
    "stay_on_line": {
        "low": "Stay on the line.",
        "medium": "Try to follow the line closer.",
        "high": "You're doing okay. Just take your time on the line."
    },
    "watch_carefully": {
        "low": "Watch the replay.",
        "medium": "Watch carefully.",
        "high": "Let's watch how it's done together."
    }
}

def get_coaching_audio_url(intent: str, intensity: str = "medium") -> str:
    """
    Returns the URL for the coaching phrase audio based on intensity.
    """
    phrases = COACHING_PHRASES.get(intent)
    if not phrases:
        return ""
        
    phrase = phrases.get(intensity, phrases.get("medium", ""))
    if not phrase:
        return ""
    
    safe_name = phrase.lower().replace(" ", "_").replace("'", "").replace(".", "").replace(",", "")
    return get_or_generate_audio(phrase, f"coach_{intent}_{intensity}_{safe_name[:10]}")
