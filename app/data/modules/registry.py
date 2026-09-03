"""
app/data/modules/registry.py — Module Registry

Single source of truth for every available learning module.
Static config — not stored in DB. Modules are versioned so ML training
datasets can be traced back to the exact data version used.

To add a new module: add an entry here + create a data file.
"""

from typing import TypedDict


class ModuleDefinition(TypedDict):
    label: str
    description: str
    icon: str
    difficulty_levels: list[str]
    profile_types: list[str]    # which profile types can access this
    languages: list[str]
    xp_per_session: int         # base XP for a completed session
    data_file: str | None       # import path for the data module
    version: str


MODULES: dict[str, ModuleDefinition] = {
    "alphabet_practice": {
        "label": "Alphabet Practice",
        "description": "Trace and perfect individual letters",
        "icon": "🔤",
        "difficulty_levels": ["beginner", "intermediate", "advanced"],
        "profile_types": ["early_learner", "child", "adult"],
        "languages": ["english"],
        "xp_per_session": 10,
        "data_file": "app.data.modules.alphabet_en",
        "version": "v1",
    },
    "word_practice": {
        "label": "Word Practice",
        "description": "Write and analyze common words",
        "icon": "📖",
        "difficulty_levels": ["beginner", "intermediate", "advanced"],
        "profile_types": ["child", "adult"],
        "languages": ["english"],
        "xp_per_session": 15,
        "data_file": "app.data.modules.words_en",
        "version": "v1",
    },
    "sentence_practice": {
        "label": "Sentence Practice",
        "description": "Full sentence formation and consistency",
        "icon": "✏️",
        "difficulty_levels": ["intermediate", "advanced"],
        "profile_types": ["child", "adult"],
        "languages": ["english"],
        "xp_per_session": 20,
        "data_file": None,      # Phase 3
        "version": "v1",
    },
    "shape_practice": {
        "label": "Shape Practice",
        "description": "Draw circles, lines, curves — build motor control",
        "icon": "⭕",
        "difficulty_levels": ["beginner"],
        "profile_types": ["early_learner", "child"],
        "languages": ["english"],
        "xp_per_session": 8,
        "data_file": None,      # Phase 3
        "version": "v1",
    },
    "pronunciation_practice": {
        "label": "Pronunciation Practice",
        "description": "Hear the word, then write it",
        "icon": "🎵",
        "difficulty_levels": ["beginner", "intermediate"],
        "profile_types": ["early_learner", "child", "adult"],
        "languages": ["english"],
        "xp_per_session": 12,
        "data_file": None,      # Phase 7
        "version": "v1",
    },
    "spell_correction": {
        "label": "Spell Correction",
        "description": "Identify and fix common misspellings",
        "icon": "🔍",
        "difficulty_levels": ["intermediate", "advanced"],
        "profile_types": ["child", "adult"],
        "languages": ["english"],
        "xp_per_session": 15,
        "data_file": None,      # Phase 8
        "version": "v1",
    },
    "free_draw": {
        "label": "Free Draw",
        "description": "Draw anything freely — no guidance",
        "icon": "🎨",
        "difficulty_levels": ["beginner"],
        "profile_types": ["early_learner", "child", "adult"],
        "languages": ["english"],
        "xp_per_session": 5,
        "data_file": None,      # no data file needed
        "version": "v1",
    },
}


def get_module(module_type: str) -> ModuleDefinition:
    """Retrieve a module definition. Raises KeyError if not found."""
    if module_type not in MODULES:
        raise KeyError(f"Unknown module: '{module_type}'. "
                       f"Available: {list(MODULES.keys())}")
    return MODULES[module_type]


def get_modules_for_profile(profile_type: str) -> list[dict]:
    """Return all modules accessible to a given profile type."""
    return [
        {"module_type": key, **mod}
        for key, mod in MODULES.items()
        if profile_type in mod["profile_types"]
    ]
