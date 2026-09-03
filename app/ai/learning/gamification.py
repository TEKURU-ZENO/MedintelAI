from typing import Dict, Any

# ------------------------------------------------------------------
# Level Configuration
#
# Purpose:
# Defines adaptive scoring behavior for different learner levels.
#
# Each level contains:
# 1. weights
#    Determines the importance of each handwriting feature when
#    calculating the overall score.
#
# 2. thresholds
#    Defines acceptable variance ranges for each feature.
#
# Lower levels are more forgiving.
# Higher levels require greater handwriting consistency.
# ------------------------------------------------------------------

DEFAULT_LEVEL_CONFIG = {

    # ==============================================================
    # Level 1 (Beginner)
    #
    # Focus:
    # - Letter formation and slant consistency
    # - More tolerant spacing and alignment requirements
    # ==============================================================

    1: {
        "weights": {
            "spacing": 0.1,
            "slant": 0.4,
            "baseline": 0.3,
            "stroke": 0.2
        },

        "thresholds": {
            "expected_spacing_range": 1.5,
            "expected_slant_range": 15.0,
            "expected_baseline_range": 8.0,
            "expected_stroke_range": 0.3
        }
    },

    # ==============================================================
    # Level 2 (Intermediate)
    #
    # Focus:
    # Balanced evaluation across all handwriting dimensions.
    # ==============================================================

    2: {
        "weights": {
            "spacing": 0.25,
            "slant": 0.25,
            "baseline": 0.25,
            "stroke": 0.25
        },

        "thresholds": {
            "expected_spacing_range": 1.0,
            "expected_slant_range": 12.0,
            "expected_baseline_range": 6.0,
            "expected_stroke_range": 0.25
        }
    },

    # ==============================================================
    # Level 3 (Advanced)
    #
    # Focus:
    # Greater emphasis on spacing precision and overall writing
    # consistency.
    # ==============================================================

    3: {
        "weights": {
            "spacing": 0.3,
            "slant": 0.25,
            "baseline": 0.25,
            "stroke": 0.2
        },

        "thresholds": {
            "expected_spacing_range": 0.8,
            "expected_slant_range": 10.0,
            "expected_baseline_range": 5.0,
            "expected_stroke_range": 0.2
        }
    }
}


# ------------------------------------------------------------------
# Level Configuration Helpers
#
# Purpose:
# Retrieve level-specific scoring configurations.
#
# Supports:
# - Default system configuration
# - Custom configuration overrides
# ------------------------------------------------------------------

def get_level_config(
    level: int,
    custom_config: Dict[int, Any] = None
) -> Dict[str, Any]:
    """
    Returns the complete configuration for a given level.

    If the level does not exist, Level 3 configuration
    is returned as the default fallback.
    """

    configs = custom_config or DEFAULT_LEVEL_CONFIG

    # Default to Level 3 if level is not found
    return configs.get(level, configs.get(3))


def get_level_weights(
    level: int,
    custom_config: Dict[int, Any] = None
) -> Dict[str, float]:
    """
    Returns scoring weights for the specified level.
    """
    return get_level_config(
        level,
        custom_config
    )["weights"]


def get_level_thresholds(
    level: int,
    custom_config: Dict[int, Any] = None
) -> Dict[str, float]:
    """
    Returns expected feature thresholds for the specified level.
    """
    return get_level_config(
        level,
        custom_config
    )["thresholds"]


# ------------------------------------------------------------------
# Score-to-Gamification Mapping
#
# Purpose:
# Converts numerical handwriting scores into user-friendly
# achievement indicators.
#
# Output:
# - Grade
# - Star Rating
#
# These values are used by the UI for:
# - Progress displays
# - Achievement badges
# - Reward systems
# - Motivation feedback
# ------------------------------------------------------------------

def map_score_to_signals(
    score: float
) -> Dict[str, Any]:
    """
    Maps a 0–100 score to gamification signals.
    """

    if score >= 90:
        return {
            "grade": "A+",
            "stars": 5
        }

    elif score >= 80:
        return {
            "grade": "A",
            "stars": 4
        }

    elif score >= 70:
        return {
            "grade": "B",
            "stars": 3
        }

    elif score >= 60:
        return {
            "grade": "C",
            "stars": 2
        }

    elif score >= 50:
        return {
            "grade": "D",
            "stars": 1
        }

    else:
        return {
            "grade": "Needs Practice",
            "stars": 0
        }


# ------------------------------------------------------------------
# Gamification Signal Application
#
# Purpose:
# Attaches gamified performance indicators to the final
# handwriting analysis result.
#
# Expected Workflow:
#
# Feature Extraction
#        ↓
# Validation
#        ↓
# Normalization
#        ↓
# Confidence Estimation
#        ↓
# Scoring
#        ↓
# History Smoothing
#        ↓
# Gamification   ← This module
#        ↓
# Feedback Engine
#
# The smoothed score is preferred because it reduces sudden
# fluctuations between sessions and provides a more stable
# learner experience.
# ------------------------------------------------------------------

def apply_gamification_signals(
    features: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Wraps the gamification logic to extract the final
    smoothed score and map it to UI signals.

    Note:
    Score smoothing should already have been applied
    by user_history.py before this step.
    """

    scores = features.get("scores", {})

    # --------------------------------------------------------------
    # Prefer the smoothed score if available.
    # Fallback to overall score otherwise.
    # --------------------------------------------------------------
    final_score = scores.get(
        "smoothed_score",
        scores.get("overall_score", 0.0)
    )

    # Convert numerical score into stars and grade
    signals = map_score_to_signals(final_score)

    # Retrieve existing gamification data if present
    gamification_data = features.get(
        "gamification",
        {}
    )

    # Add UI-friendly achievement indicators
    gamification_data["stars"] = signals["stars"]
    gamification_data["grade"] = signals["grade"]

    # Store gamification results back into features
    features["gamification"] = gamification_data

    return features
