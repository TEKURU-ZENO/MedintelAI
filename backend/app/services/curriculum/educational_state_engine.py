"""
app/services/curriculum/educational_state_engine.py — Unified Educational State

Computes learning fatigue, global confidence, retention, mastery stability,
frustration trend, and readiness. This is the brain of the platform.
"""

from typing import Dict, Any, List
from app.services.curriculum.mastery_engine import MasteryDimensions
from app.services.curriculum.plateau_detector import detect_learning_plateaus

def compute_educational_state(
    snapshot: Dict[str, MasteryDimensions],
    recent_telemetry: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes a high-level educational state from the raw snapshot and recent telemetry.
    """
    
    # 1. Global Confidence & Stability
    if snapshot:
        avg_confidence = sum(m.confidence_mastery for m in snapshot.values()) / len(snapshot)
        avg_retention = sum(m.retention_mastery for m in snapshot.values()) / len(snapshot)
    else:
        avg_confidence = 0.0
        avg_retention = 0.0
        
    # 2. Frustration Trend
    frustration_count = sum(1 for t in recent_telemetry if t.get("hesitation_ms", 0) > 3000 or t.get("failsafe_used", False))
    if frustration_count > len(recent_telemetry) * 0.3:
        frustration_trend = "high"
    elif frustration_count > len(recent_telemetry) * 0.15:
        frustration_trend = "medium"
    else:
        frustration_trend = "low"
        
    # 3. Learning Fatigue (Proxy: how many sessions today + frustration)
    sessions_today = len([t for t in recent_telemetry if "today" in t.get("timestamp", "today")]) # MVP proxy
    estimated_fatigue = min(1.0, (sessions_today * 0.1) + (0.3 if frustration_trend == "high" else 0.0))
    
    # 4. Plateau Detection
    plateaus = detect_learning_plateaus(snapshot, recent_telemetry)
    
    # 5. Readiness
    readiness = "ready"
    if estimated_fatigue > 0.8:
        readiness = "fatigued"
    elif plateaus:
        readiness = "frustrated"

    return {
        "global_confidence": round(avg_confidence, 3),
        "global_retention": round(avg_retention, 3),
        "frustration_trend": frustration_trend,
        "estimated_fatigue": round(estimated_fatigue, 3),
        "plateaus": plateaus,
        "readiness": readiness
    }
