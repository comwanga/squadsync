from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

SkillLevel = Literal["beginner", "intermediate", "advanced", "professional"]
ParticipantRole = Literal[
    "frontend", "backend", "fullstack", "ai_ml", "ux", "devops",
    "blockchain", "mobile", "product", "marketing",
]


class ParticipantRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    skill_level: SkillLevel
    role: ParticipantRole
    years_experience: int = Field(default=0, ge=0, le=60)
    tech_stack: list[str] = []
    interests: list[str] = []


class ParticipantOut(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    email: str
    phone: Optional[str]
    skill_level: str
    role: str
    years_experience: int
    tech_stack: list[str]
    interests: list[str]
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class EventPublicInfo(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    status: str

    model_config = {"from_attributes": True}
