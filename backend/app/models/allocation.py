import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Enum as SAEnum, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AllocationConfig(Base):
    __tablename__ = "allocation_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), unique=True, nullable=False)
    weight_experience = Column(Float, nullable=False, default=0.5)
    weight_skill = Column(Float, nullable=False, default=0.5)
    role_constraints = Column(JSONB, nullable=False, default=dict)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Allocation(Base):
    __tablename__ = "allocations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(UUID(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    snapshot_hash = Column(String, nullable=False)
    status = Column(
        SAEnum("draft", "published", name="allocation_status"),
        nullable=False,
        default="draft",
    )
    constraint_warnings = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
