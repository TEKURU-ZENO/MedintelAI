"""
app/services/spelling/assist_profiles.py — Assist Levels

Determines spelling hints and assistance level based on the user's
learning style and age profile.
"""

from typing import Dict, Any

def get_assist_profile(learning_style: str, profile_type: str = "child") -> Dict[str, Any]:
    """
    Returns assistance parameters.
    - early_learner / replay_dependent: highly assisted (shows next letter ghost, auto-repeats word).
    - methodical: minimal hints, lets them figure it out.
    - visual: always shows the ghost target.
    """
    is_early = profile_type == "early_learner"
    
    assist = {
        "show_ghost_word": is_early or learning_style == "visual",
        "show_next_letter_hint": is_early or learning_style == "replay_dependent",
        "auto_repeat_pronunciation": learning_style == "replay_dependent",
        "forgiveness_level": "high" if is_early else "medium"
    }
    
    if learning_style == "methodical":
        assist["show_next_letter_hint"] = False
        assist["auto_repeat_pronunciation"] = False
        
    return assist
