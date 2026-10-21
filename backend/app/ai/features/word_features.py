from typing import Dict, List, Any
import numpy as np

def extract_word_features(structured_lines: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, float]:
    """
    Computes features based on the word bounding boxes across all lines.
    
    Args:
        structured_lines (List[Dict]): The segmented lines containing words.
        config (Dict): Configuration dict.
        
    Returns:
        Dict[str, float]: Word related metrics.
    """
    if not config.get('enabled', True):
        return {}
        
    widths = []
    
    for line in structured_lines:
        for word in line.get("words", []):
            widths.append(word["bbox"]["width"])
            
    features = {}
    if config.get("compute_width", True) and widths:
        features["avg_word_width"] = float(np.mean(widths))
    else:
        features["avg_word_width"] = 0.0
        
    return features
