from typing import Dict, Any

def normalize_features(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizes pixel-dependent features to image-size independent metrics.
    """
    normalized_metrics = {}
    
    word_features = features.get("word_features", {})
    char_features = features.get("character_features", {})
    line_features = features.get("line_features", {})
    
    # 1. Spacing Normalization
    # We expect `median_inter_word_spacing` in word_features, but sometimes it's nested
    avg_spacing = word_features.get("median_inter_word_spacing", 0.0)
    
    # Use avg word width for fallback if avg char width is missing
    avg_word_width = word_features.get("avg_word_width", 50.0)
    char_width_proxy = max(avg_word_width / 5.0, 1.0)
    
    normalized_metrics["normalized_spacing"] = avg_spacing / char_width_proxy
    
    # 2. Stroke Normalization
    avg_stroke = char_features.get("avg_stroke_width", 0.0)
    
    # Fallback to 50 if char height missing
    avg_char_height = char_features.get("avg_char_height", 0.0)
    if avg_char_height == 0.0:
        avg_line_height = line_features.get("avg_line_height", 50.0) 
        avg_char_height = max(avg_line_height * 0.7, 1.0) # approx fallback
        
    normalized_metrics["normalized_stroke_width"] = avg_stroke / max(avg_char_height, 1.0)
    
    # 3. Stroke Density Normalization
    stroke_density = char_features.get("stroke_density", 0.0)
    expected_density_range = features.get("config", {}).get("expected_density_range", 0.1) # Default 10% ink
    normalized_metrics["normalized_stroke_density"] = stroke_density / max(expected_density_range, 0.01)
    
    # Add slant for completeness, though it is usually an angle (already normalized)
    normalized_metrics["slant_angle"] = char_features.get("slant_angle", 0.0)
    
    features["normalized_metrics"] = normalized_metrics
    return features
