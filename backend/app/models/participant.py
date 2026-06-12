import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SAEnum, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class Participant(Base):
    __tablename__ = "participants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    skill_level = Column(
        SAEnum("beginner", "intermediate", "advanced", "professional", name="skill_level"),
        nullable=False,
    )
    role = Column(
        SAEnum(
            "frontend", "backend", "fullstack", "ai_ml", "ux", "devops",
            "blockchain", "mobile", "product", "marketing", name="participant_role",
        ),
        nullable=False,
    )
    years_experience = Column(Integer, nullable=False, default=0)
    tech_stack = Column(ARRAY(String), nullable=False, default=list)
    interests = Column(ARRAY(String), nullable=False, default=list)
    composite_score = Column(Float, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
