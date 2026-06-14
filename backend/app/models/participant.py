import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Enum as SAEnum, DateTime, JSON, Uuid, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_participant_event_email"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    experience_level = Column(
        SAEnum("beginner", "intermediate", "advanced", name="experience_level"),
        nullable=False,
    )
    primary_strength = Column(
        SAEnum(
            "technical", "design", "planning", "coordination",
            "communication", "research", "domain_expert", "other",
            name="primary_strength",
        ),
        nullable=False,
    )
    strength_other = Column(String, nullable=True)
    normalized_strength = Column(String, nullable=True)
    strength_source = Column(String, nullable=False, default="preset")
    tech_stack = Column(JSON, nullable=False, default=list)
    interests = Column(JSON, nullable=False, default=list)
    composite_score = Column(Float, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
