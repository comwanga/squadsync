import uuid
from sqlalchemy import Column, Text, ForeignKey, DateTime, Uuid
from sqlalchemy.sql import func

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
