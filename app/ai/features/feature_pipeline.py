import numpy as np
from typing import Dict, Any, List

# ------------------------------------------------------------------
# Feature Extraction Pipeline
#
# Purpose:
# Main orchestration layer responsible for executing the complete
# handwriting analysis workflow.
#
# Pipeline Stages:
# 1. Feature Extraction
# 2. Validation
# 3. Normalization
# 4. Confidence Estimation
# 5. Adaptive Scoring
# 6. Historical Score Smoothing
# 7. Gamification
# 8. Feedback Generation
# 9. Text-to-Speech Coaching
#
# Input:
# - Preprocessed handwriting image
# - Segmentation output (lines, words, characters)
# - Configuration settings
#
# Output:
# - Fully enriched handwriting analysis result containing:
#   - Features
#   - Scores
#   - Confidence
#   - Feedback
#   - Gamification signals
#   - Audio coaching metadata
# ------------------------------------------------------------------

from app.ai.features.line_features import extract_line_features
from app.ai.features.word_features import extract_word_features
from app.ai.features.spacing_features import extract_spacing_features
from app.ai.features.slant_features import extract_slant_features
from app.ai.features.stroke_features import extract_stroke_features
from app.ai.features.character_features import extract_character_features
from app.ai.features.baseline_features import extract_baseline_features
from app.ai.features.feature_schema import build_feature_schema

from app.ai.intelligence.validation import validate_features
from app.ai.intelligence.normalization import normalize_features
from app.ai.intelligence.confidence import estimate_confidence
from app.ai.intelligence.scoring import score_features
from app.ai.intelligence.feedback_engine import generate_feedback

from app.ai.learning.gamification import (
    get_level_weights,
    apply_gamification_signals,
    get_level_thresholds
)

from app.ai.learning.user_history import UserHistoryManager
from app.ai.tts.audio_feedback import apply_tts
from datetime import datetime

from app.ai.utils.logger import get_logger

# Logger used for pipeline monitoring and debugging
logger = get_logger(__name__)

# Tracks historical user performance and score smoothing
history_manager = UserHistoryManager()


def run_feature_extraction_pipeline(
    image: np.ndarray,
    structured_data: Dict[str, Any],
    config: Dict[str, Any],
    image_id: str = "unknown"
) -> Dict[str, Any]:
    """
    Executes the complete handwriting feature extraction
    and intelligence pipeline.

    Args:
        image (np.ndarray):
            Preprocessed binary handwriting image.

        structured_data (Dict):
            Segmentation output containing lines,
            words, characters, and related metadata.

        config (Dict):
            Pipeline configuration and user settings.

        image_id (str):
            Identifier used in the final output schema.

    Returns:
        Dict:
            Fully processed handwriting analysis result.
    """

    logger.info(f"Starting feature extraction for {image_id}")

    # --------------------------------------------------------------
    # Retrieve segmented lines from segmentation output
    # --------------------------------------------------------------
    lines = structured_data.get("lines", [])

    # ==============================================================
    # FEATURE EXTRACTION LAYER
    # ==============================================================

    # --------------------------------------------------------------
    # Line-Level Features
    # Examples:
    # - Line height
    # - Line consistency
    # - Structural measurements
    # --------------------------------------------------------------
    lf1 = extract_line_features(
        lines,
        config.get("line_features", {})
    )

    # --------------------------------------------------------------
    # Baseline Features
    # Examples:
    # - Baseline drift
    # - Writing alignment
    # --------------------------------------------------------------
    lf2 = extract_baseline_features(
        lines,
        config.get("baseline_features", {})
    )

    # Merge all line-related features
    line_features = {**lf1, **lf2}

    # --------------------------------------------------------------
    # Word-Level Features
    # Examples:
    # - Word width
    # - Word distribution
    # --------------------------------------------------------------
    wf1 = extract_word_features(
        lines,
        config.get("word_features", {})
    )

    # --------------------------------------------------------------
    # Spacing Features
    # Examples:
    # - Inter-word spacing
    # - Consistency of spacing
    # --------------------------------------------------------------
    wf2 = extract_spacing_features(
        lines,
        config.get("spacing_features", {})
    )

    # Merge all word-related features
    word_features = {**wf1, **wf2}

    # --------------------------------------------------------------
    # Character and Stroke Features
    # --------------------------------------------------------------

    # Character slant estimation
    cf1 = extract_slant_features(
        image,
        config.get("slant_features", {})
    )

    # Stroke thickness and density
    cf2 = extract_stroke_features(
        image,
        config.get("stroke_features", {})
    )

    # Character-level structural analysis
    cf3 = extract_character_features(
        structured_data,
        config.get("character_features", {})
    )

    # Merge all character-level features
    character_features = {**cf1, **cf2, **cf3}

    # ==============================================================
    # RAW FEATURE SCHEMA
    # ==============================================================

    # Package extracted features into standard JSON schema
    raw_result = build_feature_schema(
        image_id,
        line_features,
        word_features,
        character_features
    )

    # ==============================================================
    # INTELLIGENCE LAYERS
    # ==============================================================

    # --------------------------------------------------------------
    # 1. Validation Layer
    #
    # Verifies required fields, ranges, and schema integrity.
    # --------------------------------------------------------------
    validated_result = validate_features(raw_result)

    # --------------------------------------------------------------
    # 2. Normalization Layer
    #
    # Converts raw feature values into normalized scales
    # for consistent scoring.
    # --------------------------------------------------------------
    normalized_result = normalize_features(validated_result)

    # --------------------------------------------------------------
    # 3. Confidence Estimation
    #
    # Estimates reliability of extracted features based on
    # image quality and segmentation quality.
    # --------------------------------------------------------------
    confidence_result = estimate_confidence(
        normalized_result,
        structured_data
    )

    # ==============================================================
    # ADAPTIVE SCORING SYSTEM
    # ==============================================================

    # Current learner level
    user_level = config.get("level", 2)

    # Retrieve scoring weights for this level
    level_weights = get_level_weights(user_level)

    # Retrieve threshold overrides for this level
    level_thresholds = get_level_thresholds(user_level)

    # Build scoring configuration
    scoring_config = config.get("scoring", {})
    scoring_config["weights"] = level_weights

    # Inject adaptive threshold values
    scoring_config.update(level_thresholds)

    # --------------------------------------------------------------
    # 4. Scoring Layer
    #
    # Produces category scores and overall handwriting score.
    # --------------------------------------------------------------
    scored_result = score_features(
        confidence_result,
        scoring_config
    )

    # ==============================================================
    # HISTORY & SCORE SMOOTHING
    # ==============================================================

    # User identifier used for historical analysis
    user_id = config.get("user_id", "anonymous")

    # Update performance history and calculate smoothed score
    history_result = history_manager.update_history_and_smooth_score(
        user_id=user_id,
        new_score=scored_result["scores"]["overall_score"],
        timestamp=datetime.now().isoformat()
    )

    # Store smoothed score
    scored_result["scores"]["smoothed_score"] = (
        history_result["smoothed_score"]
    )

    # ==============================================================
    # GAMIFICATION LAYER
    # ==============================================================

    # Add XP, achievements, badges, progression indicators
    gamified_result = apply_gamification_signals(scored_result)

    # Add improvement information if performance increased
    if history_result["is_improvement"]:
        gamified_result["gamification"]["improvement_message"] = (
            history_result["improvement_message"]
        )
        gamified_result["gamification"]["improvement"] = True
    else:
        gamified_result["gamification"]["improvement"] = False

    # ==============================================================
    # FEEDBACK ENGINE
    # ==============================================================

    # Generate personalized feedback and recommendations
    final_result = generate_feedback(
        gamified_result,
        config.get("feedback", {})
    )

    # --------------------------------------------------------------
    # Inject positive improvement message into feedback list
    # --------------------------------------------------------------
    if gamified_result["gamification"]["improvement"]:
        final_result["feedback"]["issues"].insert(
            0,
            {
                "issue": "improvement",
                "severity": "Positive",
                "message": history_result["improvement_message"],
                "score_impact": 0
            }
        )

    # ==============================================================
    # TEXT-TO-SPEECH COACHING
    # ==============================================================

    # Generate spoken coaching feedback metadata/audio
    final_result = apply_tts(final_result)

    logger.info(
        "Feature extraction and intelligence layers completed"
    )

    return final_result
