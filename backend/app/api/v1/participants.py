from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import Response as RawResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.models.user import User
from app.schemas.participant import ParticipantRegister, ParticipantOut, EventPublicInfo, ParticipantCategoryUpdate, ParticipantImportSummary
from app.services.registration_service import (
    get_public_event, register_participant, list_participants, delete_participant, override_category,
    export_participants_csv, import_participants_csv,
)

router = APIRouter()


@router.get(
    "/{slug}/info",
    response_model=EventPublicInfo,
    dependencies=[Depends(rate_limit("public-event-info", requests=60))],
)
def public_info(slug: str, db: Session = Depends(get_db)):
    return get_public_event(db, slug)


@router.post(
    "/{slug}/register",
    response_model=ParticipantOut,
    dependencies=[Depends(rate_limit("participant-registration", requests=20))],
)
def register(slug: str, req: ParticipantRegister, response: Response, db: Session = Depends(get_db)):
    participant, created = register_participant(db, slug, req)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return participant


@router.get("/{event_id}/participants", response_model=list[ParticipantOut])
def list_all(
    event_id: UUID,
    strength: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_participants(db, event_id, current_user.id, strength, experience, limit, offset)


@router.get("/{event_id}/participants/export/csv")
def export_participants(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = export_participants_csv(db, event_id, current_user.id)
    return RawResponse(content=data, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=squadsync-participants-{event_id}.csv"
    })


@router.post("/{event_id}/participants/import/csv", response_model=ParticipantImportSummary)
async def import_participants(
    event_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=415, detail="Upload must be a CSV file")
    chunks: list[bytes] = []
    size = 0
    while chunk := await file.read(64 * 1024):
        size += len(chunk)
        if size > settings.CSV_IMPORT_MAX_BYTES:
            from fastapi import HTTPException
            raise HTTPException(status_code=413, detail="CSV file is too large")
        chunks.append(chunk)
    content = b"".join(chunks)
    return import_participants_csv(db, event_id, current_user.id, content)


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
