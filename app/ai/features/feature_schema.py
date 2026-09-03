from typing import Dict, Any

# ------------------------------------------------------------------
# Feature Schema Builder
#
# Purpose:
# Creates a standardized JSON-compatible structure for storing
# extracted handwriting features from an image.
#
# Parameters:
# - image_id: Unique identifier of the processed image.
# - line_features: Features extracted at the line level
#                  (e.g., baseline alignment, line spacing).
# - word_features: Features extracted at the word level
#                  (e.g., word spacing, word width).
# - character_features: Features extracted at the character level
#                       (e.g., slant, stroke thickness, shape metrics).
#
# Returns:
# A dictionary following the project feature schema format.
#
# Example Output:
# {
#     "schema_version": "1.0",
#     "image_id": "sample_001",
#     "line_features": {...},
#     "word_features": {...},
#     "character_features": {...}
# }
# ------------------------------------------------------------------

from typing import Dict, Any

def build_feature_schema(
    image_id: str,
    line_features: dict,
    word_features: dict,
    character_features: dict
) -> Dict[str, Any]:
    """
    Packages all extracted handwriting features into a
    standardized JSON schema.
    """

    return {
        # Schema version used for compatibility and future upgrades
        "schema_version": "1.0",

        # Unique identifier of the processed image
        "image_id": image_id,

        # Line-level handwriting features
        "line_features": line_features,

        # Word-level handwriting features
        "word_features": word_features,

        # Character-level handwriting features
        "character_features": character_features
    }
