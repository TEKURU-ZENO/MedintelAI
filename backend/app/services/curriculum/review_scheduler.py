"""
app/services/curriculum/review_scheduler.py — Spaced Repetition System

Schedules items for review using time, confidence, frustration, and mastery stability.
"""

from typing import List, Dict, Any
from datetime import datetime
from app.services.curriculum.mastery_engine import MasteryDimensions

def get_due_review_items(mastery_data: Dict[str, MasteryDimensions], frustration_trend: str) -> List[str]:
    """
    Evaluates all known items and returns a list of items that require review today.
    """
    due_items = []
    now = datetime.utcnow()
    
    for item, mastery in mastery_data.items():
        if not mastery.last_seen:
            continue
            
        try:
            last_seen = datetime.fromisoformat(mastery.last_seen.replace("Z", "+00:00"))
            # remove tzinfo for safe subtraction if both are naive/aware
            last_seen = last_seen.replace(tzinfo=None)
            days_elapsed = (now - last_seen).days
        except Exception:
            days_elapsed = 0
            
        # 1. High instability or low confidence → aggressive review (1 day)
        if mastery.confidence_mastery < 0.5 or mastery.get_overall_mastery() < 0.6:
            if days_elapsed >= 1:
                due_items.append(item)
            continue
            
        # 2. Medium mastery → standard spaced repetition (3 days)
        if mastery.get_overall_mastery() < 0.8:
            if days_elapsed >= 3:
                due_items.append(item)
            continue
            
        # 3. High mastery but high global frustration → pull back to easy review items for confidence boost
        if frustration_trend == "high" and days_elapsed >= 2:
            due_items.append(item)
            continue
            
        # 4. Mastery maintenance (7+ days)
        if days_elapsed >= 7:
            due_items.append(item)

    return due_items
