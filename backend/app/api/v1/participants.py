from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.participant import ParticipantRegister, ParticipantOut, EventPublicInfo, ParticipantCategoryUpdate
from app.services.registration_service import (
    get_public_event, register_participant, list_participants, delete_participant, override_category,
)

router = APIRouter()


@router.get("/{slug}/info", response_model=EventPublicInfo)
def public_info(slug: str, db: Session = Depends(get_db)):
    return get_public_event(db, slug)


@router.post("/{slug}/register", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def register(slug: str, req: ParticipantRegister, db: Session = Depends(get_db)):
    return register_participant(db, slug, req)


@router.get("/{event_id}/participants", response_model=list[ParticipantOut])
def list_all(
    event_id: UUID,
    strength: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_participants(db, event_id, current_user.id, strength, experience)


@router.patch("/{event_id}/participants/{participant_id}", response_model=ParticipantOut)
def patch_category(
    event_id: UUID,
    participant_id: UUID,
    req: ParticipantCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return override_category(db, event_id, participant_id, current_user.id, req.normalized_strength)


@router.delete("/{event_id}/participants/{participant_id}", response_model=ParticipantOut)
def delete(
    event_id: UUID,
    participant_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_participant(db, event_id, participant_id, current_user.id)
