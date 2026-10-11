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
    # Only scale down if image exceeds maximum dimension (e.g. 4096px) to prevent OOM
    max_dim = config.get('max_dimension', 4096)
    h, w = image.shape[:2]
    
    if max(h, w) <= max_dim:
        return image
        
    scale = max_dim / float(max(h, w))
    target_width = int(w * scale)
    target_height = int(h * scale)
    logger.info(f"Downscaling extremely large image from {w}x{h} to {target_width}x{target_height}")
    
    interpolation = cv2.INTER_AREA
    normalized = cv2.resize(image, (target_width, target_height), interpolation=interpolation)
    return normalized
