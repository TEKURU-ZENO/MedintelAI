"""
app/api/analytics_v2.py — Analytics API routes (Phase 3.5)

Thin handlers only.
All business logic is in analytics_service.py.
No sub-service is called directly from here.

Routes:
  GET /analytics/summary       → DashboardSummaryResponse
  GET /analytics/progress      → ProgressTrendResponse  (?module_type=...)
  GET /analytics/engagement    → EngagementMetricsResponse
  GET /analytics/insights      → LearningInsightResponse
  GET /analytics/modules       → list[ModulePerformanceResponse]
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    DashboardSummaryResponse,
    ProgressTrendResponse,
    EngagementMetricsResponse,
    LearningInsightResponse,
    ModulePerformanceResponse,
)
from app.services.analytics.analytics_service import (
    get_dashboard_summary,
    get_progress_report,
    get_engagement_report,
    get_learning_insights,
    get_module_performance,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=DashboardSummaryResponse)
def analytics_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Home-screen analytics snapshot.
    Combines streak, engagement, accuracy, difficulty, and confidence.
    """
    return get_dashboard_summary(current_user.id, current_user, db)


@router.get("/progress", response_model=ProgressTrendResponse)
def analytics_progress(
    module_type: str = Query(default="alphabet_practice"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Weekly accuracy trend + learning velocity for a specific module.
    """
    return get_progress_report(current_user.id, module_type, db)


@router.get("/engagement", response_model=EngagementMetricsResponse)
def analytics_engagement(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streak, consistency, session duration, abandon rate.
    """
    return get_engagement_report(current_user.id, current_user, db)


@router.get("/insights", response_model=LearningInsightResponse)
def analytics_insights(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Full behavioral intelligence: structured InsightItems for strengths,
    weaknesses, and behavioral observations.
    """
    return get_learning_insights(current_user.id, current_user, db)


@router.get("/modules", response_model=list[ModulePerformanceResponse])
def analytics_modules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Per-module performance cards with recommended_focus signals.
    """
    return get_module_performance(current_user.id, db)
