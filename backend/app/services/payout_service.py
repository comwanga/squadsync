"""Lightning payout: deterministic split + orchestration.

`compute_split` is pure and reproducible: an integer even split with the
remainder assigned to the earliest members (by the order they are passed in).
"""
import logging
from typing import Sequence, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payout import Payout, PayoutItem
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.services import bolt11, lnurl_service, nwc_service

logger = logging.getLogger(__name__)

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


def execute_payout(
    db: Session, payout: Payout, splits: list[tuple[Participant, str, int]], nwc: str,
) -> Payout:
    """Pay each member, recording per-item status. Rolls payout.status up at the end."""
    paid = 0
    for participant, address, amount_sats in splits:
        item = PayoutItem(payout_id=payout.id, participant_id=participant.id,
                          lightning_address=address, amount_sats=amount_sats, status="pending")
        db.add(item)
        db.flush()
        try:
            params = lnurl_service.resolve_lnurl(address)
            invoice = lnurl_service.request_invoice(params, amount_sats)
            item.bolt11 = invoice
            item.preimage = nwc_service.pay_invoice(nwc, invoice)
            if bolt11.preimage_matches(invoice, item.preimage):
                item.status = "paid"
                paid += 1
            else:
                # The wallet returned a preimage that does not hash to the invoice's
                # payment hash — we have no proof the sats moved, so never mark it paid.
                # Left as a terminal status (retry skips it) to avoid re-sending money
                # that may in fact have left the wallet.
                item.status = "unverified"
                item.error = "wallet returned a preimage that does not match the invoice"
        except Exception as exc:  # noqa: BLE001 — record + continue
            item.status = "failed"
            item.error = str(exc)
            logger.warning("payout item %s failed: %s", item.id, exc)
        # Commit per item: a sent payment's preimage must be durable the moment it
        # lands, so a later crash/commit failure can never lose a record of real money
        # already moved (which would risk a double-pay on re-run).
        db.commit()
    payout.status = "complete" if paid == len(splits) else ("partial" if paid else "failed")
    db.commit()
    db.refresh(payout)
    return payout


def retry_failed(
    db: Session, payout: Payout, nwc: str, overrides: dict[str, str] | None = None,
) -> Payout:
    """Retry only the failed items of an existing payout.

    `overrides` maps `str(participant_id) -> lightning_address` and corrects a bad
    address before the retry, so a payout that failed purely on addresses can be
    recovered without creating a new one.
    """
    overrides = overrides or {}
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    for item in items:
        if item.status != "failed":
            continue
        corrected = overrides.get(str(item.participant_id))
        if corrected:
            item.lightning_address = corrected
        try:
            params = lnurl_service.resolve_lnurl(item.lightning_address)
            invoice = lnurl_service.request_invoice(params, item.amount_sats)
            item.bolt11 = invoice
            item.preimage = nwc_service.pay_invoice(nwc, invoice)
            if bolt11.preimage_matches(invoice, item.preimage):
                item.status, item.error = "paid", None
            else:
                item.status = "unverified"
                item.error = "wallet returned a preimage that does not match the invoice"
        except Exception as exc:  # noqa: BLE001
            item.error = str(exc)
            logger.warning("payout retry item %s failed: %s", item.id, exc)
        db.commit()  # durable per item (see execute_payout)
    paid = sum(1 for i in items if i.status == "paid")
    payout.status = "complete" if paid == len(items) else ("partial" if paid else "failed")
    db.commit()
    db.refresh(payout)
    return payout
