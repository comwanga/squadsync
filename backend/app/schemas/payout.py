from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PayoutCreate(BaseModel):
    team_id: UUID
    total_sats: int = Field(gt=0)
    nwc: str = Field(min_length=1)
    # Optional per-member address overrides: {str(participant_id): "name@domain"}.
    # Lets the organizer fill/correct a missing address in the payout modal.
    addresses: Optional[dict[str, str]] = None


class PayoutRetry(BaseModel):
    nwc: str = Field(min_length=1)
    # Optional per-member address corrections applied to failed items before retry:
    # {str(participant_id): "name@domain"}. Lets an organizer recover a payout that
    # failed because an address was wrong, without creating a new payout.
    addresses: Optional[dict[str, str]] = None


class PayoutItemOut(BaseModel):
    id: UUID
    participant_id: UUID
    lightning_address: Optional[str]
    amount_sats: int
    status: str
    preimage: Optional[str]
    error: Optional[str]

    model_config = {"from_attributes": True}


class PayoutOut(BaseModel):
    id: UUID
    event_id: UUID
    allocation_id: UUID
    team_label: str
    total_sats: int
    status: str
    items: list[PayoutItemOut]

    model_config = {"from_attributes": True}
