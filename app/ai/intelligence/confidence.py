from typing import Dict, Any

def estimate_confidence(features: Dict[str, Any], structured_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Estimates the confidence of extracted features based on extraction quality and data availability.
    """
    confidence = {}
    overall_score = 1.0
    
    # 1. Count items
    num_lines = 0
    num_words = 0
    
    if structured_data and "lines" in structured_data:
        num_lines = len(structured_data["lines"])
        for line in structured_data["lines"]:
            num_words += len(line.get("words", []))
            
    # Estimate confidence based on available data
    # Proxy characters by words if not explicitly available
    num_chars_proxy = num_words * 5 
    char_features = features.get("character_features", {})
    if "num_characters" in char_features:
        num_chars_proxy = char_features["num_characters"]
        
    # Calculate numeric confidence (threshold = 20 chars)
    confidence_score = min(1.0, float(num_chars_proxy) / 20.0)
    
    # Factor in density
    if char_features.get("stroke_density", 0.0) < 0.01:
        confidence_score *= 0.5
        
    # Explicit Minimum Data Check flag
    if char_features.get("low_confidence_data", False):
        confidence_score *= 0.25 # Severe penalty
        
    label = "low"
    if confidence_score > 0.7:
        label = "high"
    elif confidence_score > 0.4:
        label = "medium"
        
    confidence["score"] = confidence_score
    confidence["label"] = label
    
    # Granular Per-Feature Confidence
    spacing_conf = 1.0 if num_words >= 3 else 0.5
    baseline_conf = 1.0 if num_lines >= 2 else 0.5
    slant_conf = confidence_score
    stroke_conf = confidence_score
    if char_features.get("stroke_density", 0.0) < 0.01:
        stroke_conf *= 0.5
        
    confidence["features"] = {
        "spacing": min(1.0, spacing_conf),
        "baseline": min(1.0, baseline_conf),
        "slant": min(1.0, slant_conf),
        "stroke": min(1.0, stroke_conf)
    }

    features["confidence_metrics"] = confidence
    return features
