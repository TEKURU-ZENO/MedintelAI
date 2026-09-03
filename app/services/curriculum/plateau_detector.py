"""
app/services/curriculum/plateau_detector.py — Educational Plateau Detection

Identifies when a learner is stuck (high effort, stable/low accuracy).
Signals the orchestrator to switch teaching strategies.
"""

from typing import List, Dict, Any
from app.services.curriculum.mastery_engine import MasteryDimensions

def detect_learning_plateaus(snapshot: Dict[str, MasteryDimensions], recent_telemetry: List[Dict[str, Any]]) -> List[str]:
    """
    Returns a list of items where the user is experiencing a plateau.
    A plateau occurs when attempts are high/increasing, but mastery/accuracy is stable and below threshold.
    """
    plateau_items = []
    
    # Group recent telemetry by item
    attempts_by_item: Dict[str, int] = {}
    for t in recent_telemetry:
        item = t.get("target_item")
        if item:
            attempts_by_item[item] = attempts_by_item.get(item, 0) + 1
            
    for item, mastery in snapshot.items():
        if mastery.get_overall_mastery() > 0.8:
            continue # Mastered, not a plateau
            
        recent_attempts = attempts_by_item.get(item, 0)
        
        # If they've tried this item more than 5 times recently and confidence is high but mastery is low
        # This means they are consistently performing poorly (stable bad performance).
        if recent_attempts >= 5 and mastery.confidence_mastery > 0.6 and mastery.get_overall_mastery() < 0.6:
            plateau_items.append(item)
            
    return plateau_items
