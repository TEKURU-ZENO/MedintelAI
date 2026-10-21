import math
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

def validate_feature(value: float, min_val: float, max_val: float, default_val: float = 0.0) -> float:
    """Validates a feature value, clamping it to min/max or replacing NaN with default."""
    if value is None or (isinstance(value, float) and (math.isnan(value) or math.isinf(value))):
        logger.warning(f"Invalid feature value detected. Using default: {default_val}")
        return default_val
    return max(min_val, min(max_val, float(value)))

def validate_features(raw_features: Dict[str, Any], schema_bounds: Dict[str, Tuple[float, float]] = None) -> Dict[str, Any]:
    """
    Validates a dictionary of features against expected bounds.
    """
    # Default bounds to prevent score explosions on high-variance edge cases
    default_bounds = {
        "spacing_consistency": (0.0, 50.0),
        "baseline_deviation": (0.0, 50.0),
        "stroke_variance": (0.0, 20.0),
        "slant_variance": (0.0, 90.0),
        "width_std": (0.0, 100.0),
        "height_std": (0.0, 100.0),
        "spacing_std": (0.0, 50.0)
    }
    
    schema_bounds = schema_bounds or default_bounds
    validated = {}
    
    for key, value in raw_features.items():
        if isinstance(value, dict):
             # Recursively validate nested features
             validated[key] = validate_features(value, schema_bounds)
        elif key in schema_bounds:
            min_val, max_val = schema_bounds[key]
            if isinstance(value, (int, float)):
                validated[key] = validate_feature(value, min_val, max_val)
            else:
                validated[key] = value
        else:
            # If no bounds specified, at least check for NaN/Inf if it's a number
            if isinstance(value, (int, float)):
                 validated[key] = validate_feature(value, -float('inf'), float('inf'), default_val=0.0)
            else:
                validated[key] = value
                
    return validated
