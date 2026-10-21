"""
app/models/recommendation_feedback.py — Feedback Storage

Stores: what was recommended, what user did, and outcome delta.
This is the ML goldmine — future training labels come from here.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.core.database import Base


class RecommendationFeedback(Base):
    __tablename__ = "recommendation_feedback"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # What was recommended
    item        = Column(String, nullable=False)          # e.g. "S"
    module_type = Column(String, nullable=False)
    focus_mode  = Column(String, nullable=True)           # session plan's mode
    source      = Column(String, nullable=True)           # "rule" | "ml"

    # What user did
    action = Column(String, nullable=False)               # accepted | skipped | completed

    # Outcome (filled when action=completed)
    outcome_accuracy = Column(Float, nullable=True)       # 0.0–1.0

    # Shadow delta (stored for future ML training)
    rule_prediction = Column(String, nullable=True)
    ml_prediction   = Column(String, nullable=True)
    ml_confidence   = Column(Float, nullable=True)
    predictions_agreed = Column(Boolean, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
