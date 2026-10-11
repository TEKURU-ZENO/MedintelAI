"""
app/services/curriculum/learning_journey_engine.py — The Educational Planner

The top-level journey orchestrator. Reads user profile, mastery snapshot,
and educational state to generate a structured `LearningJourney`.
"""

from typing import Dict, Any, List
from app.services.curriculum.mastery_snapshot import build_mastery_snapshot
from app.services.curriculum.educational_state_engine import compute_educational_state
from app.services.curriculum.curriculum_graph import CurriculumGraph
from app.services.curriculum.progression_rules import meets_confidence_gate
from app.services.curriculum.review_scheduler import get_due_review_items

def generate_learning_journey(user_id: int, raw_session_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generates the high-level educational state and curriculum goals.
    """
    
    # 1. Build Snapshot & State
    snapshot = build_mastery_snapshot(user_id, raw_session_history)
    edu_state = compute_educational_state(snapshot, raw_session_history)
    
    # 2. Extract Mastered Nodes (using confidence gating)
    mastered_nodes = set()
    for item, mastery in snapshot.items():
        if meets_confidence_gate(item, mastery, raw_session_history):
            mastered_nodes.add(item)
            
    # 3. Curriculum Graph Resolution
    graph = CurriculumGraph()
    available_unlocks = graph.get_available_nodes(mastered_nodes)
    
    # 4. Spaced Repetition Requirements
    due_reviews = get_due_review_items(snapshot, edu_state["frustration_trend"])
    
    # 5. Focus Mode & Strategy selection
    focus_mode = "standard_progression"
    recommended_domains = ["motor_control"] # Default MVP domain
    
    if edu_state["readiness"] == "fatigued":
        focus_mode = "light_review"
        available_unlocks = [] # Disable new content when fatigued
    elif edu_state["plateaus"]:
        focus_mode = "plateau_breakthrough"
        # Force review of plateaus
        due_reviews = list(set(due_reviews + edu_state["plateaus"]))
    elif edu_state["frustration_trend"] == "high":
        focus_mode = "confidence_rebuild"
        available_unlocks = [] # Disable new content when frustrated
        
    return {
        "focus_mode": focus_mode,
        "recommended_domains": recommended_domains,
        "review_items": due_reviews,
        "new_unlocks": available_unlocks,
        "educational_state": edu_state,
        "mastery_snapshot": {item: m.to_dict() for item, m in snapshot.items()}
    }
