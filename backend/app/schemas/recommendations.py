"""app/schemas/recommendations.py — Recommendation DTOs"""

from pydantic import BaseModel
from typing import Literal


class ItemRecommendation(BaseModel):
    item:           str
    priority_score: float
    reason:         str
    priority:       Literal["high", "medium", "low"]
    confidence:     float
    source:         str


class SessionPlan(BaseModel):
    items:            list[str]
    session_length_s: int
    focus_mode:       Literal["standard", "deep_focus", "confidence_boost", "quick_win"]
    reasoning:        str
    difficulty:       str
    confidence:       float
    source:           str
    learning_style:   str
    session_config:   str
    audio_metadata:   dict | None = None


class FullRecommendationResponse(BaseModel):
    learning_style:          str
    style_label:             str
    style_recommendation:    str
    style_confidence:        float
    style_source:            str
    recommended_difficulty:  str
    difficulty_confidence:   float
    difficulty_source:       str
    recommended_items:       list[ItemRecommendation]
    session_plan:            SessionPlan
    data_completeness:       float
    overall_confidence:      float
    source:                  str


class RecommendationFeedbackRequest(BaseModel):
    recommendation_id: str | None = None
    item:              str
    action:            Literal["accepted", "skipped", "completed"]
    outcome_accuracy:  float | None = None   # accuracy achieved if completed
    module_type:       str = "alphabet_practice"


class RecommendationFeedbackResponse(BaseModel):
    stored:  bool
    message: str
