import secrets
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.event import Event, EventCoOrganizer
from app.models.user import User
from app.schemas.event import EventCreate, EventUpdate, CoOrganizerInvite, EventOut


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


def _assert_organizer(db: Session, event_id: UUID, user_id: UUID) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    is_owner = str(event.owner_id) == str(user_id)
    is_co = db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == user_id,
    ).first() is not None
    if not (is_owner or is_co):
        raise HTTPException(status_code=403, detail="Not authorized")
    return event


def assert_allocation_organizer(db: Session, allocation_id: UUID, user_id: UUID):
    """Resolve an allocation to its event and assert the user organizes that event.

    Returns the Allocation. Raises 404 if the allocation does not exist and 403
    if the caller is not an organizer of the owning event.
    """
    from app.models.allocation import Allocation

    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    _assert_organizer(db, allocation.event_id, user_id)
    return allocation


def create_event(db: Session, req: EventCreate, owner_id: UUID) -> Event:
    slug = _generate_slug()
    while db.query(Event).filter(Event.registration_slug == slug).first():
        slug = _generate_slug()
    event = Event(**req.model_dump(), owner_id=owner_id, registration_slug=slug)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, user_id: UUID, archived: bool = False) -> list[Event]:
    status_filter = (Event.status == "archived") if archived else (Event.status != "archived")
    owned = db.query(Event).filter(Event.owner_id == user_id, status_filter).all()
    co_event_ids = [
        row.event_id for row in db.query(EventCoOrganizer).filter(EventCoOrganizer.user_id == user_id).all()
    ]
    co_events = db.query(Event).filter(Event.id.in_(co_event_ids), status_filter).all()
    seen = {str(e.id) for e in owned}
    return owned + [e for e in co_events if str(e.id) not in seen]


def get_event(db: Session, event_id: UUID, user_id: UUID) -> Event:
    return _assert_organizer(db, event_id, user_id)


def update_event(db: Session, event_id: UUID, user_id: UUID, req: EventUpdate) -> Event:
    event = _assert_organizer(db, event_id, user_id)
    for field, value in req.model_dump(exclude_none=True).items():
        setattr(event, field, value)
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: UUID, user_id: UUID) -> EventOut:
    """Permanently delete an event and all of its child rows (hard delete).

    Owner-only: this is irreversible, so co-organizers may archive (PATCH status)
    but not permanently destroy an event they don't own.

    NOTE: keep the cascade below in sync with every table that has an event_id (or
    transitive) FK. New child tables must be added here or their rows will orphan.
    """
    from app.models.allocation import Allocation, AllocationConfig
    from app.models.team import Team, TeamMember
    from app.models.participant import Participant

    event = _assert_organizer(db, event_id, user_id)
    if str(event.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Only the owner can delete an event")
    snapshot = EventOut.model_validate(event)  # capture before deletion

    alloc_ids = [a.id for a in db.query(Allocation).filter(Allocation.event_id == event_id).all()]
    if alloc_ids:
        team_ids = [t.id for t in db.query(Team).filter(Team.allocation_id.in_(alloc_ids)).all()]
        if team_ids:
            db.query(TeamMember).filter(TeamMember.team_id.in_(team_ids)).delete(synchronize_session=False)
        db.query(Team).filter(Team.allocation_id.in_(alloc_ids)).delete(synchronize_session=False)
        db.query(Allocation).filter(Allocation.event_id == event_id).delete(synchronize_session=False)
    db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).delete(synchronize_session=False)
    db.query(Participant).filter(Participant.event_id == event_id).delete(synchronize_session=False)
    db.query(EventCoOrganizer).filter(EventCoOrganizer.event_id == event_id).delete(synchronize_session=False)
    db.delete(event)
    db.commit()
    return snapshot


def invite_co_organizer(db: Session, event_id: UUID, user_id: UUID, req: CoOrganizerInvite) -> None:
    _assert_organizer(db, event_id, user_id)
    invitee = db.query(User).filter(User.pubkey == req.pubkey).first()
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found")
    existing = db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == invitee.id,
    ).first()
    if not existing:
        db.add(EventCoOrganizer(event_id=event_id, user_id=invitee.id))
        db.commit()


def remove_co_organizer(db: Session, event_id: UUID, owner_id: UUID, co_user_id: UUID) -> None:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event or str(event.owner_id) != str(owner_id):
        raise HTTPException(status_code=403, detail="Only owner can remove co-organizers")
    db.query(EventCoOrganizer).filter(
        EventCoOrganizer.event_id == event_id,
        EventCoOrganizer.user_id == co_user_id,
    ).delete()
    db.commit()
