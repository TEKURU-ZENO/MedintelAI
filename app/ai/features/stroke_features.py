import cv2
import numpy as np
from typing import Dict, Any

def extract_stroke_features(image: np.ndarray, config: Dict[str, Any]) -> Dict[str, float]:
    """
    Estimates stroke thickness and density.
    """
    if not config.get('enabled', True):
        return {}
        
    features = {}
    
    # Density: foreground pixels / total area
    if config.get("compute_density", True):
        total_pixels = image.shape[0] * image.shape[1]
        foreground_pixels = cv2.countNonZero(image)
        features["stroke_density"] = float(foreground_pixels) / float(total_pixels) if total_pixels > 0 else 0.0
        
    # Average width: using Distance Transform
    if config.get("compute_width", True):
        dist_transform = cv2.distanceTransform(image, cv2.DIST_L2, 3)
        # Stroke centers are local maxima in the distance transform
        # We can approximate average thickness by 2 * average distance in the stroke core
        threshold_dist = dist_transform > (np.max(dist_transform) * 0.5)
        core_distances = dist_transform[threshold_dist]
        
        if len(core_distances) > 0:
            features["avg_stroke_width"] = float(np.mean(core_distances) * 2)
            features["stroke_variance"] = float(np.std(core_distances) * 2) # Equivalent to stroke_std in UI
        else:
            features["avg_stroke_width"] = 0.0
            features["stroke_variance"] = 0.0
        
    return features
