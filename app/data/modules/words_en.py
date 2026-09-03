"""
app/data/modules/words_en.py — English Word Practice Data v1

Words are organized into three difficulty tiers:
  beginner     — 3-4 letter CVC words, high frequency, phonetically regular
  intermediate — 4-6 letter words, common but less phonetically obvious
  advanced     — 6+ letters, irregular spelling, tricky patterns

Each word entry:
  word          — the target word to write
  phonetic      — pronunciation guide (used in Phase 7 TTS)
  syllables     — syllable count (used for difficulty scoring)
  category      — semantic group (for thematic practice sets)

VERSION = "v1"
"""

VERSION = "v1"

WORDS: dict[str, list[dict]] = {
    "beginner": [
        {"word": "cat",   "phonetic": "kæt",    "syllables": 1, "category": "animals"},
        {"word": "dog",   "phonetic": "dɒɡ",    "syllables": 1, "category": "animals"},
        {"word": "sun",   "phonetic": "sʌn",    "syllables": 1, "category": "nature"},
        {"word": "run",   "phonetic": "rʌn",    "syllables": 1, "category": "actions"},
        {"word": "hat",   "phonetic": "hæt",    "syllables": 1, "category": "clothes"},
        {"word": "big",   "phonetic": "bɪɡ",    "syllables": 1, "category": "adjectives"},
        {"word": "map",   "phonetic": "mæp",    "syllables": 1, "category": "objects"},
        {"word": "cup",   "phonetic": "kʌp",    "syllables": 1, "category": "objects"},
        {"word": "bed",   "phonetic": "bɛd",    "syllables": 1, "category": "objects"},
        {"word": "fox",   "phonetic": "fɒks",   "syllables": 1, "category": "animals"},
        {"word": "box",   "phonetic": "bɒks",   "syllables": 1, "category": "objects"},
        {"word": "hen",   "phonetic": "hɛn",    "syllables": 1, "category": "animals"},
        {"word": "jam",   "phonetic": "dʒæm",   "syllables": 1, "category": "food"},
        {"word": "pen",   "phonetic": "pɛn",    "syllables": 1, "category": "objects"},
        {"word": "bus",   "phonetic": "bʌs",    "syllables": 1, "category": "transport"},
        {"word": "fish",  "phonetic": "fɪʃ",    "syllables": 1, "category": "animals"},
        {"word": "cake",  "phonetic": "keɪk",   "syllables": 1, "category": "food"},
        {"word": "milk",  "phonetic": "mɪlk",   "syllables": 1, "category": "food"},
        {"word": "tree",  "phonetic": "triː",   "syllables": 1, "category": "nature"},
        {"word": "frog",  "phonetic": "frɒɡ",   "syllables": 1, "category": "animals"},
    ],
    "intermediate": [
        {"word": "water",  "phonetic": "ˈwɔːtər",  "syllables": 2, "category": "nature"},
        {"word": "apple",  "phonetic": "ˈæpəl",    "syllables": 2, "category": "food"},
        {"word": "happy",  "phonetic": "ˈhæpi",    "syllables": 2, "category": "adjectives"},
        {"word": "flower", "phonetic": "ˈflaʊər",  "syllables": 2, "category": "nature"},
        {"word": "pencil", "phonetic": "ˈpɛnsɪl",  "syllables": 2, "category": "objects"},
        {"word": "orange", "phonetic": "ˈɒrɪndʒ",  "syllables": 2, "category": "food"},
        {"word": "garden", "phonetic": "ˈɡɑːrdən", "syllables": 2, "category": "places"},
        {"word": "butter", "phonetic": "ˈbʌtər",   "syllables": 2, "category": "food"},
        {"word": "window", "phonetic": "ˈwɪndoʊ",  "syllables": 2, "category": "objects"},
        {"word": "rabbit", "phonetic": "ˈræbɪt",   "syllables": 2, "category": "animals"},
        {"word": "family", "phonetic": "ˈfæmɪli",  "syllables": 3, "category": "people"},
        {"word": "purple", "phonetic": "ˈpɜːrpəl", "syllables": 2, "category": "colors"},
        {"word": "jungle", "phonetic": "ˈdʒʌŋɡəl", "syllables": 2, "category": "nature"},
        {"word": "bottle", "phonetic": "ˈbɒtəl",   "syllables": 2, "category": "objects"},
        {"word": "monkey", "phonetic": "ˈmʌŋki",   "syllables": 2, "category": "animals"},
        {"word": "candle", "phonetic": "ˈkændəl",  "syllables": 2, "category": "objects"},
        {"word": "gentle", "phonetic": "ˈdʒɛntəl", "syllables": 2, "category": "adjectives"},
        {"word": "castle", "phonetic": "ˈkɑːsəl",  "syllables": 2, "category": "places"},
        {"word": "mirror", "phonetic": "ˈmɪrər",   "syllables": 2, "category": "objects"},
        {"word": "school",  "phonetic": "skuːl",   "syllables": 1, "category": "places"},
    ],
    "advanced": [
        {"word": "beautiful",   "phonetic": "ˈbjuːtɪfəl",  "syllables": 4, "category": "adjectives"},
        {"word": "Wednesday",   "phonetic": "ˈwɛnzdeɪ",    "syllables": 3, "category": "time"},
        {"word": "necessary",   "phonetic": "ˈnɛsɪsəri",   "syllables": 4, "category": "adjectives"},
        {"word": "knowledge",   "phonetic": "ˈnɒlɪdʒ",     "syllables": 2, "category": "concepts"},
        {"word": "parliament",  "phonetic": "ˈpɑːrləmənt",  "syllables": 3, "category": "government"},
        {"word": "February",    "phonetic": "ˈfɛbrʊəri",   "syllables": 4, "category": "time"},
        {"word": "dictionary",  "phonetic": "ˈdɪkʃənəri",  "syllables": 4, "category": "objects"},
        {"word": "environment", "phonetic": "ɪnˈvaɪrənmənt", "syllables": 4, "category": "nature"},
        {"word": "extraordinary", "phonetic": "ɪkˈstrɔːrdɪnəri", "syllables": 6, "category": "adjectives"},
        {"word": "conscience",  "phonetic": "ˈkɒnʃəns",    "syllables": 3, "category": "concepts"},
        {"word": "lieutenant",  "phonetic": "lɛfˈtɛnənt",  "syllables": 3, "category": "people"},
        {"word": "maintenance", "phonetic": "ˈmeɪntənəns",  "syllables": 3, "category": "concepts"},
        {"word": "millennium",  "phonetic": "mɪˈlɛniəm",   "syllables": 4, "category": "time"},
        {"word": "occurrence",  "phonetic": "əˈkʌrəns",    "syllables": 3, "category": "concepts"},
        {"word": "privilege",   "phonetic": "ˈprɪvɪlɪdʒ",  "syllables": 3, "category": "concepts"},
    ],
}


def get_words(difficulty: str = "beginner") -> list[dict]:
    """Return word list for a given difficulty. Includes version metadata."""
    if difficulty not in WORDS:
        raise KeyError(f"Difficulty '{difficulty}' not found. "
                       f"Available: {list(WORDS.keys())}")
    return [{"version": VERSION, **w} for w in WORDS[difficulty]]


def get_word(word: str) -> dict | None:
    """Find a word entry across all difficulties."""
    for tier in WORDS.values():
        for entry in tier:
            if entry["word"].lower() == word.lower():
                return {"version": VERSION, **entry}
    return None


def get_random_words(difficulty: str, count: int = 5) -> list[dict]:
    """Return a random subset of words for a practice session."""
    import random
    pool = get_words(difficulty)
    return random.sample(pool, min(count, len(pool)))
