import numpy as np
from typing import Dict, Any, List

from app.ai.segmentation.line_segmentation import segment_lines
from app.ai.segmentation.word_segmentation import segment_words
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

def run_segmentation_pipeline(image: np.ndarray) -> Dict[str, List[Dict[str, int]]]:
    """
    Orchestrates the structural segmentation of the document into lines and words.
    
    Args:
        image (np.ndarray): Preprocessed binary image.
        
    Returns:
        Dict returning hierarchical segmentation:
        {
            "lines": [{"bbox": {...}, "words": [{"bbox": {...}}, ...]}],
        }
    """
    logger.info("Starting segmentation pipeline")
    
    # 1. Segment structural lines
    line_boxes = segment_lines(image, threshold=0.03, min_gap=15)
    
    structured_data = {
        "lines": []
    }
    
    # 2. Segment words inside each line
    for idx, line_box in enumerate(line_boxes):
        x, y, w, h = line_box["x"], line_box["y"], line_box["width"], line_box["height"]
        
        # Crop the line
        line_img = image[y:y+h, x:x+w]
        
        # Segment words on this line
        word_boxes = segment_words(line_img, line_box, min_gap=20)
        
        line_record = {
            "bbox": line_box,
            "words": [{"bbox": word} for word in word_boxes]
        }
        structured_data["lines"].append(line_record)
        
    logger.info(f"Segmentation completed: {len(line_boxes)} lines extracted.")
    return structured_data
