"""
app/schemas/analytics.py — Analytics DTOs

All analytics API responses use these typed models.
InsightItem is the atomic unit of all intelligence output.
Never expose raw DB rows.
"""

from pydantic import BaseModel
from typing import Literal


# ──────────────────────────────────────────────────────────────────────────────
# Core: InsightItem (Upgrade #1 — structured, localizable, ML-ready)
# ──────────────────────────────────────────────────────────────────────────────

class InsightItem(BaseModel):
    """
    Atomic unit of educational intelligence.
    code:     machine-stable key (never changes — safe for filtering/ML)
    severity: visual treatment in UI
    message:  human-readable text
    """
    code:     str
    severity: Literal["positive", "low", "medium", "high"]
    message:  str


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard summary (home screen analytics card)
# ──────────────────────────────────────────────────────────────────────────────

class DashboardSummaryResponse(BaseModel):
    current_streak:        int
    streak_status:         Literal["active", "at_risk", "broken"]
    engagement_level:      Literal["high", "medium", "low"]
    confidence_level:      Literal["high", "medium", "low", "unknown"]
    frustration_level:     Literal["high", "medium", "low"]
    rolling_accuracy:      float                            # 0.0–1.0
    accuracy_trend:        Literal["improving", "stable", "declining"]
    current_difficulty:    str
    promotion_readiness:   float                            # 0.0–1.0
    total_sessions:        int
    total_xp:              int
    level:                 int
    active_days_this_week: int


# ──────────────────────────────────────────────────────────────────────────────
# Progress report (per-module accuracy trends)
# ──────────────────────────────────────────────────────────────────────────────

class ProgressTrendResponse(BaseModel):
    module_type:    str
    weekly_accuracy: list[float]    # last 4 weeks, oldest first
    trend:          Literal["improving", "stable", "declining"]
    velocity:       Literal["fast", "steady", "slow"]
    rolling_average: float
    best_letters:   list[str]
    worst_letters:  list[str]


# ──────────────────────────────────────────────────────────────────────────────
# Engagement report
# ──────────────────────────────────────────────────────────────────────────────

class EngagementMetricsResponse(BaseModel):
    current_streak:       int
    longest_streak:       int
    streak_status:        Literal["active", "at_risk", "broken"]
    at_risk:              bool
    consistency_score:    float         # 0.0–1.0
    active_days:          int
    total_days_window:    int
    practice_pattern:     Literal["consistent", "weekday_only", "weekend_heavy", "irregular"]
    avg_session_seconds:  float
    abandon_rate:         float         # 0.0–1.0
    engagement_level:     Literal["high", "medium", "low"]


# ──────────────────────────────────────────────────────────────────────────────
# Learning insights (structured intelligence — InsightItem not raw strings)
# ──────────────────────────────────────────────────────────────────────────────

class LearningInsightResponse(BaseModel):
    """
    Structured educational intelligence consumed by InsightsList.tsx.
    Three categories — all using InsightItem for localization + ML readiness.
    """
    strengths:         list[InsightItem]    # severity="positive"
    weaknesses:        list[InsightItem]    # severity="high"|"medium"
    behavioral:        list[InsightItem]    # hesitation, frustration, replay
    confidence_level:  Literal["high", "medium", "low", "unknown"]
    frustration_level: Literal["high", "medium", "low"]
    engagement:        Literal["high", "medium", "low"]


# ──────────────────────────────────────────────────────────────────────────────
# Module performance (ModuleGrid cards)
# ──────────────────────────────────────────────────────────────────────────────

class ModulePerformanceResponse(BaseModel):
    module_type:         str
    label:               str
    sessions_completed:  int
    avg_accuracy:        float
    accuracy_trend:      Literal["improving", "stable", "declining"]
    current_difficulty:  str
    promotion_readiness: float       # 0.0–1.0
    recommended_focus:   Literal[
        "ready_to_advance",
        "needs_more_practice",
        "maintain_consistency",
        "review_basics",
    ]
    last_practiced:      str | None  # ISO date string or null
