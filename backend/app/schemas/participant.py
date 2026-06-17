from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
from app.services.nostr_service import validate_npub

ExperienceLevel = Literal["beginner", "intermediate", "advanced"]
PrimaryStrength = Literal[
    "technical", "design", "planning", "coordination",
    "communication", "research", "domain_expert", "other",
]


class ParticipantRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    primary_strength: PrimaryStrength
    strength_other: Optional[str] = Field(default=None, max_length=120)
    experience_level: ExperienceLevel
    npub: Optional[str] = None
    tech_stack: list[str] = []
    interests: list[str] = []

    @model_validator(mode="after")
    def _require_other_text(self):
        if self.primary_strength == "other" and not (self.strength_other and self.strength_other.strip()):
            raise ValueError("Please describe your strength when choosing 'Other'.")
        return self

    @field_validator("npub", mode="before")
    @classmethod
    def _normalize_npub(cls, v):
        if v is None:
            return None
        v = str(v).strip().lower()
        if not v:
            return None
        validate_npub(v)  # raises ValueError (→ 422) if malformed
        return v


class ParticipantOut(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    email: str
    phone: Optional[str]
    primary_strength: str
    strength_other: Optional[str]
    normalized_strength: Optional[str]
    strength_source: str
    experience_level: str
    npub: Optional[str]
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class ParticipantCategoryUpdate(BaseModel):
    normalized_strength: str = Field(min_length=1, max_length=120)


class EventPublicInfo(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    status: str

    model_config = {"from_attributes": True}
