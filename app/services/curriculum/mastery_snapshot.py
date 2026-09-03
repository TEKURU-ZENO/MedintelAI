"""
app/services/curriculum/mastery_snapshot.py — Educational Feature Vector

Condenses fragmented raw telemetries (sessions, feedback, analytics)
into a stable, curriculum-ready mastery snapshot.
"""

from typing import Dict, Any, List
from app.services.curriculum.mastery_engine import MasteryDimensions, compute_item_mastery

def build_mastery_snapshot(user_id: int, raw_session_history: List[Dict[str, Any]]) -> Dict[str, MasteryDimensions]:
    """
    In a real app, this queries the DB for all `PracticeSession` and `RecommendationFeedback`
    rows for the user, groups them by item, and computes the MasteryDimensions.
    
    For MVP, we expect the caller to pass grouped raw history.
    """
    
    # Group by item
    grouped_history: Dict[str, List[Dict[str, Any]]] = {}
    for session in raw_session_history:
        item = session.get("target_item")
        if not item:
            continue
        if item not in grouped_history:
            grouped_history[item] = []
        grouped_history[item].append(session)
        
    # Compute mastery per item
    snapshot: Dict[str, MasteryDimensions] = {}
    for item, history in grouped_history.items():
        snapshot[item] = compute_item_mastery(item, history)
        
    return snapshot

def get_mastered_nodes(snapshot: Dict[str, MasteryDimensions], threshold: float = 0.75) -> set[str]:
    """Returns a set of nodes/items that have achieved the minimum overall mastery."""
    mastered = set()
    for item, dims in snapshot.items():
        # Requires overall mastery AND confidence to prevent lucky unlocks
        if dims.get_overall_mastery() >= threshold and dims.confidence_mastery >= (threshold - 0.1):
            mastered.add(item)
    return mastered
