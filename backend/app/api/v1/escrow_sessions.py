"""Escrow session lifecycle endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.escrow import Escrow
from app.models.user import User
from app.schemas.escrow import EscrowCreate, EscrowFund, EscrowListItem, EscrowOut
from app.services import escrow_service

router = APIRouter()


def _list_out(escrow: Escrow) -> EscrowListItem:
    return EscrowListItem(
        id=escrow.id,
        agent_coordinate=escrow.agent_coordinate,
        event_id=escrow.event_id,
        allocation_id=escrow.allocation_id,
        amount_sats=escrow.amount_sats,
        rail=escrow.rail,
        status=escrow.status,
        release_policy=escrow.release_policy,
        refund_policy=escrow.refund_policy,
        funding_request=escrow.funding_request,
        created_at=escrow.created_at,
        funded_at=escrow.funded_at,
        released_at=escrow.released_at,
    )


def _escrow_out(escrow: Escrow) -> EscrowOut:
    return EscrowOut(
        id=escrow.id,
        organizer_id=escrow.organizer_id,
        agent_coordinate=escrow.agent_coordinate,
        event_id=escrow.event_id,
        allocation_id=escrow.allocation_id,
        team_id=escrow.team_id,
        amount_sats=escrow.amount_sats,
        rail=escrow.rail,
        status=escrow.status,
        release_policy=escrow.release_policy,
        refund_policy=escrow.refund_policy,
        dispute_policy=escrow.dispute_policy,
        funding_request=escrow.funding_request,
        nwc_uri=escrow.nwc_uri,
        created_at=escrow.created_at,
        updated_at=escrow.updated_at,
        funded_at=escrow.funded_at,
        released_at=escrow.released_at,
    )


def _own_escrow(db: Session, escrow_id: UUID, user_id: UUID) -> Escrow:
    escrow = db.query(Escrow).filter(Escrow.id == escrow_id).first()
    if not escrow:
        raise HTTPException(status_code=404, detail="Escrow not found")
    if escrow.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Not your escrow")
    return escrow


@router.post("", response_model=EscrowOut, status_code=status.HTTP_201_CREATED)
def create_escrow(
    req: EscrowCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    escrow = escrow_service.create_escrow(
        db,
        organizer_id=current_user.id,
        agent_coordinate=req.agent_coordinate,
        amount_sats=req.amount_sats,
        rail=req.rail,
        event_id=req.event_id,
        allocation_id=req.allocation_id,
        team_id=req.team_id,
    )
    return _escrow_out(escrow)


@router.get("", response_model=list[EscrowListItem])
def list_escrows(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Escrow).filter(Escrow.organizer_id == current_user.id)
    if status:
        q = q.filter(Escrow.status == status)
    return [_list_out(e) for e in q.order_by(Escrow.created_at.desc()).all()]


@router.get("/{escrow_id}", response_model=EscrowOut)
def get_escrow(
    escrow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _escrow_out(_own_escrow(db, escrow_id, current_user.id))


@router.post("/{escrow_id}/activate", response_model=EscrowOut)
def activate_escrow(
    escrow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move escrow from draft to awaiting_funding."""
    escrow = _own_escrow(db, escrow_id, current_user.id)
    return _escrow_out(escrow_service.activate(db, escrow))


@router.post("/{escrow_id}/fund", response_model=EscrowOut)
def fund_escrow(
    escrow_id: UUID,
    req: EscrowFund,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Activate escrow and generate a funding request (bolt11 or address)."""
    escrow = _own_escrow(db, escrow_id, current_user.id)

    if escrow.status == "draft":
        escrow = escrow_service.activate(db, escrow)

    if escrow.status != "awaiting_funding":
        raise HTTPException(status_code=409, detail="Escrow is not awaiting funding")

    if req.nwc_uri:
        escrow.nwc_uri = req.nwc_uri

    # Generate a placeholder funding request. In production, this would call the
    # escrow agent's API to get a real bolt11 invoice or on-chain address.
    if not escrow.funding_request:
        if escrow.rail == "lightning":
            escrow.funding_request = (
                f"lnbc{escrow.amount_sats * 1000}u1p3xqplaceholder"
            )
        elif escrow.rail == "bitcoin":
            escrow.funding_request = "bc1qplaceholderaddress000000000000000000000"
        else:
            escrow.funding_request = f"spark-request-{escrow.id}"

    db.commit()
    db.refresh(escrow)
    return _escrow_out(escrow)


@router.post("/{escrow_id}/confirm-funded", response_model=EscrowOut)
def confirm_funded(
    escrow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark escrow as funded (payment confirmed by the agent)."""
    escrow = _own_escrow(db, escrow_id, current_user.id)
    return _escrow_out(escrow_service.mark_funded(db, escrow))


@router.post("/{escrow_id}/release", response_model=EscrowOut)
def release_escrow(
    escrow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark escrow as released (funds sent to recipients)."""
    escrow = _own_escrow(db, escrow_id, current_user.id)
    if escrow.status == "funded":
        escrow = escrow_service.activate_after_funding(db, escrow)
    if escrow.status == "active":
        escrow = escrow_service.request_release(db, escrow)
    return _escrow_out(escrow_service.mark_released(db, escrow))


@router.post("/{escrow_id}/cancel", response_model=EscrowOut)
def cancel_escrow(
    escrow_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel the escrow (only in draft or awaiting_funding)."""
    escrow = _own_escrow(db, escrow_id, current_user.id)
    return _escrow_out(escrow_service.cancel(db, escrow))
