from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.models.allocation import AllocationConfig, Allocation
from app.schemas.allocation import AllocationConfigIn, AllocationConfigOut, AllocationOut, TeamOut, TeamMemberOut
from app.services.allocation_engine import run_allocation
from app.services.event_service import _assert_organizer
from app.models.team import Team, TeamMember
from app.models.participant import Participant

router = APIRouter()


def _build_allocation_out(db: Session, allocation: Allocation) -> AllocationOut:
    teams_orm = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    teams_out = []
    for team in teams_orm:
        members_orm = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        members_out = [TeamMemberOut.model_validate(m) for m in members_orm]
        teams_out.append(TeamOut(
            id=str(team.id),
            allocation_id=str(team.allocation_id),
            name=team.name,
            fairness_score=team.fairness_score,
            skill_score=team.skill_score,
            role_balance_score=team.role_balance_score,
            members=members_out,
        ))
    return AllocationOut(
        id=str(allocation.id),
        event_id=str(allocation.event_id),
        snapshot_hash=allocation.snapshot_hash,
        status=allocation.status,
        constraint_warnings=allocation.constraint_warnings or {},
        teams=teams_out,
    )


@router.get("/{event_id}/config", response_model=AllocationConfigOut)
def get_config(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_organizer(db, event_id, current_user.id)
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


@router.put("/{event_id}/config", response_model=AllocationConfigOut)
def update_config(
    event_id: UUID,
    req: AllocationConfigIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    if abs(req.weight_experience + req.weight_skill - 1.0) > 0.001:
        raise HTTPException(status_code=400, detail="Weights must sum to 1.0")
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
    config.weight_experience = req.weight_experience
    config.weight_skill = req.weight_skill
    config.role_constraints = req.role_constraints
    db.commit()
    db.refresh(config)
    return config


@router.post("/{event_id}/allocate", response_model=AllocationOut)
def allocate(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _assert_organizer(db, event_id, current_user.id)
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).first()
    if not config:
        config = AllocationConfig(event_id=event_id)
        db.add(config)
        db.commit()
    allocation = run_allocation(db, event_id, config)
    return _build_allocation_out(db, allocation)


@router.get("/{event_id}/allocations/{allocation_id}", response_model=AllocationOut)
def get_allocation(
    event_id: UUID,
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    allocation = db.query(Allocation).filter(
        Allocation.id == allocation_id, Allocation.event_id == event_id
    ).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return _build_allocation_out(db, allocation)


@router.post("/{event_id}/allocations/{allocation_id}/publish")
def publish_allocation(
    event_id: UUID,
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    allocation = db.query(Allocation).filter(
        Allocation.id == allocation_id, Allocation.event_id == event_id
    ).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    allocation.status = "published"
    db.commit()
    return {"detail": "published"}
