from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.allocation import Allocation
from app.models.payout import Payout, PayoutItem
from app.models.team import Team
from app.models.user import User
from app.schemas.payout import PayoutCreate, PayoutRetry, PayoutOut
from app.services.event_service import assert_allocation_organizer
from app.services import payout_service

router = APIRouter()


def _payout_out(db: Session, payout: Payout) -> PayoutOut:
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    return PayoutOut(
        id=payout.id, event_id=payout.event_id, allocation_id=payout.allocation_id,
        team_label=payout.team_label, total_sats=payout.total_sats, status=payout.status,
        items=items,
    )


@router.post("/{allocation_id}/payouts", response_model=PayoutOut,
             status_code=status.HTTP_201_CREATED)
def create_payout(
    allocation_id: UUID,
    req: PayoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation: Allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    team = db.query(Team).filter(Team.id == req.team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in this allocation")

    # Spend ceiling: reject an implausibly large amount before touching a wallet.
    if req.total_sats > settings.PAYOUT_MAX_SATS:
        raise HTTPException(
            status_code=422,
            detail=f"total_sats {req.total_sats} exceeds the payout ceiling "
                   f"of {settings.PAYOUT_MAX_SATS} sats",
        )

    # Idempotency: refuse a second payout for a team that already has one, so a
    # double-click or a client retry after a timeout can never pay winners twice.
    if db.query(Payout).filter(
        Payout.allocation_id == allocation_id, Payout.team_label == team.name
    ).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This team has already been paid; retry the existing payout instead.",
        )

    # Pre-flight: split + verify every member has an address BEFORE spending anything.
    try:
        splits = payout_service.preflight(db, team.id, req.total_sats, req.addresses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    payout = Payout(event_id=allocation.event_id, allocation_id=allocation_id,
                    team_label=team.name, total_sats=req.total_sats, status="pending")
    db.add(payout)
    # The unique (allocation_id, team_label) constraint is the race backstop: if a
    # concurrent request inserted first, this flush raises before any sats move.
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This team has already been paid; retry the existing payout instead.",
        )
    payout = payout_service.execute_payout(db, payout, splits, req.nwc)
    return _payout_out(db, payout)


@router.post("/payouts/{payout_id}/retry", response_model=PayoutOut)
def retry_payout(
    payout_id: UUID,
    req: PayoutRetry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    assert_allocation_organizer(db, payout.allocation_id, current_user.id)
    payout = payout_service.retry_failed(db, payout, req.nwc)
    return _payout_out(db, payout)
