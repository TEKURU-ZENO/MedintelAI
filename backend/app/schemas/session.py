from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Any


# ──────────────────────────────────────────────────────────────────────────────
# Request schemas
# ──────────────────────────────────────────────────────────────────────────────

class SessionStart(BaseModel):
    module_type: str
    target_item: str | None = None
    language: str = "english"
    difficulty: str = "beginner"

    @field_validator("module_type")
    @classmethod
    def validate_module_type(cls, v: str) -> str:
        from app.data.modules.registry import MODULES
        if v not in MODULES:
            raise ValueError(
                f"Unknown module_type '{v}'. Valid: {list(MODULES.keys())}"
            )
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        valid = {"beginner", "intermediate", "advanced"}
        if v not in valid:
            raise ValueError(f"difficulty must be one of {valid}")
        return v


class SessionComplete(BaseModel):
    accuracy_score: float            # 0.0 – 1.0
    detailed_scores: dict | None = None
    duration_seconds: int
    stroke_data: list[dict] | None = None  # raw canvas output
    total_strokes: int | None = None
    total_points: int | None = None

    @field_validator("accuracy_score")
    @classmethod
    def clamp_accuracy(cls, v: float) -> float:
        return max(0.0, min(1.0, v))


class SessionAbandon(BaseModel):
    reason: str | None = None        # "timeout" | "user_exit" | None
    stroke_data: list[dict] | None = None   # save partial stroke data


# ──────────────────────────────────────────────────────────────────────────────
# Response schemas
# ──────────────────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    id: int
    user_id: int
    module_type: str
    target_item: str | None
    language: str
    difficulty: str
    attempt_number: int
    module_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: int | None
    is_completed: bool
    accuracy_score: float | None
    detailed_scores: dict | None
    total_strokes: int | None
    total_points: int | None
    xp_earned: int

    model_config = ConfigDict(from_attributes=True)


class SessionCompleteResponse(BaseModel):
    """Returned after POST /sessions/{id}/complete."""
    session: SessionResponse
    xp_earned: int
    total_xp: int           # user's new total XP
    new_level: int          # user's level after this session
    level_up: bool          # True if user crossed a level boundary
    new_streak: int         # current streak count
    daily_xp_remaining: int # XP user can still earn today


class ModuleItemResponse(BaseModel):
    """A single practice item returned by the module data endpoints."""
    module_type: str
    item: str               # "A", "cat", etc.
    version: str

    model_config = ConfigDict(extra="allow")


class ModuleListResponse(BaseModel):
    """List of available modules for the current user."""
    profile_type: str
    modules: list[dict]


# ──────────────────────────────────────────────────────────────────────────────
# Phase 3: Guidance Event schemas
# ──────────────────────────────────────────────────────────────────────────────

class InactivityAnalytics(BaseModel):
    """Tracks hesitation time — becomes confidence/friction signal."""
    time_before_first_stroke_ms: int | None = None
    pause_between_strokes_ms: list[int] | None = None   # per stroke gap
    total_hesitation_ms: int | None = None


class GuidanceEvent(BaseModel):
    """Sent by frontend after each stroke ends (authoritative backend validation)."""
    event_type: str                  # "stroke_complete" | "stroke_start" | "idle_timeout"
    stroke_id: int                   # 1-indexed stroke order
    drawn_points: list[list[float]]  # [[x, y, t?], ...] normalized 0–100 grid
    reference_stroke_id: int | None = None  # which ref stroke to compare against
    hesitation_ms: int | None = None        # pause before this stroke started
    module_type: str | None = None
    target_item: str | None = None


class StrokeScore(BaseModel):
    """Per-stroke score returned from guidance event."""
    direction_score:          float
    coverage_score:           float
    smoothness_score:         float
    normalized_path_error:    float
    overshoot_ratio:          float
    stroke_velocity_variance: float
    combined_score:           float


class DirectionInfo(BaseModel):
    direction:     str
    confidence:    float
    angle_degrees: float
    displacement:  float


class GuidanceResponse(BaseModel):
    """Returned after POST /sessions/{id}/guidance-event."""
    stroke_id:           int
    scores:              StrokeScore
    direction_detected:  DirectionInfo
    direction_match:     bool           # drawn direction matches expected
    feedback_type:       str            # encouragement | correction | celebration | warning
    feedback_message:    str
    unlock_next_stroke:  bool           # True = frontend unlocks next stroke
    failsafe_unlock:     bool           # True = unlocked because max_attempts reached
    attempt_number:      int            # how many times this stroke has been attempted


class RecommendedDifficultyResponse(BaseModel):
    """Returned by GET /sessions/modules/{type}/recommended-difficulty."""
    difficulty:    str
    current:       str
    promoted:      bool
    demoted:       bool
    avg_accuracy:  float | None
    sessions_used: int
