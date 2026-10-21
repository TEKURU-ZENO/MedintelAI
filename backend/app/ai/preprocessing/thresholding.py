import cv2
import numpy as np
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_threshold(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """
    Applies adaptive thresholding to a grayscale image to create a binary mask.
    
    Args:
        image (np.ndarray): Grayscale input image.
        config (Dict[str, Any]): Preprocessing configuration for thresholding.
        
    Returns:
        np.ndarray: Binary image (255 for foreground text, 0 for background).
    """
    if len(image.shape) != 2:
        raise ValueError("Image must be grayscale before thresholding.")
        
    method = config.get('method', 'adaptive')
    
    if method == 'adaptive':
        block_size = config.get('block_size', 35)
        c = config.get('c', 10)
        
        # Ensure block size is odd and > 1
        if block_size % 2 == 0:
            block_size += 1
        block_size = max(3, block_size)
            
        logger.debug(f"Applying adaptive thresholding (block_size={block_size}, c={c})")
        # Text is usually dark on light background. We want text to be 255 (white).
        binary = cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, block_size, c
        )
    else:
        logger.debug("Applying Otsu thresholding")
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
    return binary
