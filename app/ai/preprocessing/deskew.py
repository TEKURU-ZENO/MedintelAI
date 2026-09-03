import cv2
import numpy as np
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_deskew(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """
    Corrects global skew in the document.
    Expects a binary image where text is 255 and background is 0.
    
    Args:
        image (np.ndarray): Binary input image.
        config (Dict[str, Any]): Preprocessing configuration for deskew.
        
    Returns:
        np.ndarray: Deskewed image.
    """
    if not config.get('enabled', True):
        return image
        
    max_angle = config.get('max_angle', 15.0)
    
    # Find all non-zero pixels (text)
    coords = np.column_stack(np.where(image > 0))
    if len(coords) == 0:
        logger.warning("No foreground pixels found for deskew")
        return image
        
    # Get bounding box
    angle = cv2.minAreaRect(coords)[-1]
    
    # OpenCV minAreaRect returns angles in strange ranges depending on version
    # Normalizing angle to be roughly horizontal
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Limit maximum Deskew Angle to prevent drastic rotation on single words or weird noise
    if abs(angle) > max_angle:
        logger.debug(f"Detected skew angle {angle:.2f} exceeds max {max_angle}. Skipping deskew.")
        return image
        
    logger.debug(f"Deskewing image by angle: {angle:.2f} degrees")
    
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Compute rotation matrix and rotate
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return deskewed
