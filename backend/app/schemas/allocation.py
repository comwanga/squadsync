from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.taxonomy import CONCRETE_STRENGTHS


class AllocationConfigIn(BaseModel):
    role_constraints: dict[str, int] = Field(default_factory=dict)

    @field_validator("role_constraints")
    @classmethod
    def validate_role_constraints(cls, value: dict[str, int]) -> dict[str, int]:
        invalid_roles = set(value) - set(CONCRETE_STRENGTHS)
        if invalid_roles:
            raise ValueError(f"Unknown strength categories: {', '.join(sorted(invalid_roles))}")
        if any(count < 1 or count > 10 for count in value.values()):
            raise ValueError("Role constraint counts must be between 1 and 10")
        return value


class AllocationConfigOut(BaseModel):
    id: UUID
    event_id: UUID
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
    rationale: Optional[dict] = None

    model_config = {"from_attributes": True}


class AllocationOut(BaseModel):
    id: UUID
    event_id: UUID
    snapshot_hash: str
    status: str
    constraint_warnings: dict
    ai_normalized: int = 0
    auto_normalized: int = 0
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
    rationale: Optional[dict] = None


class PublicPayoutSummary(BaseModel):
    team_label: str
    total_sats: int
    status: str
    paid_count: int
    member_count: int


class PublicAllocationOut(BaseModel):
    id: UUID
    status: str
    teams: list[PublicTeam] = []
    payouts: list[PublicPayoutSummary] = []


class FindTeamRequest(BaseModel):
    email: EmailStr


class MemberMove(BaseModel):
    team_id: UUID
