import hashlib
import json
import time

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import NostrAuthRequest


def verify_nostr_event(event: dict) -> bool:
    """Verify NIP-98 kind-27235 event: recompute ID then check BIP340 Schnorr sig."""
    try:
        serialized = json.dumps(
            [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        computed_id = hashlib.sha256(serialized.encode()).hexdigest()
        if event.get("id") != computed_id:
            return False

        from coincurve import PublicKeyXOnly
        pub = PublicKeyXOnly(bytes.fromhex(event["pubkey"]))
        return pub.verify(bytes.fromhex(event["sig"]), bytes.fromhex(computed_id))
    except Exception:
        return False


def nostr_login(db: Session, req: NostrAuthRequest) -> str:
    event = req.event

    if event.get("kind") != 27235:
        raise HTTPException(status_code=400, detail="Invalid event kind (expected 27235)")

    if event.get("pubkey") != req.pubkey:
        raise HTTPException(status_code=400, detail="Pubkey mismatch")

    if abs(time.time() - event.get("created_at", 0)) > 60:
        raise HTTPException(status_code=400, detail="Event expired")

    if not verify_nostr_event(event):
        raise HTTPException(status_code=401, detail="Invalid Nostr signature")

    user = db.query(User).filter(User.pubkey == req.pubkey).first()
    if not user:
        user = User(pubkey=req.pubkey)
        db.add(user)
        db.commit()
        db.refresh(user)

    return create_access_token(str(user.id))
