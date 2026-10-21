import cv2
import numpy as np
from typing import Optional
from pathlib import Path
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def load_image(filepath: str, grayscale: bool = False) -> Optional[np.ndarray]:
    """
    Loads an image from disk.
    
    Args:
        filepath (str): Path to the image.
        grayscale (bool): Whether to load the image in grayscale mode.
        
    Returns:
        np.ndarray: The loaded image, or None if it fails.
    """
    path = Path(filepath)
    if not path.is_file():
        logger.error(f"Image not found: {filepath}")
        return None
        
    flags = cv2.IMREAD_GRAYSCALE if grayscale else cv2.IMREAD_COLOR
    try:
        image = cv2.imread(str(path), flags)
        if image is None:
            logger.error(f"Failed to read image (might be corrupt): {filepath}")
            return None
        return image
    except Exception as e:
        logger.error(f"Exception while loading image {filepath}: {e}")
        return None

def save_image(filepath: str, image: np.ndarray) -> bool:
    """
    Saves an image to disk.
    
    Args:
        filepath (str): Destination path.
        image (np.ndarray): Image to save.
        
    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(filepath, image)
        if not success:
            logger.error(f"Failed to write image to {filepath}")
        return success
    except Exception as e:
        logger.error(f"Exception while saving image {filepath}: {e}")
        return False
