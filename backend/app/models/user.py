import uuid
from sqlalchemy import Column, String, Enum as SAEnum, DateTime, Uuid
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    provider = Column(SAEnum("local", "google", name="user_provider"), nullable=False, default="local")
    provider_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
