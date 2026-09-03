"""
app/services/audio/coaching_event_mapper.py — Declarative Audio Events

Maps practice events/states to specific audio keys, prioritizing
and defining interruption rules.
"""

from typing import Dict, Any

# Map of abstract guidance events to audio intents
EVENT_TO_AUDIO_MAP: Dict[str, Dict[str, Any]] = {
    "session_start": {
        "intent": "welcome",
        "priority": 1,
        "interrupt": False,
        "cooldown_ms": 0,
        "max_repeats": 1
    },
    "stroke_start": {
        "intent": "start_top",
        "priority": 1,
        "interrupt": False,
        "cooldown_ms": 10000,
        "max_repeats": 3
    },
    "direction_failure": {
        "intent": "wrong_way",
        "priority": 2,
        "interrupt": True,
        "cooldown_ms": 4000,
        "max_repeats": 2
    },
    "off_path": {
        "intent": "stay_on_line",
        "priority": 2,
        "interrupt": False,
        "cooldown_ms": 5000,
        "max_repeats": 3
    },
    "failsafe_triggered": {
        "intent": "watch_carefully",
        "priority": 3,
        "interrupt": True,
        "cooldown_ms": 8000,
        "max_repeats": 2
    },
    "success_minor": {
        "intent": "celebrate_minor",
        "priority": 1,
        "interrupt": False,
        "cooldown_ms": 0,
        "max_repeats": 99
    },
    "success_strong": {
        "intent": "celebrate_strong",
        "priority": 2,
        "interrupt": True,
        "cooldown_ms": 0,
        "max_repeats": 99
    }
}

def get_event_audio_config(event_name: str) -> Dict[str, Any]:
    """Returns the declarative audio configuration for an event."""
    return EVENT_TO_AUDIO_MAP.get(event_name, {})
