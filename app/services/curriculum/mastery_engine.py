"""
app/services/curriculum/mastery_engine.py — Multi-Dimensional Mastery

Computes mastery across motor, cognitive, retention, and confidence dimensions.
Applies time-based decay to simulate real retention modeling.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta

class MasteryDimensions:
    def __init__(self, item: str, motor: float, cognitive: float, retention: float, confidence: float, last_seen: str):
        self.item = item
        self.motor_mastery = motor
        self.cognitive_mastery = cognitive
        self.retention_mastery = retention
        self.confidence_mastery = confidence
        self.last_seen = last_seen

    def get_overall_mastery(self) -> float:
        # Weighted average. Motor and cognitive are primary.
        return (self.motor_mastery * 0.4) + (self.cognitive_mastery * 0.3) + (self.retention_mastery * 0.2) + (self.confidence_mastery * 0.1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item,
            "motor_mastery": round(self.motor_mastery, 3),
            "cognitive_mastery": round(self.cognitive_mastery, 3),
            "retention_mastery": round(self.retention_mastery, 3),
            "confidence_mastery": round(self.confidence_mastery, 3),
            "overall_mastery": round(self.get_overall_mastery(), 3),
            "last_seen": self.last_seen
        }

def decay_mastery(mastery_score: float, last_seen_date: str) -> float:
    """
    Applies an Ebbinghaus-style forgetting curve decay based on days since last practice.
    """
    if not last_seen_date:
        return mastery_score
        
    try:
        last_seen = datetime.fromisoformat(last_seen_date.replace("Z", "+00:00"))
        days_elapsed = (datetime.utcnow().replace(tzinfo=last_seen.tzinfo) - last_seen).days
    except Exception:
        return mastery_score

    if days_elapsed <= 1:
        return mastery_score
        
    # Simple decay: loses roughly 5% per day unpracticed, capping at 0.3 loss.
    decay_factor = min(0.3, (days_elapsed - 1) * 0.05)
    return max(0.0, mastery_score - decay_factor)

def compute_item_mastery(item: str, raw_history: List[Dict[str, Any]]) -> MasteryDimensions:
    """
    Condenses a list of historical sessions into multi-dimensional mastery.
    """
    if not raw_history:
        return MasteryDimensions(item, 0.0, 0.0, 0.0, 0.0, "")
        
    # Sort history chronological
    history = sorted(raw_history, key=lambda x: x.get("timestamp", ""))
    
    # 1. Motor Mastery: based purely on trace accuracy scores.
    motor = sum(h.get("accuracy", 0) for h in history[-3:]) / min(3, len(history))
    
    # 2. Cognitive Mastery: based on hesitation, hints used, or spelling accuracy.
    # Proxy: accuracy * (1 - retry_rate)
    cognitive = sum(h.get("cognitive_score", h.get("accuracy", 0)) for h in history[-3:]) / min(3, len(history))
    
    # 3. Retention Mastery: heavily weighted by performance after a delay.
    retention = cognitive * 0.8  # MVP proxy
    
    # 4. Confidence Mastery: based on consistency (low variance).
    accuracies = [h.get("accuracy", 0) for h in history[-5:]]
    if len(accuracies) > 1:
        mean_acc = sum(accuracies) / len(accuracies)
        variance = sum((a - mean_acc)**2 for a in accuracies) / len(accuracies)
        confidence = max(0.0, mean_acc - (variance * 2))
    else:
        confidence = accuracies[0] if accuracies else 0.0
        
    last_seen = history[-1].get("timestamp", datetime.utcnow().isoformat())
    
    # Apply decay
    motor = decay_mastery(motor, last_seen)
    cognitive = decay_mastery(cognitive, last_seen)
    retention = decay_mastery(retention, last_seen)
    
    return MasteryDimensions(item, motor, cognitive, retention, confidence, last_seen)
