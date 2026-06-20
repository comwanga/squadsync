from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PayoutCreate(BaseModel):
    team_id: UUID
    total_sats: int = Field(gt=0)
    # Self-custody: when omitted, the server creates pending items and the browser
    # performs the NIP-47 send, reporting each result back. The legacy server-side
    # path (server holds the credential) runs only when `nwc` is supplied.
    nwc: Optional[str] = None
    # Optional per-member address overrides: {str(participant_id): "name@domain"}.
    # Lets the organizer fill/correct a missing address in the payout modal.
    addresses: Optional[dict[str, str]] = None


class PayoutItemResult(BaseModel):
    """A browser-performed send to report for one item."""
    bolt11: str = Field(min_length=1)
    preimage: str = Field(min_length=1)


class PayoutItemFailed(BaseModel):
    error: str = Field(min_length=1)


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
