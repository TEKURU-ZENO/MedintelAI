import numpy as np
from app.ai.segmentation.line_segmentation import segment_lines
from app.ai.segmentation.word_segmentation import segment_words

def test_line_segmentation_empty():
    img = np.zeros((100, 100), dtype=np.uint8)
    lines = segment_lines(img)
    assert len(lines) == 0

def test_line_segmentation_simple_block():
    img = np.zeros((100, 100), dtype=np.uint8)
    img[20:30, :] = 255  # One line of text
    lines = segment_lines(img, threshold=0.01, min_gap=5)
    assert len(lines) == 1
    assert lines[0]['height'] >= 10

def test_word_segmentation_empty():
    img = np.zeros((30, 100), dtype=np.uint8)
    bbox = {'x': 0, 'y': 20, 'width': 100, 'height': 30}
    words = segment_words(img, bbox)
    assert len(words) == 0
