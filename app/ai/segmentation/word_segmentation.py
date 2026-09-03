import numpy as np
from typing import List, Dict
from app.ai.segmentation.projection_profiles import compute_vertical_projection
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def segment_words(line_image: np.ndarray, line_bbox: Dict[str, int], min_gap: int = 15) -> List[Dict[str, int]]:
    """
    Segments a single text line into words using vertical projection profiles.
    
    Args:
        line_image (np.ndarray): Binary image crop of a single line.
        line_bbox (Dict[str, int]): Bounding box of the line in the original image.
        min_gap (int): Minimum zero-sum columns required to split a word.
        
    Returns:
        List[Dict[str, int]]: List of word bounding boxes relative to the original image.
    """
    profile = compute_vertical_projection(line_image)
    max_val = np.max(profile) if len(profile) > 0 else 0
    
    if max_val == 0:
        return []
        
    # Any column with > 0 pixels is ink
    is_ink = profile > 0
    
    words = []
    in_word = False
    start_x = 0
    h, w = line_image.shape
    
    for x in range(w):
        if is_ink[x] and not in_word:
            in_word = True
            start_x = x
        elif not is_ink[x] and in_word:
            # Look ahead to see if it's a real gap or just an intra-word space
            gap_lookahead = is_ink[x:x+min_gap]
            if not np.any(gap_lookahead):
                in_word = False
                end_x = x
                if end_x - start_x > 2: # Min width
                    words.append({
                        "x": line_bbox["x"] + start_x,
                        "y": line_bbox["y"],
                        "width": end_x - start_x,
                        "height": line_bbox["height"]
                    })
                    
    if in_word:
        words.append({
            "x": line_bbox["x"] + start_x,
            "y": line_bbox["y"],
            "width": w - start_x,
            "height": line_bbox["height"]
        })
        
    return words
