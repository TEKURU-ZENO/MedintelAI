from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base

class Result(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"))

    features = Column(JSONB)
    scores = Column(JSONB)
    feedback = Column(JSONB)

    confidence = Column(Float)
    audio_path = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
