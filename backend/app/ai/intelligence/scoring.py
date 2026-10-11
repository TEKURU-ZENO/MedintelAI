from typing import Dict, Any

# ------------------------------------------------------------------
# Hybrid Score Calculation
#
# Purpose:
# Converts a feature deviation measurement into a normalized
# 0–100 score.
#
# Scoring Philosophy:
# - Smaller deviations produce higher scores.
# - Larger deviations receive progressively lower scores.
# - Scores are clamped between 0 and 100.
#
# Formula:
#
# deviation = std / expected_range
#
# score = 100 - (k × deviation)
#
# where:
# - std = measured variance/deviation
# - expected_range = acceptable variance threshold
# - k = penalty factor controlling score sensitivity
# ------------------------------------------------------------------

def calculate_hybrid_score(
    std: float,
    expected_range: float,
    k: float = 20.0
) -> float:
    """
    Calculates score based on deviation from expected range.

    score = max(0, min(100, 100 - k * deviation))
    """

    # Prevent division by zero
    if expected_range == 0:
        return 100.0

    # Normalize deviation relative to acceptable range
    deviation = std / expected_range

    # Convert deviation into a bounded score
    score = max(
        0.0,
        min(
            100.0,
            100.0 - k * deviation
        )
    )

    return float(score)


# ------------------------------------------------------------------
# Feature Scoring Engine
#
# Purpose:
# Converts extracted handwriting features into numerical
# performance scores.
#
# Output Scores:
# - spacing_score
# - baseline_score
# - stroke_score
# - slant_score
# - raw_overall_score
# - overall_score
#
# Workflow:
# 1. Compute category scores
# 2. Apply configurable weights
# 3. Apply feature-level confidence weighting
# 4. Compute weighted overall score
# 5. Apply global confidence adjustment
# ------------------------------------------------------------------

def score_features(
    features: Dict[str, Any],
    config: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Computes 0-100 scores for various handwriting metrics
    using the hybrid scoring formula.
    """

    # --------------------------------------------------------------
    # Initialize configuration
    # --------------------------------------------------------------
    config = config or {}

    # Controls how aggressively deviations reduce scores
    k_factor = config.get(
        "k_factor",
        25.0
    )

    scores = {}

    # ==============================================================
    # EXPECTED FEATURE RANGES
    #
    # These represent acceptable handwriting variability.
    # Higher deviations beyond these values reduce scores.
    # ==============================================================

    EXPECTED_SPACING_RANGE = config.get(
        "expected_spacing_range",
        0.5
    )

    EXPECTED_STROKE_RANGE = config.get(
        "expected_stroke_range",
        0.2
    )

    EXPECTED_BASELINE_RANGE = config.get(
        "expected_baseline_range",
        5.0
    )

    EXPECTED_SLANT_RANGE = config.get(
        "expected_slant_range",
        10.0
    )

    # ==============================================================
    # SPACING SCORE
    # ==============================================================

    word_features = features.get(
        "word_features",
        {}
    )

    # Standard deviation of inter-word spacing
    spacing_std = word_features.get(
        "spacing_consistency",
        0.0
    )

    scores["spacing_score"] = calculate_hybrid_score(
        spacing_std,
        EXPECTED_SPACING_RANGE,
        k_factor
    )

    # ==============================================================
    # BASELINE SCORE
    # ==============================================================

    line_features = features.get(
        "line_features",
        {}
    )

    # Baseline alignment variation
    baseline_std = line_features.get(
        "baseline_deviation",
        0.0
    )

    scores["baseline_score"] = calculate_hybrid_score(
        baseline_std,
        EXPECTED_BASELINE_RANGE,
        k_factor
    )

    # ==============================================================
    # STROKE & SLANT SCORES
    # ==============================================================

    char_features = features.get(
        "character_features",
        {}
    )

    # Stroke thickness variability
    stroke_std = char_features.get(
        "stroke_variance",
        0.0
    )

    scores["stroke_score"] = calculate_hybrid_score(
        stroke_std,
        EXPECTED_STROKE_RANGE,
        k_factor
    )

    # Character slant variability
    slant_std = char_features.get(
        "slant_variance",
        0.0
    )

    scores["slant_score"] = calculate_hybrid_score(
        slant_std,
        EXPECTED_SLANT_RANGE,
        k_factor
    )

    # ==============================================================
    # OVERALL SCORE CONFIGURATION
    # ==============================================================

    # Default contribution of each handwriting dimension
    default_weights = {
        "spacing": 0.3,
        "baseline": 0.25,
        "stroke": 0.2,
        "slant": 0.25
    }

    # Allow weights to be overridden via configuration
    weights_config = config.get(
        "weights",
        default_weights
    )

    weights = {
        "spacing": weights_config.get(
            "spacing",
            0.3
        ),
        "baseline": weights_config.get(
            "baseline",
            0.25
        ),
        "stroke": weights_config.get(
            "stroke",
            0.2
        ),
        "slant": weights_config.get(
            "slant",
            0.25
        )
    }

    # Sum of configured weights
    total_weight = sum(weights.values())

    # ==============================================================
    # CONFIDENCE METRICS
    #
    # Each feature can have its own confidence score,
    # allowing unreliable measurements to contribute less.
    # ==============================================================

    confidence_metrics = features.get(
        "confidence_metrics",
        {}
    )

    # Overall confidence for the analysis
    confidence_score = confidence_metrics.get(
        "score",
        1.0
    )

    # Feature-specific confidence values
    feature_conf = confidence_metrics.get(
        "features",
        {}
    )

    spacing_conf = feature_conf.get(
        "spacing",
        1.0
    )

    baseline_conf = feature_conf.get(
        "baseline",
        1.0
    )

    stroke_conf = feature_conf.get(
        "stroke",
        1.0
    )

    slant_conf = feature_conf.get(
        "slant",
        1.0
    )

    # ==============================================================
    # CONFIDENCE-WEIGHTED FEATURE SCORES
    # ==============================================================

    w_spacing = (
        scores["spacing_score"]
        * weights["spacing"]
        * spacing_conf
    )

    w_baseline = (
        scores["baseline_score"]
        * weights["baseline"]
        * baseline_conf
    )

    w_stroke = (
        scores["stroke_score"]
        * weights["stroke"]
        * stroke_conf
    )

    w_slant = (
        scores["slant_score"]
        * weights["slant"]
        * slant_conf
    )

    # Effective weight after confidence adjustments
    total_effective_weight = (
        weights["spacing"] * spacing_conf +
        weights["baseline"] * baseline_conf +
        weights["stroke"] * stroke_conf +
        weights["slant"] * slant_conf
    )

    # ==============================================================
    # RAW OVERALL SCORE
    # ==============================================================

    if total_effective_weight > 0:

        overall = (
            w_spacing +
            w_baseline +
            w_stroke +
            w_slant
        ) / total_effective_weight

    else:
        overall = 0.0

    # ==============================================================
    # GLOBAL CONFIDENCE ADJUSTMENT
    #
    # Applies a forgiving confidence curve:
    #
    # multiplier = 0.5 + 0.5 × confidence
    #
    # Confidence 1.0 → 100% score retained
    # Confidence 0.0 → 50% score retained
    # ==============================================================

    final_score = (
        overall *
        (0.5 + 0.5 * confidence_score)
    )

    # Store final results
    scores["overall_score"] = final_score

    # Preserve pre-confidence weighted score
    scores["raw_overall_score"] = overall

    # Attach scores to feature output
    features["scores"] = scores

    return features
