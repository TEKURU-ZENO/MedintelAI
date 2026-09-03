import cv2
import numpy as np
from typing import List, Dict

def draw_bounding_boxes(image: np.ndarray, boxes: List[Dict[str, int]], color: tuple = (0, 255, 0), thickness: int = 2) -> np.ndarray:
    """
    Draws bounding boxes on a copy of the given image.
    
    Args:
        image (np.ndarray): Original image.
        boxes (List[Dict[str, int]]): List of dicts with 'x', 'y', 'width', 'height'.
        color (tuple): BGR color.
        thickness (int): Thickness of the box edges.
        
    Returns:
        np.ndarray: A new image with bounding boxes drawn.
    """
    output = image.copy()
    if len(output.shape) == 2:
        output = cv2.cvtColor(output, cv2.COLOR_GRAY2BGR)
        
    for box in boxes:
        x, y = box['x'], box['y']
        w, h = box['width'], box['height']
        cv2.rectangle(output, (x, y), (x + w, y + h), color, thickness)
        
    return output

def plot_projection_profile(profile: np.ndarray, horizontal: bool = True) -> np.ndarray:
    """
    Creates a visual representation of a 1D projection profile.
    
    Args:
        profile (np.ndarray): 1D array representing the projection.
        horizontal (bool): True if horizontal projection (rows), False if vertical (columns).
        
    Returns:
        np.ndarray: An image visualizing the profile.
    """
    max_val = np.max(profile) if np.max(profile) > 0 else 1
    
    if horizontal:
        width = 400
        height = len(profile)
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        for y, val in enumerate(profile):
            length = int((val / max_val) * width)
            cv2.line(img, (0, y), (length, y), (255, 0, 0), 1)
    else:
        height = 400
        width = len(profile)
        img = np.ones((height, width, 3), dtype=np.uint8) * 255
        for x, val in enumerate(profile):
            length = int((val / max_val) * height)
            cv2.line(img, (x, height), (x, height - length), (0, 0, 255), 1)
            
    return img
