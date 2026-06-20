import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class Payout(Base):
    __tablename__ = "payouts"
    # One payout per team per allocation: the authoritative guard against paying
    # a winning team twice (double-click, client retry). Re-attempts go through
    # the retry endpoint, which reuses the existing payout's items.
    __table_args__ = (
        UniqueConstraint("allocation_id", "team_label", name="uq_payout_allocation_team"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    team_label = Column(String, nullable=False)
    total_sats = Column(Integer, nullable=False)
    # pending | partial | complete | failed
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PayoutItem(Base):
    __tablename__ = "payout_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payout_id = Column(Uuid(as_uuid=True), ForeignKey("payouts.id"), nullable=False, index=True)
    participant_id = Column(Uuid(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    lightning_address = Column(String, nullable=True)
    amount_sats = Column(Integer, nullable=False)
    # pending | paid | failed | unverified (wallet preimage did not match the invoice)
    status = Column(String, nullable=False, default="pending")
    bolt11 = Column(String, nullable=True)
    preimage = Column(String, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
