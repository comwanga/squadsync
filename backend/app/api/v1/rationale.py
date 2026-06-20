from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.services.event_service import assert_allocation_organizer
from app.services import rationale_service
from app.services.rationale_service import RationaleUnavailable

router = APIRouter()


@router.post("/{allocation_id}/rationale")
def generate_rationale(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    try:
        return rationale_service.generate(db, allocation)
    except RationaleUnavailable as exc:
        raise HTTPException(status_code=400, detail=str(exc))
