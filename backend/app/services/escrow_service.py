"""Escrow session state machine and business logic."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.escrow import Escrow
from app.services import pip01

_VALID_TRANSITIONS: dict[str, list[str]] = {
    "draft": ["awaiting_funding", "cancelled"],
    "awaiting_funding": ["funded", "cancelled", "expired"],
    "funded": ["active", "cancelled", "refund_pending", "disputed"],
    "active": ["release_pending", "refund_pending", "disputed"],
    "release_pending": ["released", "failed"],
    "released": [],
    "cancelled": [],
    "refund_pending": ["refunded", "failed"],
    "refunded": [],
    "disputed": ["released", "refunded", "cancelled"],
    "failed": [],
    "expired": [],
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def transition(db: Session, escrow: Escrow, to_status: str) -> Escrow:
    allowed = _VALID_TRANSITIONS.get(escrow.status, [])
    if to_status not in allowed:
        msg = f"Cannot transition from {escrow.status} to {to_status}"
        raise ValueError(msg)

    escrow.status = to_status
    escrow.updated_at = _utcnow()

    if to_status == "funded":
        escrow.funded_at = _utcnow()
    if to_status == "released":
        escrow.released_at = _utcnow()

    db.commit()
    db.refresh(escrow)
    return escrow


def create_escrow(
    db: Session,
    organizer_id: UUID,
    agent_coordinate: str,
    amount_sats: int,
    rail: str,
    event_id: UUID | None = None,
    allocation_id: UUID | None = None,
    team_id: UUID | None = None,
) -> Escrow:
    parsed = pip01.parse_escrow_event(
        {"content": "{}", "tags": []}
    )

    release_policy = {
        "release_trigger": "SquadSync allocation published",
    }
    refund_policy = {
        "refund_trigger": "48 hours after event end or organizer cancel",
    }
    dispute_policy = {
        "policy": "mutual agreement between parties",
    }

    escrow = Escrow(
        id=uuid4(),
        organizer_id=organizer_id,
        agent_coordinate=agent_coordinate,
        event_id=event_id,
        allocation_id=allocation_id,
        team_id=team_id,
        amount_sats=amount_sats,
        rail=rail,
        status="draft",
        release_policy=release_policy,
        refund_policy=refund_policy,
        dispute_policy=dispute_policy,
    )
    db.add(escrow)
    db.commit()
    db.refresh(escrow)
    return escrow


def activate(db: Session, escrow: Escrow) -> Escrow:
    """Move escrow from draft to awaiting_funding."""
    return transition(db, escrow, "awaiting_funding")


def mark_funded(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "funded")


def activate_after_funding(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "active")


def request_release(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "release_pending")


def mark_released(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "released")


def cancel(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "cancelled")


def mark_refunded(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "refunded")


def mark_disputed(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "disputed")


def mark_failed(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "failed")


def mark_expired(db: Session, escrow: Escrow) -> Escrow:
    return transition(db, escrow, "expired")
