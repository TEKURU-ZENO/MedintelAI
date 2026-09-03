from sqlalchemy import Column, Integer, String, Enum, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.core.database import Base
import enum

class InputType(str, enum.Enum):
    IMAGE = "image"
    CANVAS = "canvas"

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    input_type = Column(Enum(InputType, values_callable=lambda x: [e.value for e in x]), nullable=False)

    image_path = Column(String, nullable=True)
    stroke_data = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
