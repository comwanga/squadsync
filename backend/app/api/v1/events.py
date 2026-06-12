from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, EventOut, CoOrganizerInvite
from app.services.event_service import (
    create_event, list_events, get_event, update_event, delete_event,
    invite_co_organizer, remove_co_organizer,
)

router = APIRouter()


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create(req: EventCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return create_event(db, req, current_user.id)


@router.get("", response_model=list[EventOut])
def list_all(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return list_events(db, current_user.id)


@router.get("/{event_id}", response_model=EventOut)
def get(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return get_event(db, event_id, current_user.id)


@router.patch("/{event_id}", response_model=EventOut)
def update(event_id: UUID, req: EventUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return update_event(db, event_id, current_user.id, req)


@router.delete("/{event_id}", response_model=EventOut)
def delete(event_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return delete_event(db, event_id, current_user.id)


@router.post("/{event_id}/co-organizers")
def invite(event_id: UUID, req: CoOrganizerInvite, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    invite_co_organizer(db, event_id, current_user.id, req)
    return {"detail": "invited"}


@router.delete("/{event_id}/co-organizers/{co_user_id}")
def remove(event_id: UUID, co_user_id: UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    remove_co_organizer(db, event_id, current_user.id, co_user_id)
    return {"detail": "removed"}
