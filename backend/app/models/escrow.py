import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class Escrow(Base):
    __tablename__ = "escrows"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organizer_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    agent_coordinate = Column(String, nullable=False, index=True)
    event_id = Column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=True)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=True)
    team_id = Column(Uuid(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    amount_sats = Column(Integer, nullable=False)
    rail = Column(String, nullable=False, default="lightning")
    # draft | awaiting_funding | funded | active | release_pending | released
    # cancelled | refund_pending | refunded | disputed | failed | expired
    status = Column(String, nullable=False, default="draft")
    release_policy = Column(JSON, nullable=False)
    refund_policy = Column(JSON, nullable=False)
    dispute_policy = Column(JSON, nullable=False)
    funding_request = Column(String, nullable=True)
    nwc_uri = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    funded_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
