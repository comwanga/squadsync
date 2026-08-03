from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
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


@router.get(
    "/allocations/{allocation_id}",
    response_model=PublicAllocationOut,
    dependencies=[Depends(rate_limit("public-allocation", requests=60))],
)
def public_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Unauthenticated read of a *published* allocation for participant share links.

    Returns 404 for unknown or unpublished allocations so draft results never leak.
    Email and other contact PII are intentionally omitted from the response.
    """
    allocation = _get_published_allocation(db, allocation_id)

    teams_orm = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    team_ids = [team.id for team in teams_orm]
    members_by_team: dict[UUID, list[Participant]] = {team_id: [] for team_id in team_ids}
    if team_ids:
        member_rows = (
            db.query(TeamMember.team_id, Participant)
            .join(Participant, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id.in_(team_ids))
            .all()
        )
        for team_id, participant in member_rows:
            members_by_team[team_id].append(participant)
    teams = []
    for team in teams_orm:
        members = members_by_team[team.id]
        teams.append(PublicTeam(
            id=team.id,
            name=team.name,
            fairness_score=team.fairness_score,
            members=[PublicTeamMember.model_validate(m) for m in members],
            rationale=team.rationale,
        ))
    payouts = []
    payout_rows = db.query(Payout).filter(Payout.allocation_id == allocation.id).all()
    payout_ids = [payout.id for payout in payout_rows]
    items_by_payout: dict[UUID, list[PayoutItem]] = {payout_id: [] for payout_id in payout_ids}
    if payout_ids:
        for item in db.query(PayoutItem).filter(PayoutItem.payout_id.in_(payout_ids)).all():
            items_by_payout[item.payout_id].append(item)
    for p in payout_rows:
        items = items_by_payout[p.id]
        payouts.append(PublicPayoutSummary(
            team_label=p.team_label, total_sats=p.total_sats, status=p.status,
            paid_count=sum(1 for i in items if i.status == "paid"), member_count=len(items),
        ))
    return PublicAllocationOut(id=allocation.id, status=allocation.status, teams=teams, payouts=payouts)


@router.post(
    "/allocations/{allocation_id}/find-team",
    response_model=PublicTeam,
    dependencies=[Depends(rate_limit("find-team", requests=20))],
)
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
