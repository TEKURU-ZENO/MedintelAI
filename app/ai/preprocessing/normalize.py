import cv2
import numpy as np
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_normalization(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """
    Normalizes the image dimensions to a standard vertical height to ensure consistent
    stroke width and spatial frequencies across the dataset.
    
    Args:
        image (np.ndarray): Input image.
        config (Dict[str, Any]): Preprocessing configuration for normalization.
        
    Returns:
        np.ndarray: Normalized image.
    """
    target_height = config.get('target_height', 800)
    maintain_aspect_ratio = config.get('maintain_aspect_ratio', True)
    
    h, w = image.shape[:2]
    
    if h == target_height:
        return image
        
    if maintain_aspect_ratio:
        scale = target_height / float(h)
        target_width = int(w * scale)
    else:
        target_width = w
        
    logger.debug(f"Normalizing image from {w}x{h} to {target_width}x{target_height}")
    
    # If the image target is binary we should interpolate carefully
    interpolation = cv2.INTER_AREA if target_height < h else cv2.INTER_CUBIC
    normalized = cv2.resize(image, (target_width, target_height), interpolation=interpolation)
    
    # In case it is a binary image, cubic might blur the edges. Hard threshold back to binary.
    if len(normalized.shape) == 2 and np.unique(normalized).size > 2:
        _, normalized = cv2.threshold(normalized, 127, 255, cv2.THRESH_BINARY)
        
    return normalized
