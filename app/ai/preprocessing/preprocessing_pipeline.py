import cv2
import numpy as np
from typing import Dict, Any

from app.ai.preprocessing.grayscale import apply_grayscale
from app.ai.preprocessing.thresholding import apply_threshold
from app.ai.preprocessing.noise_removal import apply_noise_removal
from app.ai.preprocessing.deskew import apply_deskew
from app.ai.preprocessing.normalize import apply_normalization
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_contrast_enhancement(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
    """Applies CLAHE (Contrast Limited Adaptive Histogram Equalization) to improve readability of faint medical text."""
    if not config.get('enabled', True):
        return image
    clip_limit = config.get('clip_limit', 2.0)
    tile_size = tuple(config.get('tile_grid_size', [8, 8]))
    
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    return clahe.apply(image)

def run_preprocessing_pipeline(image: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
    """
    Executes medical document preprocessing steps in sequence.
    
    Pipeline Flow:
    1. Grayscale conversion
    2. Dimension Normalization
    3. CLAHE Contrast Enhancement
    4. Bilateral / Median Denoising
    5. Thresholding (Adaptive / Otsu Binarization)
    6. Deskewing
    
    Args:
        image (np.ndarray): Original medical document image.
        config (Dict[str, Any]): Preprocessing configuration dict.
        
    Returns:
        np.ndarray: Clean preprocessed image.
    """
    if config is None:
        config = {}
        
    logger.info("Starting medical document preprocessing pipeline")
    processed = image.copy()
    
    # 1. Grayscale
    if config.get('grayscale', {}).get('enabled', True):
        processed = apply_grayscale(processed)
        
    # 2. Normalize
    processed = apply_normalization(processed, config.get('normalize', {}))
    
    # 3. Contrast Enhancement (CLAHE)
    contrast_cfg = config.get('contrast', {'enabled': True})
    processed = apply_contrast_enhancement(processed, contrast_cfg)
    
    # 4. Bilateral Denoising
    denoise_cfg = config.get('denoise', {'enabled': True})
    if denoise_cfg.get('enabled', True):
        if len(processed.shape) == 2:
            processed = cv2.bilateralFilter(processed, 9, 75, 75)
            
    # 5. Thresholding
    thresh_cfg = config.get('thresholding', {'method': 'adaptive', 'block_size': 35, 'c': 10})
    processed_bin = apply_threshold(processed, thresh_cfg)
    
    # 6. Deskew
    if config.get('deskew', {}).get('enabled', True):
        processed_bin = apply_deskew(processed_bin, config.get('deskew', {}))
        
    logger.info("Medical document preprocessing pipeline completed")
    return processed_bin

