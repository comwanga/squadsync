import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class TeamNotification(Base):
    """One row per successfully-sent team DM, deduped on (allocation_id, participant_id)."""
    __tablename__ = "team_notifications"
    __table_args__ = (
        UniqueConstraint("allocation_id", "participant_id", name="uq_team_notification"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    participant_id = Column(Uuid(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
