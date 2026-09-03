from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class SessionStatus(str, enum.Enum):
    STARTED     = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    ABANDONED   = "abandoned"


class PracticeSession(Base):
    """
    Central fact table for the adaptive learning engine.

    Every learning interaction creates one row here. This table drives:
      - Progress analytics (Phases 4 & 9)
      - ML personalization (Phase 11)
      - Stroke replay / behavioral analysis (Phase 4)
      - Dropout / session recovery analytics
    """
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # ── Who ───────────────────────────────────────────────────────────────────
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # ── What ──────────────────────────────────────────────────────────────────
    module_type   = Column(String, nullable=False)   # alphabet_practice | word_practice | ...
    target_item   = Column(String, nullable=True)    # "A", "cat", "The quick brown fox"
    module_version = Column(String, default="v1", nullable=False)  # tracks data version

    # ── Language & Difficulty ─────────────────────────────────────────────────
    language   = Column(String, default="english", nullable=False)
    difficulty = Column(String, default="beginner", nullable=False)

    # ── Retry tracking ────────────────────────────────────────────────────────
    # Enables "improved after N attempts" analytics and retry coaching
    attempt_number = Column(Integer, default=1, nullable=False)

    # ── Session lifecycle status ──────────────────────────────────────────────
    status = Column(
        SAEnum(SessionStatus, name="session_status_enum", values_callable=lambda x: [e.value for e in x]),
        default=SessionStatus.STARTED,
        nullable=False,
    )

    # ── Timing ────────────────────────────────────────────────────────────────
    started_at       = Column(DateTime(timezone=True), server_default=func.now())
    completed_at     = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # ── Outcome ───────────────────────────────────────────────────────────────
    is_completed   = Column(Boolean, default=False)
    attempts       = Column(Integer, default=0)
    accuracy_score = Column(Float, nullable=True)

    # Per-dimension scores: {"formation": 0.8, "smoothness": 0.7, "direction": 0.9}
    detailed_scores = Column(JSONB, nullable=True)

    # ── Raw stroke data (GOLD for ML + replay) ────────────────────────────────
    # Format: [{"id": 1, "points": [[x,y,t], ...], "pressure": [...]}]
    # Stored even for incomplete sessions — valuable behavioral signal
    stroke_data = Column(JSONB, nullable=True)

    # ── Performance metrics ───────────────────────────────────────────────────
    total_strokes = Column(Integer, nullable=True)   # number of distinct strokes drawn
    total_points  = Column(Integer, nullable=True)   # total coordinate points captured

    # ── Reward ────────────────────────────────────────────────────────────────
    xp_earned = Column(Integer, default=0)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
