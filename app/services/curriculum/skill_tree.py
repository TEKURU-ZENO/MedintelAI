"""
app/services/curriculum/skill_tree.py — Educational Skill Tree

Defines the core learning domains and milestones. 
Tracks progression across multiple dimensions rather than just linear tracing.
"""

from typing import Dict, Any

LEARNING_DOMAINS = {
    "motor_control": {
        "description": "Basic fine motor skills and tracing accuracy.",
        "levels": ["lines", "curves", "complex_shapes"]
    },
    "phonics": {
        "description": "Sound-to-symbol association.",
        "levels": ["vowels", "consonants", "blends", "digraphs"]
    },
    "spelling": {
        "description": "Sequential memory and word construction.",
        "levels": ["cvc_words", "sight_words", "complex_words"]
    },
    "sequencing": {
        "description": "Understanding directionality and order of strokes/letters.",
        "levels": ["stroke_order", "letter_order"]
    }
}

SKILL_MILESTONES = [
    {"id": "milestone_1", "name": "Basic Lines & Vowels", "required_domains": {"motor_control": "lines", "phonics": "vowels"}},
    {"id": "milestone_2", "name": "Curved Letters", "required_domains": {"motor_control": "curves"}},
    {"id": "milestone_3", "name": "CVC Words", "required_domains": {"phonics": "consonants", "spelling": "cvc_words", "sequencing": "letter_order"}},
]

def get_domain_info(domain_id: str) -> Dict[str, Any] | None:
    return LEARNING_DOMAINS.get(domain_id)
