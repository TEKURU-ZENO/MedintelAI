import cv2
import numpy as np
from typing import Dict, Any, Optional

from app.ai.preprocessing.grayscale import apply_grayscale
from app.ai.preprocessing.thresholding import apply_threshold
from app.ai.preprocessing.noise_removal import apply_noise_removal
from app.ai.preprocessing.deskew import apply_deskew
from app.ai.preprocessing.normalize import apply_normalization
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def apply_contrast_enhancement(image: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
    """Applies CLAHE to improve readability of faint text without destroying anti-aliased edges."""
    if config is None:
        config = {}
    if not config.get('enabled', True):
        return image
    clip_limit = config.get('clip_limit', 1.8)
    tile_size = tuple(config.get('tile_grid_size', [8, 8]))
    
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_size)
    return clahe.apply(image)

def run_screen_preprocessing(image: np.ndarray, upscale_factor: float = 1.0) -> np.ndarray:
    """
    Preprocessing path optimized for SCREEN / DIGITAL documents (screenshots, UI text, PDFs).
    - Preserves high-resolution anti-aliased font edges.
    - Zero destructive binarization / hard thresholding.
    - Optional bicubic upscaling for small crops.
    - Mild CLAHE contrast normalization and light bilateral filter.
    """
    logger.info("Executing screen/digital document preprocessing")
    processed = image.copy()
    
    # 1. Optional bicubic upscaling if requested
    if upscale_factor > 1.0:
        processed = cv2.resize(processed, (0, 0), fx=upscale_factor, fy=upscale_factor, interpolation=cv2.INTER_CUBIC)
        
    # 2. Convert to grayscale if 3-channel
    if len(processed.shape) == 3:
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    else:
        gray = processed
        
    # 3. Mild contrast enhancement (low clip limit prevents over-amplifying background noise)
    clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 4. Light bilateral filter preserving sharp edge gradients
    filtered = cv2.bilateralFilter(enhanced, 5, 50, 50)
    
    # Return as 3-channel BGR for RapidOCR / TrOCR consistency
    return cv2.cvtColor(filtered, cv2.COLOR_GRAY2BGR)

def run_scanned_preprocessing(image: np.ndarray, config: Dict[str, Any] = None) -> np.ndarray:
    """
    Preprocessing path optimized for SCANNED PAPER / FAX / CAMERA captures.
    - Denoise, deskew, CLAHE contrast enhancement, and adaptive thresholding.
    """
    if config is None:
        config = {}
        
    logger.info("Executing scanned paper document preprocessing pipeline")
    processed = image.copy()
    
    # 1. Grayscale
    if config.get('grayscale', {}).get('enabled', True):
        processed = apply_grayscale(processed)
        
    # 2. Dimension normalization (only for extreme dimensions > 4000px)
    processed = apply_normalization(processed, config.get('normalize', {}))
    
    # 3. Contrast Enhancement (CLAHE)
    contrast_cfg = config.get('contrast', {'enabled': True, 'clip_limit': 2.0})
    processed = apply_contrast_enhancement(processed, contrast_cfg)
    
    # 4. Bilateral Denoising
    denoise_cfg = config.get('denoise', {'enabled': True})
    if denoise_cfg.get('enabled', True):
        if len(processed.shape) == 2:
            processed = cv2.bilateralFilter(processed, 9, 75, 75)
            
    # 5. Controlled Thresholding
    thresh_cfg = config.get('thresholding', {'method': 'adaptive', 'block_size': 35, 'c': 10})
    processed_bin = apply_threshold(processed, thresh_cfg)
    
    # 6. Deskew
    if config.get('deskew', {}).get('enabled', True):
        processed_bin = apply_deskew(processed_bin, config.get('deskew', {}))
        
    if len(processed_bin.shape) == 2:
        return cv2.cvtColor(processed_bin, cv2.COLOR_GRAY2BGR)
    return processed_bin

def run_preprocessing_pipeline(
    image: np.ndarray,
    config: Dict[str, Any] = None,
    input_mode: str = 'auto'
) -> np.ndarray:
    """
    Dispatches to appropriate preprocessing pipeline based on input_mode.
    
    Args:
        image: Original input image array.
        config: Optional custom configuration dict.
        input_mode: 'screen', 'digital', 'scanned_paper', or 'auto'.
    """
    if input_mode in ('screen', 'digital'):
        return run_screen_preprocessing(image)
    elif input_mode == 'scanned_paper':
        return run_scanned_preprocessing(image, config)
    
    # Auto-detection: digital documents generally have very clean white/uniform backgrounds
    # or are rendered from PDF / screen captures.
    # If image already has clean background (std dev in corners is low), treat as digital.
    try:
        h, w = image.shape[:2]
        corners = [
            image[0:min(20, h), 0:min(20, w)],
            image[0:min(20, h), max(0, w-20):w]
        ]
        corner_stds = [np.std(c) for c in corners if c.size > 0]
        if corner_stds and np.mean(corner_stds) < 8.0:
            return run_screen_preprocessing(image)
    except Exception:
        pass
        
    return run_screen_preprocessing(image)

