from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.allocation import Allocation
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.models.payout import Payout, PayoutItem
from app.schemas.allocation import FindTeamRequest, PublicAllocationOut, PublicPayoutSummary, PublicTeam, PublicTeamMember

router = APIRouter()


def _get_published_allocation(db: Session, allocation_id: UUID) -> Allocation:
    """Return a *published* allocation or raise an opaque 404.

    All public negative cases (unknown allocation, draft, or — in find-team — an
    unmatched email) share this single message so the endpoint never reveals whether
    an allocation exists or is published.
    """
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation or allocation.status != "published":
        raise HTTPException(status_code=404, detail="Results not found")
    return allocation


@router.get("/allocations/{allocation_id}", response_model=PublicAllocationOut)
def public_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Unauthenticated read of a *published* allocation for participant share links.

    Returns 404 for unknown or unpublished allocations so draft results never leak.
    Email and other contact PII are intentionally omitted from the response.
    """
    allocation = _get_published_allocation(db, allocation_id)

    teams_orm = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    teams = []
    for team in teams_orm:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        teams.append(PublicTeam(
            id=team.id,
            name=team.name,
            fairness_score=team.fairness_score,
            members=[PublicTeamMember.model_validate(m) for m in members],
        ))
    payouts = []
    for p in db.query(Payout).filter(Payout.allocation_id == allocation.id).all():
        items = db.query(PayoutItem).filter(PayoutItem.payout_id == p.id).all()
        payouts.append(PublicPayoutSummary(
            team_label=p.team_label, total_sats=p.total_sats, status=p.status,
            paid_count=sum(1 for i in items if i.status == "paid"), member_count=len(items),
        ))
    return PublicAllocationOut(id=allocation.id, status=allocation.status, teams=teams, payouts=payouts)


@router.post("/allocations/{allocation_id}/find-team", response_model=PublicTeam)
def find_my_team(allocation_id: UUID, req: FindTeamRequest, db: Session = Depends(get_db)):
    """Public lookup: which team is this registered email on? Published-only.

    Returns the matching team (names only, no PII). 404 (opaque "Results not found")
    for unpublished allocations or emails not registered on the event.
    """
    allocation = _get_published_allocation(db, allocation_id)

    participant = (
        db.query(Participant)
        .filter(
            Participant.event_id == allocation.event_id,
            func.lower(Participant.email) == req.email.lower(),
        )
        .first()
    )
    team = None
    if participant:
        team = (
            db.query(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .filter(Team.allocation_id == allocation.id, TeamMember.participant_id == participant.id)
            .first()
        )
    if not team:
        # Same opaque message as the published-check, so a probe can't distinguish
        # "published but email unknown" from "draft / no such allocation".
        raise HTTPException(status_code=404, detail="Results not found")

    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    return PublicTeam(
        id=team.id,
        name=team.name,
        fairness_score=team.fairness_score,
        members=[PublicTeamMember.model_validate(m) for m in members],
    )
