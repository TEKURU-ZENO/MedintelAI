"""
app/services/spelling/literacy_orchestrator.py — The Educational Workflow Coordinator

Coordinates:
- Pronunciation (Phase 6.1)
- Coaching Audio (Phase 6.2)
- Spelling Curriculum & Assist Profiles (Phase 6.3)

Bundles the configuration needed by `WordModule.tsx` so the frontend simply
renders the state machine without performing the educational cognition.
"""

from typing import Dict, Any
from app.services.spelling.word_packs import get_word_metadata
from app.services.spelling.assist_profiles import get_assist_profile
from app.services.audio.pronunciation_service import get_item_pronunciation_url
from app.services.audio.coaching_policy import get_coaching_policy
from app.services.audio.coaching_audio_service import COACHING_PHRASES, get_coaching_audio_url

def generate_literacy_session_config(word: str, learning_style: str, profile_type: str = "child") -> Dict[str, Any]:
    """
    Returns the complete orchestration payload for a spelling session.
    """
    word_meta = get_word_metadata(word)
    if not word_meta:
        word_meta = {
            "word": word.upper(),
            "difficulty": 1,
            "focus_letters": list(word.upper()),
            "stroke_complexity": "unknown"
        }
        
    assist = get_assist_profile(learning_style, profile_type)
    policy = get_coaching_policy(learning_style, "low")  # default frustration to low at start
    
    # Pre-compute audio
    audio_map = {
        "word": get_item_pronunciation_url(word_meta["word"]),
        "letters": {ch: get_item_pronunciation_url(ch) for ch in word_meta["word"]}
    }
    
    # Pre-compute some coaching phrases specific to spelling
    intensity = policy["intensity"]
    coach_audio = {
        "wrong_way": get_coaching_audio_url("wrong_way", intensity),
        "celebrate_minor": get_coaching_audio_url("celebrate_minor", "low"), # generic
        "celebrate_strong": get_coaching_audio_url("celebrate_strong", "high")
    }

    return {
        "word_metadata": word_meta,
        "assist_profile": assist,
        "coaching_policy": policy,
        "audio": {
            "pronunciations": audio_map,
            "coach_audio": coach_audio
        }
    }
