"""
app/services/audio/pronunciation_service.py — Pronunciation Engine

Handles generating the correct phonetic sound for letters and words.
"""

from app.services.audio.phonetic_mapper import get_letter_metadata, get_word_metadata
from app.services.audio.audio_cache import get_or_generate_audio

def get_item_pronunciation_url(item: str) -> str:
    """
    Returns the URL for the item's pronunciation audio.
    If it's a single letter, it uses the phonetic spelling.
    If it's a word, it just speaks the word.
    """
    if len(item) == 1:
        meta = get_letter_metadata(item)
        # To get a clear pronunciation of a letter, sometimes spelling it out phonetically 
        # or just passing the letter itself works best. We will use the phonetic field.
        # But wait, gTTS handles single letters fine (e.g. "A"). Let's try just the letter,
        # fallback to phonetic if we want to be explicit.
        text_to_speak = item.upper() 
        filename = meta["audio_key"]
    else:
        meta = get_word_metadata(item)
        text_to_speak = item.lower()
        filename = meta["audio_key"]

    return get_or_generate_audio(text_to_speak, filename)
