"""
app/services/spelling/spelling_feedback.py — Micro-dopamine Feedback

Provides encouragement strings for partial successes and state transitions
during the spelling pipeline.
"""

from typing import Dict

def get_spelling_feedback(state: str, letter: str = "") -> Dict[str, str]:
    if state == "partial_success":
        return {
            "type": "encouragement",
            "message": f"Great! You got '{letter}'. Keep going!",
            "intent": "celebrate_minor"
        }
    elif state == "retrying":
        return {
            "type": "correction",
            "message": "Not quite! Let's try tracing the next letter.",
            "intent": "wrong_way"
        }
    elif state == "correct":
        return {
            "type": "celebration",
            "message": "Perfect! You spelled the word!",
            "intent": "celebrate_strong"
        }
    return {
        "type": "idle",
        "message": "Trace the word.",
        "intent": "idle"
    }
