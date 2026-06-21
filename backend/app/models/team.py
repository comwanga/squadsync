import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Uuid, JSON

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    fairness_score = Column(Float, nullable=True)
    skill_score = Column(Float, nullable=True)
    role_balance_score = Column(Float, nullable=True)
    # Cached AI explanation: {"title","summary","strengths":[...],"gaps":[...]} or None.
    rationale = Column(JSON, nullable=True)


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(Uuid(as_uuid=True), ForeignKey("teams.id"), primary_key=True)
    participant_id = Column(Uuid(as_uuid=True), ForeignKey("participants.id"), primary_key=True)
