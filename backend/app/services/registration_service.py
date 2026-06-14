from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.participant import Participant
from app.schemas.participant import ParticipantRegister


_EXP_MAP = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3}
_SKILL_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "professional": 4}


def compute_composite_score(years_exp: int, skill_level: str, w_exp: float = 0.5, w_skill: float = 0.5) -> float:
    e = 4 if years_exp >= 7 else _EXP_MAP.get(years_exp, 1)
    k = _SKILL_MAP[skill_level]
    return round((w_exp * e) + (w_skill * k), 4)


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

    score = compute_composite_score(req.years_experience, req.skill_level)
    participant = Participant(
        event_id=event.id,
        composite_score=score,
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


def list_participants(db: Session, event_id: UUID, user_id: UUID, role: str = None, skill: str = None) -> list[Participant]:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    q = db.query(Participant).filter(Participant.event_id == event_id)
    if role:
        q = q.filter(Participant.role == role)
    if skill:
        q = q.filter(Participant.skill_level == skill)
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
