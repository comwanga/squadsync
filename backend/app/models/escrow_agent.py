import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Uuid, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class EscrowAgentEvent(Base):
    __tablename__ = "escrow_agent_events"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    coordinate = Column(String, unique=True, nullable=False, index=True)
    event_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
