from typing import Dict, Any, List
import numpy as np

def extract_character_features(structured_data: Dict[str, Any], config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Computes character distributions, std metrics, and fallback estimation.
    """
    config = config or {}
    if not config.get("enabled", True):
        return {}
        
    char_widths = []
    char_heights = []
    word_widths = []
    char_spacings = []
    
    lines = structured_data.get("lines", [])
    
    # 1. Collect true characters if segmentation exists
    for line in lines:
        for word in line.get("words", []):
            word_widths.append(word["bbox"]["width"])
            
            chars = word.get("characters", [])
            
            # Sort chars by X for spacing
            sorted_chars = sorted(chars, key=lambda c: c["bbox"]["x"])
            
            for i, char in enumerate(sorted_chars):
                char_widths.append(char["bbox"]["width"])
                char_heights.append(char["bbox"]["height"])
                
                if i > 0:
                    prev_char = sorted_chars[i-1]["bbox"]
                    curr_char = char["bbox"]
                    gap = curr_char["x"] - (prev_char["x"] + prev_char["width"])
                    if gap > 0:
                        char_spacings.append(gap)
                
    features = {}
    
    # 2. Fallback Estimation (if contours fail and we have words but no characters)
    avg_expected_chars_per_word = config.get("avg_expected_chars", 5.0)
    
    if not char_widths and word_widths:
        # Fallback logic
        estimated_char_widths = [ww / avg_expected_chars_per_word for ww in word_widths]
        char_widths.extend(estimated_char_widths)
        features["fallback_used"] = True
    else:
        features["fallback_used"] = False
        
    # 3. Compute Metrics
    if char_widths:
        features["avg_char_width"] = float(np.mean(char_widths))
        features["width_std"] = float(np.std(char_widths))
        features["num_characters"] = len(char_widths)
    else:
        features["avg_char_width"] = 0.0
        features["width_std"] = 0.0
        features["num_characters"] = 0
        
    if char_heights:
        features["avg_char_height"] = float(np.mean(char_heights))
        features["height_std"] = float(np.std(char_heights))
    else:
        features["avg_char_height"] = 0.0
        features["height_std"] = 0.0
        
    if char_spacings:
        features["avg_char_spacing"] = float(np.mean(char_spacings))
        features["spacing_std"] = float(np.std(char_spacings))
    else:
        features["avg_char_spacing"] = 0.0
        features["spacing_std"] = 0.0
        
    # 4. Minimum Data Check
    MIN_THRESHOLD = config.get("min_characters_threshold", 5)
    if features.get("num_characters", 0) < MIN_THRESHOLD:
        features["low_confidence_data"] = True
    else:
        features["low_confidence_data"] = False
    
    return features
