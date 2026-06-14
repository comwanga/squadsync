from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.schemas.auth import NostrAuthRequest, TokenResponse, UserOut
from app.services.auth_service import nostr_login

router = APIRouter()


@router.post("/nostr", response_model=TokenResponse)
def nostr_auth(req: NostrAuthRequest, request: Request, db: Session = Depends(get_db)):
    # Behind a proxy the live request URL is the internal http URL, not the public
    # https URL the client signed. Prefer the configured canonical URL when set.
    if settings.PUBLIC_API_URL:
        expected_url = settings.PUBLIC_API_URL.rstrip("/") + "/auth/nostr"
    else:
        expected_url = str(request.url)
    token = nostr_login(db, req, expected_url)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user
