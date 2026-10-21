import cv2
import numpy as np
from typing import Tuple

def enhance_small_or_lowres_text(
    crop: np.ndarray,
    target_min_height: int = 36,
    max_scale: float = 3.0
) -> Tuple[np.ndarray, float]:
    """
    Enhances small, low-resolution, or faint text crops prior to OCR recognition:
    1. If crop height is below target_min_height, applies multi-scale bicubic upscaling.
    2. Applies unsharp masking to sharpen antialiased character edges.
    3. Detects inverted text (light text on dark button/chip) and inverts to dark-on-light.
    
    Returns:
        Tuple[np.ndarray, float]: (enhanced_crop, upscale_scale_factor)
    """
    if crop is None or crop.size == 0:
        return crop, 1.0

    h, w = crop.shape[:2]
    scale = 1.0

    # 1. Multi-scale bicubic upscaling for small text (< target_min_height)
    if h < target_min_height and h > 4:
        scale = min(max_scale, float(target_min_height) / float(h))
        target_w = int(round(w * scale))
        target_h = int(round(h * scale))
        crop_scaled = cv2.resize(crop, (target_w, target_h), interpolation=cv2.INTER_CUBIC)
    else:
        crop_scaled = crop.copy()

    # 2. Check for inverted text (light text on dark background e.g. dark mode / UI buttons)
    gray = cv2.cvtColor(crop_scaled, cv2.COLOR_BGR2GRAY) if len(crop_scaled.shape) == 3 else crop_scaled
    # Sample border pixels to determine background luminance
    border_pixels = np.concatenate([
        gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]
    ])
    bg_mean = float(np.mean(border_pixels))
    center_mean = float(np.mean(gray))

    # If background is dark and center is lighter, invert so OCR sees black text on white
    if bg_mean < 95.0 and center_mean > bg_mean + 15.0:
        if len(crop_scaled.shape) == 3:
            crop_scaled = cv2.bitwise_not(crop_scaled)
        else:
            crop_scaled = cv2.bitwise_not(crop_scaled)

    # 3. Unsharp masking to crisp character edges without clipping
    if scale > 1.2 or h < 30:
        if len(crop_scaled.shape) == 3:
            # Apply light unsharp masking on luminance channel
            ycrcb = cv2.cvtColor(crop_scaled, cv2.COLOR_BGR2YCrCb)
            y, cr, cb = cv2.split(ycrcb)
            gaussian = cv2.GaussianBlur(y, (0, 0), 1.2)
            y_sharp = cv2.addWeighted(y, 1.3, gaussian, -0.3, 0)
            ycrcb_sharp = cv2.merge([y_sharp, cr, cb])
            crop_scaled = cv2.cvtColor(ycrcb_sharp, cv2.COLOR_YCrCb2BGR)
        else:
            gaussian = cv2.GaussianBlur(crop_scaled, (0, 0), 1.2)
            crop_scaled = cv2.addWeighted(crop_scaled, 1.3, gaussian, -0.3, 0)

    return crop_scaled, scale
