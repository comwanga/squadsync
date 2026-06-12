from typing import Optional
from pydantic import BaseModel


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    participant_limit: Optional[int] = None
    team_count: int


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    participant_limit: Optional[int] = None
    team_count: Optional[int] = None
    status: Optional[str] = None


class EventOut(BaseModel):
    id: str
    owner_id: str
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    team_count: int
    status: str
    registration_slug: str

    model_config = {"from_attributes": True}


class CoOrganizerInvite(BaseModel):
    email: str
