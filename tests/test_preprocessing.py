import numpy as np
from app.ai.preprocessing.grayscale import apply_grayscale
from app.ai.preprocessing.thresholding import apply_threshold

def test_grayscale_conversion_color():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    out = apply_grayscale(img)
    assert len(out.shape) == 2
    
def test_grayscale_conversion_already_gray():
    img = np.zeros((100, 100), dtype=np.uint8)
    out = apply_grayscale(img)
    assert len(out.shape) == 2

def test_adaptive_thresholding():
    img = np.ones((100, 100), dtype=np.uint8) * 200
    config = {'method': 'adaptive', 'block_size': 35, 'c': 10}
    out = apply_threshold(img, config)
    assert len(out.shape) == 2
    assert np.max(out) <= 255
