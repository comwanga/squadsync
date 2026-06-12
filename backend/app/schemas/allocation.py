from typing import Optional
from pydantic import BaseModel


class AllocationConfigIn(BaseModel):
    weight_experience: float = 0.5
    weight_skill: float = 0.5
    role_constraints: dict[str, int] = {}


class AllocationConfigOut(BaseModel):
    id: str
    event_id: str
    weight_experience: float
    weight_skill: float
    role_constraints: dict

    model_config = {"from_attributes": True}


class TeamMemberOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    skill_level: str
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class TeamOut(BaseModel):
    id: str
    allocation_id: str
    name: str
    fairness_score: Optional[float]
    skill_score: Optional[float]
    role_balance_score: Optional[float]
    members: list[TeamMemberOut] = []

    model_config = {"from_attributes": True}


class AllocationOut(BaseModel):
    id: str
    event_id: str
    snapshot_hash: str
    status: str
    constraint_warnings: dict
    teams: list[TeamOut] = []

    model_config = {"from_attributes": True}
