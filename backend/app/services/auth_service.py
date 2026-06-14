import hashlib
import json
import time

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.used_event import UsedAuthEvent
from app.models.user import User
from app.schemas.auth import NostrAuthRequest


def verify_nostr_event(event: dict, expected_url: str) -> bool:
    """Verify NIP-98 kind-27235 event: ID hash, Schnorr sig, and URL/method tag binding."""
    try:
        serialized = json.dumps(
            [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        computed_id = hashlib.sha256(serialized.encode()).hexdigest()
        if event.get("id") != computed_id:
            return False

        tags = event.get("tags", [])
        u_vals = [t[1] for t in tags if len(t) >= 2 and t[0] == "u"]
        method_vals = [t[1] for t in tags if len(t) >= 2 and t[0] == "method"]
        if not u_vals or u_vals[0] != expected_url:
            return False
        if not method_vals or method_vals[0] != "POST":
            return False

        from coincurve import PublicKeyXOnly
        pub = PublicKeyXOnly(bytes.fromhex(event["pubkey"]))
        return pub.verify(bytes.fromhex(event["sig"]), bytes.fromhex(computed_id))
    except Exception:
        return False


def nostr_login(db: Session, req: NostrAuthRequest, expected_url: str) -> str:
    event = req.event

    if event.get("kind") != 27235:
        raise HTTPException(status_code=400, detail="Invalid event kind (expected 27235)")

    if event.get("pubkey") != req.pubkey:
        raise HTTPException(status_code=400, detail="Pubkey mismatch")

    now = time.time()
    created_at = event.get("created_at", 0)
    # Reject stale events and events dated meaningfully in the future (clock skew).
    if created_at > now + 5 or now - created_at > 60:
        raise HTTPException(status_code=400, detail="Event expired")

    if not verify_nostr_event(event, expected_url):
        raise HTTPException(status_code=401, detail="Invalid Nostr signature")

    # Replay protection: a verified event ID may only be redeemed once (NIP-98).
    event_id = event.get("id")
    if db.query(UsedAuthEvent).filter(UsedAuthEvent.event_id == event_id).first():
        raise HTTPException(status_code=401, detail="Replay detected — event already used")
    db.add(UsedAuthEvent(event_id=event_id))

    user = db.query(User).filter(User.pubkey == req.pubkey).first()
    if not user:
        user = User(pubkey=req.pubkey)
        db.add(user)

    # Commit both the consumed event and any new user atomically. A concurrent
    # replay of the same event hits the used_auth_events PK and is rejected.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=401, detail="Replay detected — event already used")
    db.refresh(user)

    return create_access_token(str(user.id))
