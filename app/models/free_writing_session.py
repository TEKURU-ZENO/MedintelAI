"""
app/models/free_writing_session.py — Free Writing Session Model

Separate domain model from PracticeSession — no target_item, no difficulty.
Stores full writing quality telemetry, emotional snapshot, intent, and thumbnail.

Additions from product review:
  - session_intent: "journaling" | "practice" | "doodling" | "warmup" | "story"
  - emotional_state_snapshot: JSONB (frustration, confidence, fatigue, replay_dependency)
  - thumbnail_path: str (path to canvas PNG snapshot)
  - soft_goal: str | None (user's optional pre-session goal)
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class FreeWritingSession(Base):
    __tablename__ = "free_writing_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # ── Session Intent (Addition 1) ────────────────────────────────────────────
    session_intent = Column(
        String(50),
        nullable=True,
        default="practice",
        comment="User-selected intent: journaling | practice | doodling | warmup | story"
    )

    # ── Soft Goal (Addition 4) ─────────────────────────────────────────────────
    soft_goal = Column(
        String(100),
        nullable=True,
        comment="Optional pre-session goal: smoother_writing | spacing | confidence | free_drawing | storytelling"
    )

    # ── Raw Telemetry ──────────────────────────────────────────────────────────
    stroke_data = Column(JSONB, nullable=True, comment="Raw stroke arrays from canvas")
    duration_seconds = Column(Integer, nullable=True)
    stroke_count = Column(Integer, nullable=True, default=0)
    canvas_width = Column(Integer, nullable=True, default=400)
    canvas_height = Column(Integer, nullable=True, default=400)

    # ── Computed Quality Metrics ───────────────────────────────────────────────
    quality_metrics = Column(JSONB, nullable=True, comment="Full WritingQualityReport JSON")
    overall_score = Column(Float, nullable=True, comment="Composite quality score [0-1]")
    quality_band = Column(
        String(20),
        nullable=True,
        comment="developing | building | strong | exceptional"
    )
    primary_strength = Column(String(50), nullable=True)
    primary_focus_area = Column(String(50), nullable=True)

    # ── Emotional State Snapshot (Addition 2) ─────────────────────────────────
    emotional_state_snapshot = Column(
        JSONB,
        nullable=True,
        comment="Snapshot at session end: frustration_index, confidence_level, fatigue_estimate, replay_dependency"
    )

    # ── Session Thumbnail (Addition 3) ────────────────────────────────────────
    thumbnail_path = Column(
        String(500),
        nullable=True,
        comment="Relative path to canvas PNG thumbnail (e.g. thumbnails/session_uuid.png)"
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status = Column(String(20), nullable=False, default="active", comment="active | completed | abandoned")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    user = relationship("User", back_populates="free_writing_sessions")

    def __repr__(self) -> str:
        return f"<FreeWritingSession id={self.id} user={self.user_id} band={self.quality_band}>"
