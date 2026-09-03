from typing import Dict, Any

def calculate_iou(boxA: Dict[str, int], boxB: Dict[str, int]) -> float:
    """
    Calculates the Intersection over Union (IoU) of two bounding boxes.
    Expects dicts with 'x', 'y', 'width', 'height'.
    """
    xA = max(boxA['x'], boxB['x'])
    yA = max(boxA['y'], boxB['y'])
    xB = min(boxA['x'] + boxA['width'], boxB['x'] + boxB['width'])
    yB = min(boxA['y'] + boxA['height'], boxB['y'] + boxB['height'])

    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = boxA['width'] * boxA['height']
    boxBArea = boxB['width'] * boxB['height']

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def dict_to_xywh(box: Dict[str, int]) -> tuple:
    """
    Converts a bounding box dictionary to an (x, y, w, h) tuple.
    """
    return (box.get('x', 0), box.get('y', 0), box.get('width', 0), box.get('height', 0))

def compute_center(box: Dict[str, int]) -> tuple:
    """
    Computes the (cx, cy) center coordinate of a bounding box.
    """
    cx = box['x'] + (box['width'] / 2.0)
    cy = box['y'] + (box['height'] / 2.0)
    return (cx, cy)
