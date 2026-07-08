import csv
import io
from uuid import UUID

from fastapi import HTTPException
from pydantic import ValidationError
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


def _apply_registration(existing: Participant | None, event_id: UUID, req: ParticipantRegister) -> Participant:
    is_preset = req.primary_strength != "other"
    score = compute_composite_score(req.experience_level)
    payload = req.model_dump()
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        existing.composite_score = score
        existing.normalized_strength = req.primary_strength if is_preset else None
        existing.strength_source = "preset"
        return existing
    return Participant(
        event_id=event_id,
        composite_score=score,
        normalized_strength=req.primary_strength if is_preset else None,
        strength_source="preset",
        **payload,
    )


def register_participant(db: Session, slug: str, req: ParticipantRegister) -> tuple[Participant, bool]:
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

    existing = db.query(Participant).filter(
        Participant.event_id == event.id,
        Participant.email == str(req.email),
    ).first()

    if event.participant_limit:
        count = db.query(Participant).filter(Participant.event_id == event.id).count()
        if not existing and count >= event.participant_limit:
            raise HTTPException(status_code=400, detail="Event is full")

    participant = _apply_registration(existing, event.id, req)
    if not existing:
        db.add(participant)
    # The unique (event_id, email) constraint is the authoritative dedup guard.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That email is already registered. Refresh and try again.")
    db.refresh(participant)
    return participant, existing is None


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


def export_participants_csv(db: Session, event_id: UUID, user_id: UUID) -> bytes:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    participants = db.query(Participant).filter(Participant.event_id == event_id).order_by(Participant.name).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "name", "email", "phone", "primary_strength", "strength_other",
        "experience_level", "notification_id", "prize_address",
    ])
    for p in participants:
        writer.writerow([
            p.name, p.email, p.phone or "", p.primary_strength, p.strength_other or "",
            p.experience_level, p.npub or "", p.lightning_address or "",
        ])
    return buf.getvalue().encode("utf-8")


def import_participants_csv(db: Session, event_id: UUID, user_id: UUID, content: bytes) -> dict:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    event = db.query(Event).filter(Event.id == event_id).with_for_update().first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if event.status == "archived":
        raise HTTPException(status_code=400, detail="Archived events cannot import participants")

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is empty")

    created = updated = skipped = 0
    errors: list[str] = []
    for line_number, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            skipped += 1
            continue
        try:
            req = ParticipantRegister(
                name=(row.get("name") or row.get("Name") or "").strip(),
                email=(row.get("email") or row.get("Email") or "").strip(),
                phone=(row.get("phone") or row.get("Phone") or None),
                primary_strength=(row.get("primary_strength") or row.get("Primary Strength") or "").strip(),
                strength_other=(row.get("strength_other") or row.get("Strength Other") or None),
                experience_level=(row.get("experience_level") or row.get("Experience") or "").strip(),
                npub=(row.get("notification_id") or row.get("npub") or None),
                lightning_address=(row.get("prize_address") or row.get("lightning_address") or None),
            )
        except ValidationError as exc:
            errors.append(f"Line {line_number}: {exc.errors()[0]['msg']}")
            continue

        existing = db.query(Participant).filter(
            Participant.event_id == event_id,
            Participant.email == str(req.email),
        ).first()
        if event.participant_limit and not existing:
            count = db.query(Participant).filter(Participant.event_id == event_id).count()
            if count >= event.participant_limit:
                errors.append(f"Line {line_number}: event is full")
                continue
        participant = _apply_registration(existing, event_id, req)
        if existing:
            updated += 1
        else:
            db.add(participant)
            created += 1

    if errors:
        db.rollback()
        return {"created": 0, "updated": 0, "skipped": skipped, "errors": errors}

    db.commit()
    return {"created": created, "updated": updated, "skipped": skipped, "errors": []}
