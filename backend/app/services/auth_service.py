from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests


def register_user(db: Session, req: RegisterRequest) -> str:
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        name=req.name,
        email=req.email,
        hashed_password=hash_password(req.password),
        provider="local",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return create_access_token(str(user.id))


def login_user(db: Session, req: LoginRequest) -> str:
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.hashed_password or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return create_access_token(str(user.id))


def verify_google_token(token: str) -> dict:
    return id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_CLIENT_ID)


def google_login(db: Session, token: str) -> str:
    idinfo = verify_google_token(token)
    google_sub = idinfo["sub"]
    email = idinfo["email"]
    name = idinfo.get("name", email)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email, provider="google", provider_id=google_sub)
        db.add(user)
        db.commit()
        db.refresh(user)
    return create_access_token(str(user.id))
