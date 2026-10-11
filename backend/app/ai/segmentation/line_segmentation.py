import numpy as np
from typing import List, Dict
from app.ai.segmentation.projection_profiles import compute_horizontal_projection
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def segment_lines(image: np.ndarray, threshold: float = 0.05, min_gap: int = 10) -> List[Dict[str, int]]:
    """
    Segments an image into text lines using horizontal projection profiles.
    
    Args:
        image (np.ndarray): Binary image (text=255).
        threshold (float): Fraction of the maximum projection value to consider as text.
        min_gap (int): Minimum continuous 0-sum rows to consider a true gap between lines.
        
    Returns:
        List[Dict[str, int]]: List of bounding boxes for each line {'x', 'y', 'width', 'height'}.
    """
    profile = compute_horizontal_projection(image)
    max_val = np.max(profile)
    if max_val == 0:
        return []
        
    is_text = profile > (max_val * threshold)
    
    lines = []
    in_line = False
    start_y = 0
    h, w = image.shape
    
    for y in range(h):
        if is_text[y] and not in_line:
            in_line = True
            start_y = y
        elif not is_text[y] and in_line:
            # We hit a blank row, but we should ensure the gap is large enough before breaking
            # Simplified line breaking here:
            gap_lookahead = is_text[y:y+min_gap]
            if not np.any(gap_lookahead):
                in_line = False
                end_y = y
                
                # Expand box to left and right using contour or just full width
                # Here we return full width of the image for simplicity
                if end_y - start_y > 5:  # Minimum line height
                    lines.append({
                        "x": 0,
                        "y": start_y,
                        "width": w,
                        "height": end_y - start_y
                    })
                    
    # Handle case where the last line goes to the bottom
    if in_line:
        lines.append({
            "x": 0,
            "y": start_y,
            "width": w,
            "height": h - start_y
        })
        
    logger.debug(f"Segmented {len(lines)} lines")
    return lines
