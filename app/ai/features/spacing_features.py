from typing import Dict, List, Any
import numpy as np

# ------------------------------------------------------------------
# Spacing Feature Extraction
#
# Purpose:
# Computes inter-word spacing characteristics from segmented
# handwriting data.
#
# These features help evaluate:
# - Writing readability
# - Word separation quality
# - Consistency of spacing throughout the text
#
# Input:
# - structured_lines:
#     Output from the segmentation pipeline containing lines
#     and word bounding boxes.
#
# - config:
#     Configuration dictionary for enabling/disabling the
#     spacing feature module and future parameters.
#
# Output:
# - median_inter_word_spacing:
#     Typical gap between consecutive words.
#
# - spacing_consistency:
#     Standard deviation of word spacing values.
#     Lower values indicate more consistent spacing.
# ------------------------------------------------------------------

def extract_spacing_features(
    structured_lines: List[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, float]:
    """
    Computes inter-word spacing features.
    """

    # --------------------------------------------------------------
    # Skip processing if spacing feature extraction is disabled.
    # --------------------------------------------------------------
    if not config.get('enabled', True):
        return {}

    # Stores all valid spacing measurements
    spacings = []

    # --------------------------------------------------------------
    # Process each segmented text line
    # --------------------------------------------------------------
    for line in structured_lines:

        # Retrieve words detected in the line
        words = line.get("words", [])

        # ----------------------------------------------------------
        # Ensure words are ordered from left to right based on
        # their X-coordinate position.
        # ----------------------------------------------------------
        sorted_words = sorted(
            words,
            key=lambda w: w["bbox"]["x"]
        )

        # ----------------------------------------------------------
        # Calculate spacing between consecutive words
        # ----------------------------------------------------------
        for i in range(1, len(sorted_words)):

            # Previous word bounding box
            prev = sorted_words[i - 1]["bbox"]

            # Current word bounding box
            curr = sorted_words[i]["bbox"]

            # ------------------------------------------------------
            # Gap calculation:
            #
            # Previous word ends at:
            # prev["x"] + prev["width"]
            #
            # Current word begins at:
            # curr["x"]
            #
            # Gap = start(current) - end(previous)
            # ------------------------------------------------------
            gap = curr["x"] - (
                prev["x"] + prev["width"]
            )

            # Only positive gaps are considered valid spacing
            if gap > 0:
                spacings.append(gap)

    # --------------------------------------------------------------
    # Compute spacing statistics
    # --------------------------------------------------------------
    features = {}

    if spacings:

        # Median spacing reduces sensitivity to outliers
        features["median_inter_word_spacing"] = float(
            np.median(spacings)
        )

        # Standard deviation measures consistency
        # Lower value = more uniform spacing
        features["spacing_consistency"] = float(
            np.std(spacings)
        )

    else:

        # Fallback values when no spacing data exists
        features["median_inter_word_spacing"] = 0.0
        features["spacing_consistency"] = 0.0

    return features
