import os
import csv
import json
from datetime import datetime
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class DatasetCollector:
    def __init__(self, output_dir: str = "outputs/dataset"):
        self.output_dir = output_dir
        self.features_file = os.path.join(output_dir, "features.csv")
        self.metadata_file = os.path.join(output_dir, "metadata.json")
        
        os.makedirs(self.output_dir, exist_ok=True)
        self._init_files()
        
    def _init_files(self):
        if not os.path.exists(self.features_file):
            with open(self.features_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "image_id", "slant_std", "spacing_std", "baseline_var", "stroke_var", 
                    "score", "smoothed_score", "confidence_score", "num_chars", "num_words", "human_label"
                ])
                
        if not os.path.exists(self.metadata_file):
            with open(self.metadata_file, 'w') as f:
                json.dump([], f)
                
    def collect(self, image_id: str, features: Dict[str, Any]):
        """Collects features and appends them to the dataset."""
        try:
            config = features.get("config", {})
            user_id = config.get("user_id", "anonymous")
            level = config.get("level", 2)
            
            # Extract features safely
            char_features = features.get("character_features", {})
            word_features = features.get("word_features", {})
            line_features = features.get("line_features", {})
            scores = features.get("scores", {})
            
            slant_std = char_features.get("slant_variance", 0.0)
            spacing_std = word_features.get("spacing_consistency", 0.0)
            baseline_var = line_features.get("baseline_deviation", 0.0)
            stroke_var = char_features.get("stroke_variance", 0.0)
            score = scores.get("overall_score", 0.0)
            smoothed_score = scores.get("smoothed_score", score)
            
            confidence_metrics = features.get("confidence_metrics", {})
            confidence_score = confidence_metrics.get("score", 1.0)
            num_chars = char_features.get("num_characters", 0)
            num_words = word_features.get("num_words", 0)
            
            # Append to CSV
            with open(self.features_file, 'a', newline='') as f:
                writer = csv.writer(f)
                # human_label is empty by default for auto-collection
                writer.writerow([
                    image_id, slant_std, spacing_std, baseline_var, stroke_var, 
                    score, smoothed_score, confidence_score, num_chars, num_words, ""
                ])
                
            # Append to Metadata JSON
            with open(self.metadata_file, 'r+') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = []
                data.append({
                    "image_id": image_id, 
                    "user_id": user_id,
                    "level": level,
                    "timestamp": datetime.now().isoformat(), 
                    "status": "auto-collected"
                })
                f.seek(0)
                json.dump(data, f, indent=2)
                f.truncate()
                
            logger.debug(f"Appended {image_id} to dataset.")
        except Exception as e:
            logger.error(f"Failed to collect dataset for {image_id}: {e}")
