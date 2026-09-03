import cv2
import numpy as np
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_grayscale(image: np.ndarray) -> np.ndarray:
    """
    Converts a color image to grayscale. If the image is already grayscale,
    it simply returns it.
    
    Args:
        image (np.ndarray): The input image.
        
    Returns:
        np.ndarray: The grayscale image.
    """
    if len(image.shape) == 2:
        return image
    
    logger.debug("Converting image to grayscale")
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
