from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PayoutCreate(BaseModel):
    team_id: UUID
    total_sats: int = Field(gt=0)
    # Self-custody: the server never receives a spend credential. It creates pending
    # items and the browser performs the NIP-47 send, reporting each result back.
    # Optional per-member address overrides: {str(participant_id): "name@domain"}.
    # Lets the organizer fill/correct a missing address in the payout modal.
    addresses: Optional[dict[str, str]] = None
    # Optional escrow agent coordinate ("30361:pubkey:identifier"). When set, the
    # payout is escrow-managed instead of a direct NWC send. No wallet credential
    # is needed; the items go pending and the organizer deposits externally.
    escrow_coordinate: Optional[str] = None


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


class PayoutPreflightItem(BaseModel):
    participant_id: UUID
    name: str
    lightning_address: str
    amount_sats: int


class PayoutPreflightOut(BaseModel):
    team_id: UUID
    total_sats: int
    items: list[PayoutPreflightItem]


class RewardClaimCreate(BaseModel):
    team_id: UUID
    total_sats: int = Field(gt=0)


class RewardClaimOut(BaseModel):
    id: UUID
    token: str
    allocation_id: UUID
    team_id: UUID
    participant_id: UUID
    name: str
    amount_sats: int
    lightning_address: Optional[str]
    status: str
    expires_at: str
    claim_url: str


class RewardClaimBatchOut(BaseModel):
    team_id: UUID
    total_sats: int
    items: list[RewardClaimOut]


class PublicRewardClaimOut(BaseModel):
    token: str
    participant_name: str
    team_name: str
    amount_sats: int
    status: str
    expires_at: str
    lightning_address: Optional[str] = None


class RewardClaimSubmit(BaseModel):
    lightning_address: str = Field(min_length=3, max_length=255)


class PayoutOut(BaseModel):
    id: UUID
    event_id: UUID
    allocation_id: UUID
    team_label: str
    total_sats: int
    status: str
    escrow_coordinate: Optional[str] = None
    escrow_status: str = "direct"
    items: list[PayoutItemOut]

    model_config = {"from_attributes": True}
