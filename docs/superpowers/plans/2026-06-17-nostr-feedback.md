# Nostr-Send Infra + Feedback Box (B2a) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a best-effort server-side Nostr NIP-04 DM sender (from a dedicated bot key to a recipient npub) and use it for a Settings feedback box that persists feedback to the DB and DMs the owner.

**Architecture:** A self-contained `nostr_service` decodes bech32 keys in-repo, encrypts with NIP-04 (secp256k1 ECDH raw-X via `coincurve` point-multiply + AES-256-CBC via `cryptography`), builds and schnorr-signs a kind-4 event, and publishes it to configurable relays over websockets. `send_dm` never raises and no-ops when unconfigured. A `POST /api/v1/feedback` endpoint persists a `Feedback` row (source of truth) and fires the DM via FastAPI `BackgroundTasks`. The Settings page gains a feedback card.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest (backend); `coincurve` (ECDH + schnorr), `cryptography` (AES-CBC), `websockets` (sync relay client); Next.js 16 / React 19 / Vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-06-17-nostr-feedback-design.md`

**Branch:** `feat/nostr-feedback` (already created off `main`). Commit messages must NOT include any Co-Authored-By line.

**Verified facts (do not re-derive):**
- `coincurve==20.0.0`'s `PrivateKey.ecdh()` takes **no** `hashfn` argument. Get the NIP-04 raw-X shared secret via point multiplication: `PublicKey(b"\x02" + peer_xonly).multiply(priv.secret).format(compressed=False)[1:33]`. This was confirmed to match for both parties.
- `PrivateKey.sign_schnorr(msg_32_bytes)` returns a 64-byte signature; `PublicKeyXOnly(xonly).verify(sig, msg)` validates it.
- `PrivateKey.public_key_xonly.format()` returns the 32-byte x-only pubkey.
- The bech32 decoder below was confirmed against NIP-19 vectors:
  - `npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6` → `3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d`
  - `nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9` → `67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa`
- `websockets==12.0` provides a sync client at `websockets.sync.client.connect`.
- Backend test fixtures: `client`, `auth_headers`, `db` (see `backend/tests/conftest.py`). Run tests from `backend/` with `pytest -q`.

---

## File Structure

**Backend (create):**
- `backend/app/services/nostr_service.py` — bech32 decode, NIP-04 encrypt/decrypt, event build/sign, relay publish, `send_dm`.
- `backend/app/models/feedback.py` — `Feedback` ORM model.
- `backend/alembic/versions/0005_feedback.py` — additive `feedback` table.
- `backend/app/api/v1/feedback.py` — `POST /api/v1/feedback`.
- `backend/app/schemas/feedback.py` — `FeedbackIn` request schema.
- `backend/tests/test_nostr_service.py` — crypto/bech32/no-op tests.
- `backend/tests/test_feedback.py` — endpoint tests.

**Backend (modify):**
- `backend/requirements.txt` — pin `cryptography` and `websockets`.
- `backend/app/core/config.py` — add `SQUADSYNC_NSEC`, `FEEDBACK_NPUB`, `NOSTR_RELAYS`, `nostr_relays`.
- `backend/app/models/__init__.py` — register `Feedback`.
- `backend/app/main.py` — mount feedback router.

**Frontend (create):**
- `frontend/components/settings/feedback-card.tsx` — feedback card client component.
- `frontend/tests/components/feedback-card.test.tsx` — component test.

**Frontend (modify):**
- `frontend/app/dashboard/settings/page.tsx` — render `<FeedbackCard />`.

**Docs (modify):**
- `backend/render.yaml` and `DEPLOYMENT.md` (or repo root deploy doc) — document the three new optional env vars.

---

## Task 1: Pin crypto/websocket dependencies

**Files:**
- Modify: `backend/requirements.txt`

`cryptography` and `websockets` are currently only transitive deps (via `python-jose[cryptography]` and `uvicorn[standard]`). The Nostr service imports them directly, so pin them explicitly.

- [ ] **Step 1: Add explicit pins**

Append to `backend/requirements.txt` (after line 16, `aiosqlite==0.20.0`, keeping existing lines):

```
cryptography==42.0.8
websockets==12.0
```

- [ ] **Step 2: Verify they install/import**

Run: `cd backend && python -c "import cryptography, websockets; from websockets.sync.client import connect; print('ok', cryptography.__version__, websockets.__version__)"`
Expected: prints `ok 42.0.8 12.0` (already installed; this confirms the pins match the environment).

> If `pip` reports `cryptography==42.0.8` is unavailable in the deploy environment, pin to whatever `python -c "import cryptography; print(cryptography.__version__)"` reports locally instead — the import, not the exact patch, is what matters.

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "build(backend): pin cryptography and websockets for Nostr service"
```

---

## Task 2: Config — Nostr env vars

**Files:**
- Modify: `backend/app/core/config.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_nostr_service.py`:

```python
from app.core.config import Settings


def test_nostr_relays_defaults_split_on_comma():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x")
    assert s.nostr_relays == [
        "wss://relay.damus.io",
        "wss://nos.lol",
        "wss://relay.nostr.band",
    ]


def test_nostr_relays_override_and_strip():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x", NOSTR_RELAYS=" wss://a , wss://b ")
    assert s.nostr_relays == ["wss://a", "wss://b"]


def test_nostr_keys_default_unset():
    s = Settings(DATABASE_URL="sqlite://", SECRET_KEY="x")
    assert s.SQUADSYNC_NSEC is None
    assert s.FEEDBACK_NPUB is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: FAIL — `AttributeError`/`ValidationError` (`nostr_relays`/`NOSTR_RELAYS` not defined).

- [ ] **Step 3: Add the settings**

In `backend/app/core/config.py`, add these fields inside `Settings` (after `CATEGORIZATION_MODEL`, before `class Config`):

```python
    # --- Nostr DM sender (all optional; unset → DM sending is a no-op) ---
    # Dedicated *bot* secret key (bech32 `nsec1…`) used ONLY to sign/encrypt
    # outgoing DMs. NEVER put a personal nsec here. When unset, send_dm no-ops.
    SQUADSYNC_NSEC: str | None = None
    # Recipient for the Settings feedback box (bech32 `npub1…`, the owner's public key).
    FEEDBACK_NPUB: str | None = None
    # Comma-separated relay websocket URLs to publish DMs to.
    NOSTR_RELAYS: str = "wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band"

    @property
    def nostr_relays(self) -> list[str]:
        return [r.strip() for r in self.NOSTR_RELAYS.split(",") if r.strip()]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): add Nostr DM config (SQUADSYNC_NSEC, FEEDBACK_NPUB, NOSTR_RELAYS)"
```

---

## Task 3: bech32 decode helper

**Files:**
- Create: `backend/app/services/nostr_service.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_nostr_service.py`:

```python
from app.services import nostr_service


def test_bech32_decode_npub_vector():
    hrp, key = nostr_service.bech32_decode(
        "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    )
    assert hrp == "npub"
    assert key.hex() == "3bf0c63fcb93463407af97a5e5ee64fa883d107ef9e558472c4eb9aaaefa459d"


def test_bech32_decode_nsec_vector():
    hrp, key = nostr_service.bech32_decode(
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9"
    )
    assert hrp == "nsec"
    assert key.hex() == "67dea2ed018072d675f5415ecfaed7d2597555e202d85b3d65ea4e58d2d92ffa"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.nostr_service`.

- [ ] **Step 3: Create the module with the bech32 decoder**

Create `backend/app/services/nostr_service.py`:

```python
"""Best-effort Nostr NIP-04 DM sender.

Self-contained: decodes bech32 keys, encrypts/signs a kind-4 event, and
publishes it to relays. `send_dm` never raises and no-ops when unconfigured.
Personal secret keys must never be stored — `SQUADSYNC_NSEC` is a dedicated bot key.
"""
import logging

logger = logging.getLogger(__name__)

_BECH32_CHARSET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


def bech32_decode(bech: str) -> tuple[str, bytes]:
    """Decode a bech32 `npub`/`nsec` to (hrp, 32-byte key).

    Minimal decoder: splits on the last '1', drops the 6-char checksum, and
    converts the 5-bit data groups to 8-bit bytes. Sufficient for npub/nsec.
    """
    bech = bech.strip().lower()
    pos = bech.rfind("1")
    if pos < 1:
        raise ValueError("invalid bech32 string")
    hrp = bech[:pos]
    try:
        data = [_BECH32_CHARSET.index(c) for c in bech[pos + 1:]]
    except ValueError as exc:
        raise ValueError("invalid bech32 character") from exc
    data = data[:-6]  # drop checksum
    acc = 0
    bits = 0
    out = bytearray()
    for value in data:
        acc = (acc << 5) | value
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return hrp, bytes(out)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: PASS (5 passed total).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nostr_service.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): add in-repo bech32 decoder for Nostr keys"
```

---

## Task 4: NIP-04 encrypt/decrypt round-trip

**Files:**
- Modify: `backend/app/services/nostr_service.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_nostr_service.py`:

```python
from coincurve import PrivateKey


def test_nip04_encrypt_decrypt_round_trip():
    bot = PrivateKey()
    recipient = PrivateKey()
    recipient_xonly = recipient.public_key_xonly.format()
    bot_xonly = bot.public_key_xonly.format()

    message = "Hello from SquadSync — café ☕"
    content = nostr_service.encrypt_nip04(bot.secret, recipient_xonly, message)
    assert "?iv=" in content

    # Recipient decrypts with their privkey + the bot's x-only pubkey.
    recovered = nostr_service.decrypt_nip04(recipient.secret, bot_xonly, content)
    assert recovered == message
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_nostr_service.py::test_nip04_encrypt_decrypt_round_trip -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'encrypt_nip04'`.

- [ ] **Step 3: Implement the crypto helpers**

Add to the top imports of `backend/app/services/nostr_service.py` (below `import logging`):

```python
import base64
import os

from coincurve import PrivateKey, PublicKey
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
```

Then append these functions to `backend/app/services/nostr_service.py`:

```python
def _shared_secret(privkey_bytes: bytes, peer_xonly: bytes) -> bytes:
    """secp256k1 ECDH raw-X shared secret (NIP-04).

    Reconstruct the peer point from its x-only key (assume even Y, the Nostr
    convention), multiply by our scalar, and take the raw 32-byte X coordinate.
    coincurve's `ecdh()` hashes the result, so we point-multiply instead.
    """
    peer_point = PublicKey(b"\x02" + peer_xonly)
    product = peer_point.multiply(privkey_bytes)
    return product.format(compressed=False)[1:33]


def encrypt_nip04(privkey_bytes: bytes, peer_xonly: bytes, message: str) -> str:
    """NIP-04 encrypt `message` → `base64(ciphertext)?iv=base64(iv)`."""
    key = _shared_secret(privkey_bytes, peer_xonly)
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    data = padder.update(message.encode("utf-8")) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()
    return base64.b64encode(ciphertext).decode() + "?iv=" + base64.b64encode(iv).decode()


def decrypt_nip04(privkey_bytes: bytes, peer_xonly: bytes, content: str) -> str:
    """Inverse of `encrypt_nip04` (used by tests to prove the round trip)."""
    key = _shared_secret(privkey_bytes, peer_xonly)
    b64_ct, b64_iv = content.split("?iv=")
    iv = base64.b64decode(b64_iv)
    ciphertext = base64.b64decode(b64_ct)
    decryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return (unpadder.update(padded) + unpadder.finalize()).decode("utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_nostr_service.py::test_nip04_encrypt_decrypt_round_trip -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nostr_service.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): add NIP-04 encrypt/decrypt (ECDH raw-X + AES-256-CBC)"
```

---

## Task 5: Build + sign the kind-4 event

**Files:**
- Modify: `backend/app/services/nostr_service.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_nostr_service.py`:

```python
import hashlib
import json

from coincurve import PublicKeyXOnly


def test_build_signed_event_has_valid_id_and_sig():
    bot = PrivateKey()
    recipient = PrivateKey()
    recipient_xonly = recipient.public_key_xonly.format()

    event = nostr_service.build_dm_event(bot.secret, recipient_xonly, "hi there")

    assert event["kind"] == 4
    assert event["tags"] == [["p", recipient_xonly.hex()]]
    assert event["pubkey"] == bot.public_key_xonly.format().hex()

    # id == sha256 of NIP-01 serialization
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert event["id"] == hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    # sig verifies against the bot's x-only pubkey over the id bytes
    assert PublicKeyXOnly(bot.public_key_xonly.format()).verify(
        bytes.fromhex(event["sig"]), bytes.fromhex(event["id"])
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_nostr_service.py::test_build_signed_event_has_valid_id_and_sig -q`
Expected: FAIL — `AttributeError: ... 'build_dm_event'`.

- [ ] **Step 3: Implement `build_dm_event`**

Add to the imports of `backend/app/services/nostr_service.py`:

```python
import hashlib
import json
import time
```

Append to `backend/app/services/nostr_service.py`:

```python
def build_dm_event(privkey_bytes: bytes, recipient_xonly: bytes, message: str) -> dict:
    """Build a signed NIP-04 kind-4 DM event (NIP-01 serialization for the id)."""
    privkey = PrivateKey(privkey_bytes)
    pubkey_hex = privkey.public_key_xonly.format().hex()
    created_at = int(time.time())
    content = encrypt_nip04(privkey_bytes, recipient_xonly, message)
    tags = [["p", recipient_xonly.hex()]]

    serialized = json.dumps(
        [0, pubkey_hex, created_at, 4, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sig = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()

    return {
        "id": event_id,
        "pubkey": pubkey_hex,
        "created_at": created_at,
        "kind": 4,
        "tags": tags,
        "content": content,
        "sig": sig,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_nostr_service.py::test_build_signed_event_has_valid_id_and_sig -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nostr_service.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): build + schnorr-sign NIP-04 kind-4 event"
```

---

## Task 6: `send_dm` — publish + no-op guard

**Files:**
- Modify: `backend/app/services/nostr_service.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_nostr_service.py`:

```python
def test_send_dm_noop_when_unconfigured(monkeypatch):
    monkeypatch.setattr(nostr_service.settings, "SQUADSYNC_NSEC", None, raising=False)
    # Must return False and NOT raise, even with a bad recipient.
    assert nostr_service.send_dm("npub-not-real", "hi") is False


def test_send_dm_returns_true_when_a_relay_accepts(monkeypatch):
    # Configure a valid bot key (the NIP-19 nsec test vector).
    monkeypatch.setattr(
        nostr_service.settings,
        "SQUADSYNC_NSEC",
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9",
        raising=False,
    )
    monkeypatch.setattr(nostr_service.settings, "NOSTR_RELAYS", "wss://relay.test", raising=False)

    published = {}

    def fake_publish(event, relays):
        published["event"] = event
        published["relays"] = relays
        return True

    monkeypatch.setattr(nostr_service, "_publish_to_relays", fake_publish)

    recipient = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    assert nostr_service.send_dm(recipient, "hello") is True
    assert published["event"]["kind"] == 4
    assert published["relays"] == ["wss://relay.test"]


def test_send_dm_swallows_publish_errors(monkeypatch):
    monkeypatch.setattr(
        nostr_service.settings,
        "SQUADSYNC_NSEC",
        "nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9",
        raising=False,
    )

    def boom(event, relays):
        raise RuntimeError("relay down")

    monkeypatch.setattr(nostr_service, "_publish_to_relays", boom)
    recipient = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    # Never propagates — returns False.
    assert nostr_service.send_dm(recipient, "hello") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: FAIL — `AttributeError: ... 'send_dm'` (and `settings` not imported).

- [ ] **Step 3: Implement `send_dm` and the relay publisher**

Add to the imports of `backend/app/services/nostr_service.py`:

```python
from app.core.config import settings
```

Append to `backend/app/services/nostr_service.py`:

```python
def _publish_to_relays(event: dict, relays: list[str]) -> bool:
    """Open a short-lived websocket to each relay, send the EVENT, read one OK.

    Returns True if at least one relay accepted. Per-relay errors are swallowed.
    Imported lazily so the rest of the module has no hard websockets dependency
    at import time (and tests monkeypatch this function).
    """
    from websockets.sync.client import connect

    payload = json.dumps(["EVENT", event])
    accepted = False
    for relay in relays:
        try:
            with connect(relay, open_timeout=5, close_timeout=5) as ws:
                ws.send(payload)
                ws.recv(timeout=5)  # best-effort: drain one frame (OK/NOTICE)
                accepted = True
        except Exception as exc:  # noqa: BLE001 — best-effort, never propagate
            logger.warning("Nostr relay %s rejected/failed: %s", relay, exc)
    return accepted


def send_dm(recipient_npub: str, message: str) -> bool:
    """Best-effort NIP-04 DM from the bot key to `recipient_npub`.

    No-ops (returns False) when `SQUADSYNC_NSEC` is unset. Never raises — all
    failures are logged and swallowed so callers (e.g. BackgroundTasks) are safe.
    """
    if not settings.SQUADSYNC_NSEC:
        logger.info("send_dm skipped: SQUADSYNC_NSEC not configured")
        return False
    try:
        _, privkey_bytes = bech32_decode(settings.SQUADSYNC_NSEC)
        _, recipient_xonly = bech32_decode(recipient_npub)
        event = build_dm_event(privkey_bytes, recipient_xonly, message)
        return _publish_to_relays(event, settings.nostr_relays)
    except Exception as exc:  # noqa: BLE001 — best-effort, never propagate
        logger.warning("send_dm failed: %s", exc)
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_nostr_service.py -q`
Expected: PASS (all nostr_service tests pass).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nostr_service.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): add best-effort send_dm with relay publish + no-op guard"
```

---

## Task 7: Feedback model + migration

**Files:**
- Create: `backend/app/models/feedback.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0005_feedback.py`

- [ ] **Step 1: Create the model**

Create `backend/app/models/feedback.py`:

```python
import uuid
from sqlalchemy import Column, Text, ForeignKey, DateTime, Uuid
from sqlalchemy.sql import func

from app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 2: Register the model**

Edit `backend/app/models/__init__.py` to import and export `Feedback`:

```python
from app.models.user import User
from app.models.event import Event, EventCoOrganizer
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember
from app.models.used_event import UsedAuthEvent
from app.models.feedback import Feedback

__all__ = [
    "User", "Event", "EventCoOrganizer", "Participant",
    "AllocationConfig", "Allocation", "Team", "TeamMember",
    "UsedAuthEvent", "Feedback",
]
```

- [ ] **Step 3: Create the migration**

Create `backend/alembic/versions/0005_feedback.py`:

```python
"""feedback

Revision ID: 0005_feedback
Revises: 0004_event_at
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_feedback"
down_revision: Union[str, None] = "0004_event_at"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_user_id", "feedback", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")
```

- [ ] **Step 4: Verify the model imports and migration chain is valid**

Run: `cd backend && python -c "import app.models; print(app.models.Feedback.__tablename__)"`
Expected: prints `feedback`.

Run: `cd backend && python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; s=ScriptDirectory.from_config(Config('alembic.ini')); print(s.get_current_head())"`
Expected: prints `0005_feedback` (single head — chain is linear).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/feedback.py backend/app/models/__init__.py backend/alembic/versions/0005_feedback.py
git commit -m "feat(backend): add Feedback model + 0005 migration"
```

---

## Task 8: Feedback API endpoint

**Files:**
- Create: `backend/app/schemas/feedback.py`
- Create: `backend/app/api/v1/feedback.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_feedback.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_feedback.py`:

```python
from app.api.v1 import feedback as feedback_api


def test_feedback_requires_auth(client):
    res = client.post("/api/v1/feedback", json={"message": "hello"})
    assert res.status_code in (401, 403)


def test_feedback_persists_and_returns_201(client, auth_headers, db, monkeypatch):
    # No DM should be attempted unless FEEDBACK_NPUB is set; assert it stays unsent.
    calls = []
    monkeypatch.setattr(feedback_api, "send_dm", lambda *a, **k: calls.append(a) or True)
    monkeypatch.setattr(feedback_api.settings, "FEEDBACK_NPUB", None, raising=False)

    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "great app"})
    assert res.status_code == 201
    assert res.json() == {"detail": "received"}

    from app.models.feedback import Feedback
    rows = db.query(Feedback).all()
    assert len(rows) == 1
    assert rows[0].message == "great app"
    assert calls == []  # unconfigured recipient → no DM scheduled


def test_feedback_schedules_dm_when_npub_set(client, auth_headers, monkeypatch):
    calls = []
    monkeypatch.setattr(feedback_api, "send_dm", lambda npub, msg: calls.append((npub, msg)) or True)
    monkeypatch.setattr(
        feedback_api.settings, "FEEDBACK_NPUB", "npub1ownerxxxxxxxxxxxxxxxxxxxxxxxxxxx", raising=False
    )

    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "ping"})
    assert res.status_code == 201
    assert len(calls) == 1
    npub, msg = calls[0]
    assert npub == "npub1ownerxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    assert "ping" in msg


def test_feedback_rejects_empty_message(client, auth_headers):
    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": ""})
    assert res.status_code == 422


def test_feedback_rejects_overlong_message(client, auth_headers):
    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "x" * 2001})
    assert res.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_feedback.py -q`
Expected: FAIL — `ModuleNotFoundError: app.api.v1.feedback`.

- [ ] **Step 3: Create the request schema**

Create `backend/app/schemas/feedback.py`:

```python
from pydantic import BaseModel, Field


class FeedbackIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
```

- [ ] **Step 4: Create the endpoint**

Create `backend/app/api/v1/feedback.py`:

```python
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
```

- [ ] **Step 5: Mount the router**

Edit `backend/app/main.py`: add `feedback` to the v1 import and include its router.

Change the import line:
```python
from app.api.v1 import auth, events, participants, allocation, teams, export, public, feedback
```

Add after the `public` router line (line 32):
```python
app.include_router(feedback.router, prefix="/api/v1/feedback", tags=["feedback"])
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_feedback.py -q`
Expected: PASS (5 passed).

> Note: FastAPI runs `BackgroundTasks` after the response is sent. With `TestClient`, the task runs synchronously before the call returns, so the `send_dm` monkeypatch in `test_feedback_schedules_dm_when_npub_set` is invoked and recorded.

- [ ] **Step 7: Run the full backend suite (no regressions)**

Run: `cd backend && pytest -q`
Expected: PASS (all tests, including pre-existing).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/feedback.py backend/app/api/v1/feedback.py backend/app/main.py backend/tests/test_feedback.py
git commit -m "feat(backend): add POST /api/v1/feedback (persist + best-effort DM)"
```

---

## Task 9: Settings feedback card (frontend)

**Files:**
- Create: `frontend/components/settings/feedback-card.tsx`
- Create: `frontend/tests/components/feedback-card.test.tsx`
- Modify: `frontend/app/dashboard/settings/page.tsx`

> Before writing frontend code, heed `frontend/AGENTS.md`: this is a modified Next.js 16 — check `node_modules/next/dist/docs/` if you touch routing/server APIs. This task is a client component using existing patterns (`fetchAPI`, `useSession`, `sonner` toast, `Button`, `Card`), so no new Next APIs are involved.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/components/feedback-card.test.tsx`:

```tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchAPI } from "@/lib/api";
import { FeedbackCard } from "@/components/settings/feedback-card";

vi.mock("@/lib/api", () => ({ fetchAPI: vi.fn() }));
vi.mock("next-auth/react", () => ({ useSession: () => ({ data: { accessToken: "token" } }) }));
const toast = { success: vi.fn(), error: vi.fn() };
vi.mock("sonner", () => ({ toast: { success: (m: string) => toast.success(m), error: (m: string) => toast.error(m) } }));

beforeEach(() => vi.clearAllMocks());

describe("FeedbackCard", () => {
  it("submits feedback and shows a success toast", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockResolvedValue({ detail: "received" });
    render(<FeedbackCard />);
    fireEvent.change(screen.getByLabelText(/feedback/i), { target: { value: "love it" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(fetchAPI).toHaveBeenCalledWith(
      "/api/v1/feedback",
      expect.objectContaining({ method: "POST", body: { message: "love it" }, token: "token" }),
    ));
    await waitFor(() => expect(toast.success).toHaveBeenCalled());
  });

  it("shows an error toast on failure", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("boom"));
    render(<FeedbackCard />);
    fireEvent.change(screen.getByLabelText(/feedback/i), { target: { value: "x" } });
    fireEvent.click(screen.getByRole("button", { name: /send/i }));
    await waitFor(() => expect(toast.error).toHaveBeenCalled());
  });

  it("disables send when the message is empty", () => {
    render(<FeedbackCard />);
    expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- feedback-card`
Expected: FAIL — cannot resolve `@/components/settings/feedback-card`.

- [ ] **Step 3: Create the component**

Create `frontend/components/settings/feedback-card.tsx`:

```tsx
"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { MessageSquare, Loader2 } from "lucide-react";
import { fetchAPI } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export function FeedbackCard() {
  const { data: session } = useSession();
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!message.trim() || !session?.accessToken) return;
    setSending(true);
    try {
      await fetchAPI("/api/v1/feedback", {
        method: "POST",
        body: { message: message.trim() },
        token: session.accessToken,
      });
      toast.success("Thanks for the feedback!");
      setMessage("");
    } catch {
      toast.error("Couldn't send feedback. Please try again.");
    } finally {
      setSending(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <MessageSquare className="h-5 w-5 text-primary" />
          <div>
            <CardTitle className="text-base">Send feedback</CardTitle>
            <CardDescription>Tell us what's working or what could be better</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <label htmlFor="feedback" className="sr-only">Feedback</label>
        <textarea
          id="feedback"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={2000}
          rows={4}
          placeholder="Your feedback…"
          className="w-full resize-none rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
        <Button onClick={handleSend} disabled={sending || !message.trim()} className="w-full">
          {sending ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending…</>
          ) : (
            "Send feedback"
          )}
        </Button>
      </CardContent>
    </Card>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- feedback-card`
Expected: PASS (3 passed).

- [ ] **Step 5: Render the card on the Settings page**

Edit `frontend/app/dashboard/settings/page.tsx`:

Add the import (after the Card import line):
```tsx
import { FeedbackCard } from "@/components/settings/feedback-card";
```

Add `<FeedbackCard />` inside the root `<div className="space-y-6 max-w-lg">`, after the Guide `<Link>...</Link>` block (just before the closing `</div>`):
```tsx
      <FeedbackCard />
```

- [ ] **Step 6: Typecheck, lint, and run the full frontend suite**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: tsc clean, lint clean, all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/settings/feedback-card.tsx frontend/tests/components/feedback-card.test.tsx frontend/app/dashboard/settings/page.tsx
git commit -m "feat(frontend): add Settings feedback card"
```

---

## Task 10: Document the new env vars

**Files:**
- Modify: `backend/render.yaml`
- Modify: deploy doc (`DEPLOYMENT.md` at repo root if present; otherwise add a short "Nostr DM (optional)" section to the backend README)

- [ ] **Step 1: Locate the deploy docs**

Run: `ls C:/Users/mwang/squadsync/DEPLOYMENT.md C:/Users/mwang/squadsync/backend/render.yaml 2>/dev/null; grep -rln "envVars\|FRONTEND_URL" C:/Users/mwang/squadsync/backend/render.yaml C:/Users/mwang/squadsync/render.yaml 2>/dev/null`
Expected: shows which file holds the Render env var list. Use whichever exists.

- [ ] **Step 2: Add the three optional vars to `render.yaml`**

In the backend service's `envVars:` list, add (these are optional; leave unset to disable DMs):

```yaml
      - key: SQUADSYNC_NSEC
        sync: false
      - key: FEEDBACK_NPUB
        sync: false
      - key: NOSTR_RELAYS
        sync: false
```

(`sync: false` keeps the secret out of the blueprint and prompts for it in the Render dashboard.)

- [ ] **Step 3: Document them in the deploy doc**

Add a short section to the deploy doc:

```markdown
### Nostr DM (optional)

The Settings feedback box and (later) team notifications send Nostr NIP-04 DMs.
All three vars are optional — leave them unset and feedback is still saved to the DB,
the DM is simply skipped.

- `SQUADSYNC_NSEC` — a **dedicated bot** secret key (`nsec1…`). Never use a personal nsec.
- `FEEDBACK_NPUB` — the owner's public key (`npub1…`) that receives feedback DMs.
- `NOSTR_RELAYS` — comma-separated relay URLs (defaults to damus / nos.lol / nostr.band).
```

- [ ] **Step 4: Commit**

```bash
git add backend/render.yaml DEPLOYMENT.md
git commit -m "docs: document optional Nostr DM env vars"
```

---

## Final verification (after all tasks)

- [ ] Run the full backend suite: `cd backend && pytest -q` → all pass.
- [ ] Run frontend gates: `cd frontend && npx tsc --noEmit && npm run lint && npm test` → all pass.
- [ ] Production build: `cd frontend && npm run build` → succeeds.
- [ ] Confirm the migration chain has a single head `0005_feedback`.
- [ ] Then use **superpowers:finishing-a-development-branch** to open the PR to `main`.

---

## Self-Review notes (plan author)

- **Spec coverage:** nostr_service (Tasks 3–6), config (Task 2), Feedback model+migration (Task 7), POST /api/v1/feedback with BackgroundTasks (Task 8), Settings card (Task 9), docs (Task 10), tests at every layer (round-trip ✓, bech32 vector ✓, no-op ✓, persist/auth/422 ✓, frontend render+submit ✓). Dependency pinning (Task 1) covers the spec's reliance on cryptography/websockets.
- **Crypto correctness:** ECDH uses point-multiply (NOT coincurve `ecdh`, which hashes and rejects `hashfn`). Verified both parties derive the same X; AES round-trips; schnorr sig verifies. NIP-01 id serialization uses `separators=(",",":")` and `ensure_ascii=False`.
- **Type consistency:** helper names are stable across tasks — `bech32_decode`, `encrypt_nip04`/`decrypt_nip04`, `_shared_secret`, `build_dm_event`, `_publish_to_relays`, `send_dm`; schema `FeedbackIn`; component `FeedbackCard`. The feedback DM uses `current_user.pubkey` (raw hex), so only a bech32 decoder is needed (no encoder).
