from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field

EventStatus = Literal["draft", "active", "allocated", "archived"]


class EventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    participant_limit: Optional[int] = Field(default=None, ge=1)
    team_count: int = Field(ge=2)
    event_at: Optional[datetime] = None


class EventUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    participant_limit: Optional[int] = Field(default=None, ge=1)
    team_count: Optional[int] = Field(default=None, ge=2)
    status: Optional[EventStatus] = None
    event_at: Optional[datetime] = None


class EventOut(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: Optional[str]
    event_at: Optional[datetime]
    participant_limit: Optional[int]
    team_count: int
    status: str
    registration_slug: str

    model_config = {"from_attributes": True}


class CoOrganizerInvite(BaseModel):
    pubkey: str
