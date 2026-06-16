from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.allocation import Allocation
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.schemas.allocation import FindTeamRequest, PublicAllocationOut, PublicTeam, PublicTeamMember

router = APIRouter()


@router.get("/allocations/{allocation_id}", response_model=PublicAllocationOut)
def public_allocation(allocation_id: UUID, db: Session = Depends(get_db)):
    """Unauthenticated read of a *published* allocation for participant share links.

    Returns 404 for unknown or unpublished allocations so draft results never leak.
    Email and other contact PII are intentionally omitted from the response.
    """
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation or allocation.status != "published":
        raise HTTPException(status_code=404, detail="Results not found")

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
    return PublicAllocationOut(id=allocation.id, status=allocation.status, teams=teams)


@router.post("/allocations/{allocation_id}/find-team", response_model=PublicTeam)
def find_my_team(allocation_id: UUID, req: FindTeamRequest, db: Session = Depends(get_db)):
    """Public lookup: which team is this registered email on? Published-only.

    Returns the matching team (names only, no PII). 404 for unpublished allocations
    or emails not registered on the event.
    """
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation or allocation.status != "published":
        raise HTTPException(status_code=404, detail="Results not found")

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
        raise HTTPException(status_code=404, detail="Not found on this event")

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
