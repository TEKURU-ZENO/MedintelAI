"""
app/services/audio/audio_cache.py — Caching Engine

Generates and stores MP3s via gTTS so we never request
the same audio clip from the network twice.
"""

import os
from gtts import gTTS
import threading

AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)

# Simple lock to prevent parallel generation of the same file
_lock = threading.Lock()

def get_or_generate_audio(text_to_speak: str, filename: str) -> str:
    """
    Checks if audio file exists. If not, generates it via gTTS.
    Returns the relative URL path (e.g., '/audio/letter_a.mp3').
    """
    if not filename.endswith(".mp3"):
        filename += ".mp3"
        
    filepath = os.path.join(AUDIO_DIR, filename)
    url_path = f"/audio/{filename}"

    with _lock:
        if os.path.exists(filepath):
            return url_path

        try:
            tts = gTTS(text=text_to_speak, lang="en", slow=False)
            tts.save(filepath)
            return url_path
        except Exception as e:
            print(f"[AudioCache] Failed to generate audio for {filename}: {e}")
            return ""
