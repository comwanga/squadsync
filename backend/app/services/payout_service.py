"""Lightning payout: deterministic split + orchestration.

`compute_split` is pure and reproducible: an integer even split with the
remainder assigned to the earliest members (by the order they are passed in).
"""
from typing import Sequence, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payout import Payout, PayoutItem
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.services import bolt11

T = TypeVar("T")


def compute_split(recipients: Sequence[T], total_sats: int) -> list[tuple[T, int]]:
    """Split `total_sats` evenly across `recipients`, remainder to the first members.

    Raises ValueError if there are no recipients or fewer sats than recipients
    (every member must receive at least 1 sat).
    """
    n = len(recipients)
    if n == 0:
        raise ValueError("no recipients")
    if total_sats < n:
        raise ValueError("total_sats must be at least one sat per recipient")
    base, remainder = divmod(total_sats, n)
    return [(r, base + (1 if i < remainder else 0)) for i, r in enumerate(recipients)]


def _team_members(db: Session, team_id: UUID) -> list[Participant]:
    """Members of a team, ordered by participant id for a reproducible split."""
    return (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team_id)
        .order_by(Participant.id)
        .all()
    )


def preflight(
    db: Session, team_id: UUID, total_sats: int, overrides: dict[str, str] | None = None,
) -> list[tuple[Participant, str, int]]:
    """Resolve each member's address + split.

    `overrides` maps `str(participant_id) -> lightning_address` and lets the organizer
    supply/correct addresses in the payout modal. The override wins over the
    registration value. Raise ValueError listing any member who still has no address.
    Returns (participant, address, amount_sats) tuples.
    """
    overrides = overrides or {}
    members = _team_members(db, team_id)
    resolved = [(m, overrides.get(str(m.id)) or m.lightning_address) for m in members]
    missing = [m.name for m, addr in resolved if not addr]
    if missing:
        raise ValueError(f"missing lightning address for: {', '.join(missing)}")
    # compute_split preserves order, so zip the amounts back onto (participant, address).
    amounts = compute_split([m for m, _ in resolved], total_sats)
    return [(m, addr, amount) for (m, addr), (_, amount) in zip(resolved, amounts)]


def _rollup_status(items: list[PayoutItem]) -> str:
    """Derive a payout's status from its items.

    complete: every item paid. pending: nothing paid yet and some still pending.
    partial: some paid with others still outstanding or terminally not-paid.
    failed: all items resolved and none paid.
    """
    n = len(items)
    paid = sum(1 for i in items if i.status == "paid")
    pending = any(i.status == "pending" for i in items)
    if n and paid == n:
        return "complete"
    if pending:
        return "partial" if paid else "pending"
    return "partial" if paid else "failed"


def create_pending(
    db: Session, payout: Payout, splits: list[tuple[Participant, str, int]],
) -> Payout:
    """Self-custody path: persist pending items (no network). The browser pays them."""
    for participant, address, amount_sats in splits:
        db.add(PayoutItem(payout_id=payout.id, participant_id=participant.id,
                          lightning_address=address, amount_sats=amount_sats, status="pending"))
    payout.status = "pending"
    db.commit()
    db.refresh(payout)
    return payout


def record_item_result(
    db: Session, payout: Payout, item: PayoutItem, bolt11_str: str, preimage: str,
) -> Payout:
    """Record a browser-performed send, verifying its preimage before marking paid.

    Idempotent on an already-paid item (a client retry must not re-count it).
    """
    if item.status != "paid":
        item.bolt11 = bolt11_str
        item.preimage = preimage
        if bolt11.preimage_matches(bolt11_str, preimage):
            item.status, item.error = "paid", None
        else:
            item.status = "unverified"
            item.error = "wallet returned a preimage that does not match the invoice"
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    payout.status = _rollup_status(items)
    db.commit()
    db.refresh(payout)
    return payout


def record_item_failed(db: Session, payout: Payout, item: PayoutItem, error: str) -> Payout:
    """Record that a browser send for one item failed (no preimage produced)."""
    if item.status != "paid":
        item.status = "failed"
        item.error = error
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    payout.status = _rollup_status(items)
    db.commit()
    db.refresh(payout)
    return payout


