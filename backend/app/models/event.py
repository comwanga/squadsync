import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SAEnum, DateTime, Text, Uuid
from sqlalchemy.sql import func

from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    event_at = Column(DateTime(timezone=False), nullable=True)
    participant_limit = Column(Integer, nullable=True)
    team_count = Column(Integer, nullable=False)
    status = Column(
        SAEnum("draft", "active", "allocated", "archived", name="event_status"),
        nullable=False,
        default="draft",
    )
    registration_slug = Column(String, unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EventCoOrganizer(Base):
    __tablename__ = "event_co_organizers"

    event_id = Column(Uuid(as_uuid=True), ForeignKey("events.id"), primary_key=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    invited_at = Column(DateTime(timezone=True), server_default=func.now())
