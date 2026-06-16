from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.allocation import Allocation
from app.models.team import Team, TeamMember
from app.models.participant import Participant
from app.models.user import User
from app.schemas.allocation import TeamOut, TeamMemberOut, AllocationOut, MemberMove
from app.services.event_service import assert_allocation_organizer
from app.services.allocation_engine import move_participant
from app.api.v1.allocation import _build_allocation_out

router = APIRouter()


@router.get("/{allocation_id}/teams", response_model=list[TeamOut])
def list_teams(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assert_allocation_organizer(db, allocation_id, current_user.id)
    teams = db.query(Team).filter(Team.allocation_id == allocation_id).all()
    result = []
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        result.append(TeamOut(
            id=str(team.id),
            allocation_id=str(team.allocation_id),
            name=team.name,
            fairness_score=team.fairness_score,
            skill_score=team.skill_score,
            role_balance_score=team.role_balance_score,
            members=[TeamMemberOut.model_validate(m) for m in members],
        ))
    return result


@router.get("/{allocation_id}/teams/{team_id}", response_model=TeamOut)
def get_team(allocation_id: UUID, team_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assert_allocation_organizer(db, allocation_id, current_user.id)
    team = db.query(Team).filter(Team.id == team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    return TeamOut(
        id=str(team.id),
        allocation_id=str(team.allocation_id),
        name=team.name,
        fairness_score=team.fairness_score,
        skill_score=team.skill_score,
        role_balance_score=team.role_balance_score,
        members=[TeamMemberOut.model_validate(m) for m in members],
    )


@router.patch("/{allocation_id}/members/{participant_id}", response_model=AllocationOut)
def move_member(
    allocation_id: UUID,
    participant_id: UUID,
    req: MemberMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    if allocation.status != "draft":
        raise HTTPException(status_code=409, detail="Allocation is published; teams are locked")
    move_participant(db, allocation, participant_id, req.team_id)
    return _build_allocation_out(db, allocation)
