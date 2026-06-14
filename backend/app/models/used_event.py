from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func

from app.core.database import Base


class UsedAuthEvent(Base):
    """Records NIP-98 auth event IDs that have already been consumed.

    A second login attempt presenting the same signed event is a replay and is
    rejected. Rows older than the validity window can be pruned freely.
    """

    __tablename__ = "used_auth_events"

    event_id = Column(String(64), primary_key=True)
    used_at = Column(DateTime(timezone=True), server_default=func.now())
