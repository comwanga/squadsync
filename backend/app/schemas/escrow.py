from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class EscrowCreate(BaseModel):
    agent_coordinate: str = Field(min_length=1)
    event_id: Optional[UUID] = None
    allocation_id: Optional[UUID] = None
    team_id: Optional[UUID] = None
    amount_sats: int = Field(gt=0)
    rail: str = Field(default="lightning", pattern="^(lightning|bitcoin|spark)$")


class EscrowFund(BaseModel):
    nwc_uri: Optional[str] = None


class EscrowOut(BaseModel):
    id: UUID
    organizer_id: UUID
    agent_coordinate: str
    event_id: Optional[UUID]
    allocation_id: Optional[UUID]
    team_id: Optional[UUID]
    amount_sats: int
    rail: str
    status: str
    release_policy: dict
    refund_policy: dict
    dispute_policy: dict
    funding_request: Optional[str]
    nwc_uri: Optional[str]
    created_at: datetime
    updated_at: datetime
    funded_at: Optional[datetime]
    released_at: Optional[datetime]

    model_config = {"from_attributes": True}


class EscrowListItem(BaseModel):
    id: UUID
    agent_coordinate: str
    event_id: Optional[UUID]
    allocation_id: Optional[UUID]
    amount_sats: int
    rail: str
    status: str
    release_policy: dict
    refund_policy: dict
    funding_request: Optional[str]
    created_at: datetime
    funded_at: Optional[datetime]
    released_at: Optional[datetime]

    model_config = {"from_attributes": True}
