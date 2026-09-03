import os
import cv2
import json
import numpy as np
from app.ai.pipeline.pipeline_controller import PipelineController

def test_full_pipeline_end_to_end(tmp_path):
    # Create dummy image
    img = np.ones((500, 500, 3), dtype=np.uint8) * 255
    # Draw dark lines for text
    cv2.line(img, (50, 100), (450, 100), (0, 0, 0), 5)
    cv2.line(img, (50, 200), (450, 200), (0, 0, 0), 5)
    
    img_path = tmp_path / "dummy_test.jpg"
    out_path = tmp_path / "output.json"
    cv2.imwrite(str(img_path), img)
    
    config = {
        "preprocessing": {
            "grayscale": {"enabled": True},
            "thresholding": {"method": "adaptive", "block_size": 35, "c": 10},
            "noise_removal": {"kernel_size": 3, "iterations": 1},
            "deskew": {"enabled": False},
            "normalize": {"target_height": 800, "maintain_aspect_ratio": True}
        },
        "features": {
            "line_features": {"enabled": True, "compute_height": True},
            "word_features": {"enabled": True},
            "spacing_features": {"enabled": True},
            "slant_features": {"enabled": True},
            "stroke_features": {"enabled": True},
            "baseline_features": {"enabled": True}
        },
        "pipeline": {
            "directories": {"json_output": str(tmp_path)}
        }
    }
    
    controller = PipelineController(config)
    success = controller.process_image(str(img_path), str(out_path))
    
    assert success is not None
    assert os.path.exists(str(out_path))
    
    with open(str(out_path), 'r') as f:
        data = json.load(f)
        
    assert data["schema_version"] == "1.0"
    assert "line_features" in data
    assert "word_features" in data
    assert "character_features" in data
