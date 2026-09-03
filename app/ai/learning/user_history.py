import os
import json
from typing import Dict, Any, List
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class UserHistoryManager:
    def __init__(self, history_file: str = "outputs/user_history.json"):
        self.history_file = history_file
        self.history_data = self._load_history()
        
    def _load_history(self) -> Dict[str, Any]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.error(f"Failed to decode {self.history_file}. Starting fresh.")
                return {}
        return {}
        
    def _save_history(self):
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
        with open(self.history_file, 'w') as f:
            json.dump(self.history_data, f, indent=2)
            
    def update_history_and_smooth_score(self, user_id: str, new_score: float, timestamp: str) -> Dict[str, Any]:
        """
        Updates user history, computes smoothed score, and returns attempt comparison.
        """
        if user_id not in self.history_data:
            self.history_data[user_id] = {"scores": [], "timestamps": []}
            
        user_record = self.history_data[user_id]
        past_scores = user_record["scores"]
        
        # 1. Calibrate Score (Spread distribution)
        calibrated_score = self._calibrate_score(new_score)
        
        improvement_msg = None
        is_improvement = False
        
        # Compare with last score if it exists
        MIN_DELTA = 3.0
        if past_scores:
            last_score = past_scores[-1]
            if new_score > last_score + MIN_DELTA:
                is_improvement = True
                improvement_msg = f"Great improvement! You scored {new_score:.1f}, up from {last_score:.1f}."
                
        # Update history with calibrated score
        user_record["scores"].append(calibrated_score)
        user_record["timestamps"].append(timestamp)
        self._save_history()
        
        # Calculate smoothed score (window of 3)
        window = min(len(user_record["scores"]), 3)
        recent_scores = user_record["scores"][-window:]
        smoothed_score = sum(recent_scores) / window
        
        return {
            "smoothed_score": smoothed_score,
            "calibrated_score": calibrated_score,
            "is_improvement": is_improvement,
            "improvement_message": improvement_msg
        }

    def _calibrate_score(self, new_score: float) -> float:
        """Light calibration to spread scores across a wider band."""
        all_scores = []
        for user_data in self.history_data.values():
            all_scores.extend(user_data.get("scores", []))
            
        all_scores.append(new_score)
        
        if len(all_scores) < 5:
            return new_score
            
        min_score = min(all_scores)
        max_score = max(all_scores)
        
        if max_score - min_score < 10:
            return new_score # Too narrow
            
        # Map [min_score, max_score] to [40, 100]
        mapped = 40.0 + (new_score - min_score) * (60.0) / (max_score - min_score)
        
        # Gentle blend
        return (new_score * 0.5) + (mapped * 0.5)
