from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AllocationConfigIn(BaseModel):
    weight_experience: float = 0.5
    weight_skill: float = 0.5
    role_constraints: dict[str, int] = {}


class AllocationConfigOut(BaseModel):
    id: UUID
    event_id: UUID
    weight_experience: float
    weight_skill: float
    role_constraints: dict

    model_config = {"from_attributes": True}


class TeamMemberOut(BaseModel):
    id: UUID
    name: str
    email: str
    normalized_strength: Optional[str]
    experience_level: str
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    id: UUID
    allocation_id: UUID
    name: str
    fairness_score: Optional[float]
    skill_score: Optional[float]
    role_balance_score: Optional[float]
    members: list[TeamMemberOut] = []

    model_config = {"from_attributes": True}


class AllocationOut(BaseModel):
    id: UUID
    event_id: UUID
    snapshot_hash: str
    status: str
    constraint_warnings: dict
    teams: list[TeamOut] = []

    model_config = {"from_attributes": True}


# --- Public (unauthenticated) views: no email or other PII beyond display name/role ---

class PublicTeamMember(BaseModel):
    id: UUID
    name: str
    normalized_strength: Optional[str]
    experience_level: str

    model_config = {"from_attributes": True}


class PublicTeam(BaseModel):
    id: UUID
    name: str
    fairness_score: Optional[float]
    members: list[PublicTeamMember] = []


class PublicAllocationOut(BaseModel):
    id: UUID
    status: str
    teams: list[PublicTeam] = []
