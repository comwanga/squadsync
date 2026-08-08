from datetime import datetime, timedelta, timezone
import re
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.models.allocation import Allocation
from app.models.participant import Participant
from app.models.payout import Payout, PayoutItem, RewardClaim
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.payout import (
    PayoutCreate,
    PayoutOut,
    PayoutItemResult,
    PayoutItemFailed,
    PayoutPreflightOut,
    PublicRewardClaimOut,
    RewardClaimBatchOut,
    RewardClaimCreate,
    RewardClaimSubmit,
)
from app.services.event_service import assert_allocation_organizer
from app.services import payout_service

router = APIRouter()
LIGHTNING_ADDRESS_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _payout_out(db: Session, payout: Payout) -> PayoutOut:
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    return PayoutOut(
        id=payout.id, event_id=payout.event_id, allocation_id=payout.allocation_id,
        team_label=payout.team_label, total_sats=payout.total_sats, status=payout.status,
        escrow_coordinate=payout.escrow_coordinate, escrow_status=payout.escrow_status,
        items=items,
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(claim: RewardClaim) -> bool:
    expires_at = claim.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= _utcnow()


def _claim_url(token: str) -> str:
    origin = settings.FRONTEND_URL.split(",")[0].strip().rstrip("/")
    return f"{origin}/claim/{token}"


def _claim_out(claim: RewardClaim, participant: Participant) -> dict:
    return {
        "id": claim.id,
        "token": claim.token,
        "allocation_id": claim.allocation_id,
        "team_id": claim.team_id,
        "participant_id": claim.participant_id,
        "name": participant.name,
        "amount_sats": claim.amount_sats,
        "lightning_address": claim.lightning_address,
        "status": claim.status,
        "expires_at": claim.expires_at.isoformat(),
        "claim_url": _claim_url(claim.token),
    }


def _preflight(db: Session, allocation_id: UUID, req: PayoutCreate, user_id: UUID):
    allocation: Allocation = assert_allocation_organizer(db, allocation_id, user_id)
    team = db.query(Team).filter(Team.id == req.team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in this allocation")

    if req.total_sats > settings.PAYOUT_MAX_SATS:
        raise HTTPException(
            status_code=422,
            detail=f"total_sats {req.total_sats} exceeds the payout ceiling "
                   f"of {settings.PAYOUT_MAX_SATS} sats",
        )

    try:
        splits = payout_service.preflight(db, team.id, req.total_sats, req.addresses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return allocation, team, splits


@router.post("/{allocation_id}/payouts/preflight", response_model=PayoutPreflightOut)
def preflight_payout(
    allocation_id: UUID,
    req: PayoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, _, splits = _preflight(db, allocation_id, req, current_user.id)
    return PayoutPreflightOut(
        team_id=req.team_id,
        total_sats=req.total_sats,
        items=[
            {
                "participant_id": participant.id,
                "name": participant.name,
                "lightning_address": address,
                "amount_sats": amount_sats,
            }
            for participant, address, amount_sats in splits
        ],
    )


@router.post("/{allocation_id}/reward-claims", response_model=RewardClaimBatchOut)
def create_reward_claims(
    allocation_id: UUID,
    req: RewardClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation: Allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    team = db.query(Team).filter(Team.id == req.team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in this allocation")
    if req.total_sats > settings.PAYOUT_MAX_SATS:
        raise HTTPException(
            status_code=422,
            detail=f"total_sats {req.total_sats} exceeds the payout ceiling "
                   f"of {settings.PAYOUT_MAX_SATS} sats",
        )

    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == req.team_id)
        .order_by(Participant.id)
        .all()
    )
    try:
        splits = payout_service.compute_split(members, req.total_sats)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    expires_at = _utcnow() + timedelta(hours=48)
    items = []
    for participant, amount_sats in splits:
        claim = db.query(RewardClaim).filter(
            RewardClaim.allocation_id == allocation.id,
            RewardClaim.team_id == team.id,
            RewardClaim.participant_id == participant.id,
        ).first()
        if claim and claim.status != "paid":
            claim.total_sats = req.total_sats
            claim.amount_sats = amount_sats
            claim.expires_at = expires_at
            if claim.lightning_address:
                claim.status = "claimed"
            elif claim.status == "expired":
                claim.status = "pending"
        elif not claim:
            claim = RewardClaim(
                token=secrets.token_urlsafe(24),
                allocation_id=allocation.id,
                team_id=team.id,
                participant_id=participant.id,
                total_sats=req.total_sats,
                amount_sats=amount_sats,
                lightning_address=participant.lightning_address,
                status="claimed" if participant.lightning_address else "pending",
                expires_at=expires_at,
            )
            db.add(claim)
            db.flush()
        items.append(_claim_out(claim, participant))
    db.commit()
    return {"team_id": team.id, "total_sats": req.total_sats, "items": items}


@router.get(
    "/reward-claims/{token}",
    response_model=PublicRewardClaimOut,
    dependencies=[Depends(rate_limit("reward-claim-read", requests=60))],
)
def get_reward_claim(token: str, db: Session = Depends(get_db)):
    claim = db.query(RewardClaim).filter(RewardClaim.token == token).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Reward claim not found")
    participant = db.query(Participant).filter(Participant.id == claim.participant_id).first()
    team = db.query(Team).filter(Team.id == claim.team_id).first()
    if not participant or not team:
        raise HTTPException(status_code=404, detail="Reward claim is no longer available")
    if claim.status == "pending" and _is_expired(claim):
        claim.status = "expired"
        db.commit()
    return {
        "token": claim.token,
        "participant_name": participant.name,
        "team_name": team.name,
        "amount_sats": claim.amount_sats,
        "status": claim.status,
        "expires_at": claim.expires_at.isoformat(),
        "lightning_address": claim.lightning_address,
    }


@router.post(
    "/reward-claims/{token}",
    response_model=PublicRewardClaimOut,
    dependencies=[Depends(rate_limit("reward-claim-submit", requests=10))],
)
def submit_reward_claim(token: str, req: RewardClaimSubmit, db: Session = Depends(get_db)):
    address = req.lightning_address.strip()
    if not LIGHTNING_ADDRESS_RE.match(address):
        raise HTTPException(status_code=422, detail="Use a Lightning Address like name@example.com")

    claim = db.query(RewardClaim).filter(RewardClaim.token == token).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Reward claim not found")
    participant = db.query(Participant).filter(Participant.id == claim.participant_id).first()
    team = db.query(Team).filter(Team.id == claim.team_id).first()
    if not participant or not team:
        raise HTTPException(status_code=404, detail="Reward claim is no longer available")
    if claim.status == "paid":
        raise HTTPException(status_code=409, detail="This reward has already been paid")
    if _is_expired(claim):
        claim.status = "expired"
        db.commit()
        raise HTTPException(status_code=410, detail="This reward claim has expired")

    claim.lightning_address = address
    claim.status = "claimed"
    claim.claimed_at = _utcnow()
    participant.lightning_address = address
    db.commit()
    return {
        "token": claim.token,
        "participant_name": participant.name,
        "team_name": team.name,
        "amount_sats": claim.amount_sats,
        "status": claim.status,
        "expires_at": claim.expires_at.isoformat(),
        "lightning_address": claim.lightning_address,
    }

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

    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == req.team_id)
        .order_by(Participant.id)
        .all()
    )

    if req.escrow_coordinate:
        splits = [(m, "", amt) for (m, amt) in payout_service.compute_split(members, req.total_sats)]
    else:
        try:
            splits = payout_service.preflight(db, req.team_id, req.total_sats, req.addresses)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    payout = Payout(event_id=allocation.event_id, allocation_id=allocation_id,
                    team_label=team.name, total_sats=req.total_sats, status="pending")
    db.add(payout)

    if req.escrow_coordinate:
        payout.escrow_coordinate = req.escrow_coordinate
        payout.escrow_status = "escrow_pending"

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
    # Self-custody: create pending items; the browser pays and reports each result.
    # The server never receives a spend credential.
    payout = payout_service.create_pending(db, payout, splits)
    return _payout_out(db, payout)


def _get_item(db: Session, payout_id: UUID, item_id: UUID, user_id: UUID) -> tuple[Payout, PayoutItem]:
    """Load a payout + one of its items, asserting the caller is the organizer."""
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    assert_allocation_organizer(db, payout.allocation_id, user_id)
    item = db.query(PayoutItem).filter(
        PayoutItem.id == item_id, PayoutItem.payout_id == payout_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Payout item not found")
    return payout, item


@router.post("/payouts/{payout_id}/items/{item_id}/result", response_model=PayoutOut)
def report_item_result(
    payout_id: UUID,
    item_id: UUID,
    req: PayoutItemResult,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Self-custody: the browser reports a completed send; the server verifies the preimage."""
    payout, item = _get_item(db, payout_id, item_id, current_user.id)
    payout = payout_service.record_item_result(db, payout, item, req.bolt11, req.preimage)
    return _payout_out(db, payout)


@router.post("/payouts/{payout_id}/items/{item_id}/failed", response_model=PayoutOut)
def report_item_failed(
    payout_id: UUID,
    item_id: UUID,
    req: PayoutItemFailed,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Self-custody: the browser reports a send that produced no preimage."""
    payout, item = _get_item(db, payout_id, item_id, current_user.id)
    payout = payout_service.record_item_failed(db, payout, item, req.error)
    return _payout_out(db, payout)


@router.post("/payouts/{payout_id}/escrow-funded", response_model=PayoutOut)
def escrow_funded(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an escrow-managed payout as funded (organizer deposited with the agent)."""
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    assert_allocation_organizer(db, payout.allocation_id, current_user.id)
    if payout.escrow_status != "escrow_pending":
        raise HTTPException(status_code=409, detail="Payout is not in escrow_pending status")
    payout.escrow_status = "escrow_funded"
    db.commit()
    return _payout_out(db, payout)


@router.post("/payouts/{payout_id}/escrow-released", response_model=PayoutOut)
def escrow_released(
    payout_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an escrow-managed payout as released (funds sent to recipients)."""
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    assert_allocation_organizer(db, payout.allocation_id, current_user.id)
    if payout.escrow_status not in ("escrow_funded", "escrow_pending"):
        raise HTTPException(status_code=409, detail="Payout has not been funded")
    payout.escrow_status = "escrow_released"
    db.commit()
    return _payout_out(db, payout)
