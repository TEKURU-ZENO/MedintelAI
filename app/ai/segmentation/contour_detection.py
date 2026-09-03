import cv2
import numpy as np
from typing import List, Dict
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def detect_contours(image: np.ndarray, min_area: int = 20) -> List[Dict[str, int]]:
    """
    Uses connected components/contours as a fallback for structural detection.
    
    Args:
        image (np.ndarray): Binary image.
        min_area (int): Minimum pixel area to consider a valid contour.
        
    Returns:
        List[Dict[str, int]]: List of bounding boxes.
    """
    # Find contours
    contours, _ = cv2.findContours(image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    boxes = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area >= min_area:
            x, y, w, h = cv2.boundingRect(cnt)
            boxes.append({
                "x": x,
                "y": y,
                "width": w,
                "height": h
            })
            
    logger.debug(f"Detected {len(boxes)} contours")
    return boxes
