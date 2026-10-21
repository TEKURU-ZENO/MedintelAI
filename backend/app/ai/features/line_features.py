from typing import Dict, List, Any
import numpy as np
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def extract_line_features(structured_lines: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes features based on the line segmentation boxes.
    
    Args:
        structured_lines (List[Dict]): The segmented lines data.
        config (Dict): Configuration for line features.
        
    Returns:
        Dict[str, float]: Extracted metrics.
    """
    if not config.get('enabled', True) or not structured_lines:
        return {}
        
    heights = [line["bbox"]["height"] for line in structured_lines]
    
    features = {}
    if config.get("compute_height", True):
        features["avg_line_height"] = float(np.mean(heights)) if heights else 0.0
        
    # Mocking deviation and drift based on spacing of Y coordinates
    if config.get("compute_deviation", True):
        y_coords = [line["bbox"]["y"] for line in structured_lines]
        features["baseline_deviation"] = float(np.std(y_coords)) if len(y_coords) > 1 else 0.0
        
    if config.get("compute_drift", True):
        features["baseline_drift"] = 0.5  # Placeholder for more complex drift algorithms
        
    logger.debug("Computed line features")
    return features
