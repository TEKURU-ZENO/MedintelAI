import cv2
import numpy as np
from typing import Dict, Any
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_noise_removal(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """
    Removes salt-and-pepper noise from the binary image using median blur and morphology.
    
    Args:
        image (np.ndarray): Binary input image.
        config (Dict[str, Any]): Preprocessing configuration for noise removal.
        
    Returns:
        np.ndarray: Denoised binary image.
    """
    kernel_size = config.get('kernel_size', 3)
    iterations = config.get('iterations', 1)
    
    if kernel_size % 2 == 0:
        kernel_size += 1
        
    logger.debug(f"Applying noise removal (kernel_size={kernel_size})")
    
    # Median blur targets salt-and-pepper noise
    denoised = cv2.medianBlur(image, kernel_size)
    
    # Optional morphological opening to remove small disconnected specs
    if iterations > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        denoised = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, kernel, iterations=iterations)
        
    return denoised
