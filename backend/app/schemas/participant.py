from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class ParticipantRegister(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    skill_level: str
    role: str
    years_experience: int = 0
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
