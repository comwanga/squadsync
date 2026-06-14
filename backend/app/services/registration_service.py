from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.participant import Participant
from app.schemas.participant import ParticipantRegister
from app.services.allocation_engine import compute_composite_score


def get_public_event(db: Session, slug: str) -> Event:
    event = db.query(Event).filter(Event.registration_slug == slug).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def register_participant(db: Session, slug: str, req: ParticipantRegister) -> Participant:
    # Lock the event row so concurrent registrations for the same event are
    # serialized (no-op on SQLite, which already serializes writes). This makes
    # the participant-limit check race-free on PostgreSQL.
    event = (
        db.query(Event)
        .filter(Event.registration_slug == slug)
        .with_for_update()
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status not in ("active",):
        raise HTTPException(status_code=400, detail="Event is not accepting registrations")

    if event.participant_limit:
        count = db.query(Participant).filter(Participant.event_id == event.id).count()
        if count >= event.participant_limit:
            raise HTTPException(status_code=400, detail="Event is full")

    is_preset = req.primary_strength != "other"
    score = compute_composite_score(req.experience_level)
    participant = Participant(
        event_id=event.id,
        composite_score=score,
        normalized_strength=req.primary_strength if is_preset else None,
        strength_source="preset",
        **req.model_dump(),
    )
    db.add(participant)
    # The unique (event_id, email) constraint is the authoritative dedup guard.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered for this event")
    db.refresh(participant)
    return participant


def list_participants(db: Session, event_id: UUID, user_id: UUID, strength: str = None, experience: str = None) -> list[Participant]:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    q = db.query(Participant).filter(Participant.event_id == event_id)
    if strength:
        q = q.filter(Participant.normalized_strength == strength)
    if experience:
        q = q.filter(Participant.experience_level == experience)
    return q.all()


def delete_participant(db: Session, event_id: UUID, participant_id: UUID, user_id: UUID) -> Participant:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    p = db.query(Participant).filter(Participant.id == participant_id, Participant.event_id == event_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    db.delete(p)
    db.commit()
    return p


def override_category(db: Session, event_id: UUID, participant_id: UUID, user_id: UUID, normalized_strength: str) -> Participant:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    p = db.query(Participant).filter(
        Participant.id == participant_id, Participant.event_id == event_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    p.normalized_strength = normalized_strength
    p.strength_source = "manual"
    db.commit()
    db.refresh(p)
    return p
