"""
app/services/curriculum/progression_rules.py — Confidence Gating

Implements consistency thresholds and minimum session requirements
to prevent premature curriculum unlocks.
"""

from typing import Dict, List, Any
from app.services.curriculum.mastery_engine import MasteryDimensions

def meets_confidence_gate(
    item: str, 
    mastery: MasteryDimensions, 
    raw_history: List[Dict[str, Any]], 
    min_sessions: int = 3, 
    threshold: float = 0.75
) -> bool:
    """
    Evaluates if an item passes the confidence gate.
    Requires minimum sessions AND consistent performance above threshold.
    """
    
    # 1. Base mastery checks
    if mastery.get_overall_mastery() < threshold:
        return False
        
    if mastery.confidence_mastery < (threshold - 0.1):
        return False
        
    # 2. Extract specific item history
    item_history = [h for h in raw_history if h.get("target_item") == item]
    
    # 3. Minimum sessions check
    if len(item_history) < min_sessions:
        return False
        
    # 4. Consistency check: last N sessions must all individually meet a minimum bar
    recent = sorted(item_history, key=lambda x: x.get("timestamp", ""))[-min_sessions:]
    
    for session in recent:
        # Require at least 0.6 in each individual session to prove it wasn't a fluke
        if session.get("accuracy", 0) < 0.6:
            return False
            
    return True
