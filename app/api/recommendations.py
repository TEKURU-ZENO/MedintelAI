"""
app/api/recommendations.py — Recommendation API (Phase 5)

Thin handlers only. All logic in recommendation_engine.py.

Routes:
  GET  /recommendations/full        → FullRecommendationResponse
  GET  /recommendations/session     → SessionPlan
  POST /recommendations/feedback    → RecommendationFeedbackResponse
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.recommendation_feedback import RecommendationFeedback
from app.schemas.recommendations import (
    FullRecommendationResponse,
    SessionPlan,
    RecommendationFeedbackRequest,
    RecommendationFeedbackResponse,
)
from app.services.ml.recommendation_engine import get_full_recommendation

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/full", response_model=FullRecommendationResponse)
def recommendations_full(
    module_type: str = Query(default="alphabet_practice"),
    db:          Session = Depends(get_db),
    current_user: User   = Depends(get_current_user),
):
    """Full recommendation: style + difficulty + items + session plan."""
    return get_full_recommendation(current_user.id, current_user, db, module_type)


@router.get("/session", response_model=SessionPlan)
def recommendations_session(
    module_type: str = Query(default="alphabet_practice"),
    db:          Session = Depends(get_db),
    current_user: User   = Depends(get_current_user),
):
    """Session plan only — for Practice page auto-setup."""
    result = get_full_recommendation(current_user.id, current_user, db, module_type)
    return result["session_plan"]


@router.post("/feedback", response_model=RecommendationFeedbackResponse)
def recommendations_feedback(
    payload:      RecommendationFeedbackRequest,
    db:           Session = Depends(get_db),
    current_user: User    = Depends(get_current_user),
):
    """
    Store recommendation feedback (accepted/skipped/completed).
    This is the ML goldmine — future training data.
    """
    fb = RecommendationFeedback(
        user_id          = current_user.id,
        item             = payload.item,
        module_type      = payload.module_type,
        action           = payload.action,
        outcome_accuracy = payload.outcome_accuracy,
    )
    db.add(fb)
    db.commit()
    return RecommendationFeedbackResponse(
        stored  = True,
        message = f"Feedback stored: {payload.action} on {payload.item}",
    )
