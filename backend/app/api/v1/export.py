from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.services.event_service import assert_allocation_organizer
from app.services.export_service import generate_csv, generate_pdf, generate_share_link

router = APIRouter()


@router.get("/{allocation_id}/export/csv")
def export_csv(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assert_allocation_organizer(db, allocation_id, current_user.id)
    data = generate_csv(db, allocation_id)
    return Response(content=data, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename=squadsync-{allocation_id}.csv"
    })


@router.get("/{allocation_id}/export/pdf")
def export_pdf(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assert_allocation_organizer(db, allocation_id, current_user.id)
    data = generate_pdf(db, allocation_id)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=squadsync-{allocation_id}.pdf"
    })


@router.get("/{allocation_id}/export/link")
def export_link(allocation_id: UUID, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    assert_allocation_organizer(db, allocation_id, current_user.id)
    url = generate_share_link(allocation_id)
    return {"url": url}
