"""
app/services/spelling/word_packs.py — Word Curriculum Definitions

Defines structured word metadata to power adaptive recommendations,
curriculum sequencing, and literacy progression.
"""

from typing import Dict, Any, List

WORD_PACKS: Dict[str, Dict[str, Any]] = {
    "CAT": {
        "word": "CAT",
        "difficulty": 1,
        "phonics": "simple_cvc",
        "stroke_complexity": "low",
        "focus_letters": ["C", "A"],
        "category": "animals"
    },
    "DOG": {
        "word": "DOG",
        "difficulty": 1,
        "phonics": "simple_cvc",
        "stroke_complexity": "low",
        "focus_letters": ["D", "G"],
        "category": "animals"
    },
    "SUN": {
        "word": "SUN",
        "difficulty": 1,
        "phonics": "simple_cvc",
        "stroke_complexity": "medium",
        "focus_letters": ["S", "U"],
        "category": "nature"
    },
    "BALL": {
        "word": "BALL",
        "difficulty": 2,
        "phonics": "double_consonant",
        "stroke_complexity": "medium",
        "focus_letters": ["B", "L"],
        "category": "objects"
    },
    "APPLE": {
        "word": "APPLE",
        "difficulty": 3,
        "phonics": "vowel_team",
        "stroke_complexity": "high",
        "focus_letters": ["P", "E"],
        "category": "food"
    }
}

def get_words_by_difficulty(max_difficulty: int) -> List[Dict[str, Any]]:
    return [w for w in WORD_PACKS.values() if w["difficulty"] <= max_difficulty]

def get_word_metadata(word: str) -> Dict[str, Any] | None:
    return WORD_PACKS.get(word.upper())
