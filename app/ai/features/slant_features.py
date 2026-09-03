import cv2
import numpy as np
from typing import Dict, Any

def extract_slant_features(image: np.ndarray, config: Dict[str, Any]) -> Dict[str, float]:
    """
    Estimates the dominant slant angle of the handwriting.
    """
    if not config.get('enabled', True):
        return {}
        
    # We use a simple vertical edge detection to find the slant
    # using Sobel operators
    sobel_x = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
    
    # Calculate phase (angle)
    # The slant is defined relative to the vertical axis
    angles = np.arctan2(sobel_x, sobel_y) * (180 / np.pi)
    
    # Filter valid angles that match strokes (where image magnitude is high)
    magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
    valid_angles = angles[magnitude > 50]
    
    dominant_angle = 0.0
    if len(valid_angles) > 0:
        dominant_angle = float(np.median(valid_angles))
        
    return {"dominant_slant_angle": dominant_angle}
