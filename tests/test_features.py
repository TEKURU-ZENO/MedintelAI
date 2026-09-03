from app.ai.features.line_features import extract_line_features
from app.ai.features.word_features import extract_word_features

def test_line_features_computation():
    structured_lines = [
        {"bbox": {"x": 0, "y": 10, "width": 100, "height": 20}},
        {"bbox": {"x": 0, "y": 40, "width": 100, "height": 30}}
    ]
    config = {"compute_height": True, "compute_deviation": True, "compute_drift": True}
    res = extract_line_features(structured_lines, config)
    
    # average height of 20 and 30 is 25
    assert res["avg_line_height"] == 25.0
    assert "baseline_deviation" in res
    assert "baseline_drift" in res

def test_word_features_empty():
    res = extract_word_features([], {})
    assert res == {"avg_word_width": 0.0}

def test_word_features_computation():
    structured_lines = [
        {"words": [{"bbox": {"x": 0, "y": 0, "width": 40, "height": 20}},
                   {"bbox": {"x": 50, "y": 0, "width": 60, "height": 20}}]}
    ]
    config = {"compute_width": True}
    res = extract_word_features(structured_lines, config)
    # average width of 40 and 60 is 50
    assert res["avg_word_width"] == 50.0
