from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.config import settings
from app.models.feedback import Feedback
from app.models.user import User
from app.schemas.feedback import FeedbackIn
from app.services.nostr_service import send_dm

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
def submit_feedback(
    payload: FeedbackIn,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Persist feedback (source of truth) and best-effort DM the owner.

    The DB write is the durable record; the Nostr DM is fire-and-forget and
    never blocks or fails this response. The submitter is identified by their
    raw hex pubkey (no npub encoding needed).
    """
    row = Feedback(user_id=current_user.id, message=payload.message)
    db.add(row)
    db.commit()

    if settings.FEEDBACK_NPUB:
        background_tasks.add_task(
            send_dm,
            settings.FEEDBACK_NPUB,
            f"SquadSync feedback from {current_user.pubkey}:\n\n{payload.message}",
        )

    return {"detail": "received"}
