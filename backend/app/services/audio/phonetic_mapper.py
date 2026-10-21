"""
app/services/audio/phonetic_mapper.py — Literacy Abstraction Layer

Central registry mapping characters and words to their educational
metadata, phonetics, difficulty, and audio keys.
"""

from typing import Dict, Any

# Future-proof literacy abstraction
ALPHABET_MAP: Dict[str, Dict[str, Any]] = {
    "A": {"symbol": "A", "phonetic": "ay", "category": "vowel", "difficulty": 1, "stroke_type": "angular", "audio_key": "letter_a"},
    "B": {"symbol": "B", "phonetic": "bee", "category": "consonant", "difficulty": 2, "stroke_type": "curved", "audio_key": "letter_b"},
    "C": {"symbol": "C", "phonetic": "see", "category": "consonant", "difficulty": 1, "stroke_type": "curved", "audio_key": "letter_c"},
    "D": {"symbol": "D", "phonetic": "dee", "category": "consonant", "difficulty": 2, "stroke_type": "mixed", "audio_key": "letter_d"},
    "E": {"symbol": "E", "phonetic": "ee", "category": "vowel", "difficulty": 1, "stroke_type": "angular", "audio_key": "letter_e"},
    "F": {"symbol": "F", "phonetic": "eff", "category": "consonant", "difficulty": 2, "stroke_type": "angular", "audio_key": "letter_f"},
    "G": {"symbol": "G", "phonetic": "jee", "category": "consonant", "difficulty": 3, "stroke_type": "curved", "audio_key": "letter_g"},
    "H": {"symbol": "H", "phonetic": "aych", "category": "consonant", "difficulty": 2, "stroke_type": "angular", "audio_key": "letter_h"},
    "I": {"symbol": "I", "phonetic": "eye", "category": "vowel", "difficulty": 1, "stroke_type": "straight", "audio_key": "letter_i"},
    "J": {"symbol": "J", "phonetic": "jay", "category": "consonant", "difficulty": 2, "stroke_type": "curved", "audio_key": "letter_j"},
    "K": {"symbol": "K", "phonetic": "kay", "category": "consonant", "difficulty": 3, "stroke_type": "angular", "audio_key": "letter_k"},
    "L": {"symbol": "L", "phonetic": "ell", "category": "consonant", "difficulty": 1, "stroke_type": "angular", "audio_key": "letter_l"},
    "M": {"symbol": "M", "phonetic": "em", "category": "consonant", "difficulty": 3, "stroke_type": "angular", "audio_key": "letter_m"},
    "N": {"symbol": "N", "phonetic": "en", "category": "consonant", "difficulty": 2, "stroke_type": "angular", "audio_key": "letter_n"},
    "O": {"symbol": "O", "phonetic": "oh", "category": "vowel", "difficulty": 1, "stroke_type": "curved", "audio_key": "letter_o"},
    "P": {"symbol": "P", "phonetic": "pee", "category": "consonant", "difficulty": 2, "stroke_type": "mixed", "audio_key": "letter_p"},
    "Q": {"symbol": "Q", "phonetic": "cue", "category": "consonant", "difficulty": 3, "stroke_type": "mixed", "audio_key": "letter_q"},
    "R": {"symbol": "R", "phonetic": "ar", "category": "consonant", "difficulty": 2, "stroke_type": "mixed", "audio_key": "letter_r"},
    "S": {"symbol": "S", "phonetic": "ess", "category": "consonant", "difficulty": 3, "stroke_type": "curved", "audio_key": "letter_s"},
    "T": {"symbol": "T", "phonetic": "tee", "category": "consonant", "difficulty": 1, "stroke_type": "straight", "audio_key": "letter_t"},
    "U": {"symbol": "U", "phonetic": "you", "category": "vowel", "difficulty": 2, "stroke_type": "curved", "audio_key": "letter_u"},
    "V": {"symbol": "V", "phonetic": "vee", "category": "consonant", "difficulty": 1, "stroke_type": "angular", "audio_key": "letter_v"},
    "W": {"symbol": "W", "phonetic": "double_u", "category": "consonant", "difficulty": 3, "stroke_type": "angular", "audio_key": "letter_w"},
    "X": {"symbol": "X", "phonetic": "ex", "category": "consonant", "difficulty": 2, "stroke_type": "angular", "audio_key": "letter_x"},
    "Y": {"symbol": "Y", "phonetic": "why", "category": "consonant", "difficulty": 2, "stroke_type": "mixed", "audio_key": "letter_y"},
    "Z": {"symbol": "Z", "phonetic": "zee", "category": "consonant", "difficulty": 1, "stroke_type": "angular", "audio_key": "letter_z"},
}

def get_letter_metadata(letter: str) -> Dict[str, Any]:
    return ALPHABET_MAP.get(letter.upper(), {
        "symbol": letter.upper(),
        "phonetic": letter.upper(),
        "category": "unknown",
        "difficulty": 1,
        "stroke_type": "unknown",
        "audio_key": f"item_{letter.lower()}"
    })

def get_word_metadata(word: str) -> Dict[str, Any]:
    # Placeholder for word metadata scaling
    return {
        "symbol": word.upper(),
        "phonetic": word.lower(),
        "category": "word",
        "difficulty": len(word),
        "audio_key": f"word_{word.lower()}"
    }
