# Lightning Prize Splitting (NWC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an organizer mark a winning team, enter a sats prize, connect a Nostr Wallet Connect (NWC) wallet, and have SquadSync split the pot evenly and pay each winner's Lightning address live.

**Architecture:** A bolt-on at the results stage. Backend does all Lightning work, reusing the existing `nostr_service` NIP-04 + relay plumbing: an LNURL-pay client resolves each winner's `lud16` to a bolt11 invoice, and an NWC (NIP-47) client pays it. A pure split function and persisted `Payout`/`PayoutItem` rows make it reproducible and verifiable. Frontend adds a Lightning-address field at registration (prefilled from the user's Nostr profile) and a payout modal on the results page.

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, `coincurve` (Schnorr), `httpx` (LNURL), `websockets` (NWC relay), Next.js 16 / React 19.

**Spec:** `docs/superpowers/specs/2026-06-17-lightning-prize-splitting-design.md`

---

## File Structure

**Backend — create:**
- `backend/app/models/payout.py` — `Payout`, `PayoutItem` ORM models.
- `backend/app/services/lnurl_service.py` — LNURL-pay resolve + invoice request.
- `backend/app/services/nwc_service.py` — NIP-47 URI parse, request build/encrypt, response decode, pay.
- `backend/app/services/payout_service.py` — `compute_split` + payout orchestration.
- `backend/app/schemas/payout.py` — request/response schemas.
- `backend/app/api/v1/payouts.py` — organizer endpoints.
- `backend/alembic/versions/0007_lightning_payout.py` — migration.
- Tests: `test_split.py`, `test_lnurl_service.py`, `test_nwc_service.py`, `test_payout_endpoint.py`.

**Backend — modify:**
- `backend/app/models/participant.py` — add `lightning_address` column.
- `backend/app/models/__init__.py` — register `Payout`, `PayoutItem`.
- `backend/app/schemas/participant.py` — add `lightning_address` to register + out schemas.
- `backend/app/main.py` — include payouts router.
- `backend/app/api/v1/public.py` — add payout summary to public results.

**Frontend — modify (concrete tasks at end):**
- Registration form — Lightning-address field, prefilled from Nostr `kind:0`.
- Results page — "Mark winner & pay out" modal with live status.
- Public results — "⚡ Prize paid" badge.

**Note on tests vs migrations:** the test suite builds tables from models via `Base.metadata.create_all` (`tests/conftest.py`), so tests do NOT exercise the Alembic migration. The migration (Task 3) is required for dev/prod only.

---

## Task 1: `lightning_address` on participants

**Files:**
- Modify: `backend/app/models/participant.py:34` (after the `npub` column)
- Modify: `backend/app/schemas/participant.py`
- Test: `backend/tests/test_registration.py` (add one test)

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_registration.py` (routes confirmed against `tests/test_find_my_team.py`: create event → PATCH status active → register at `/api/v1/events/{slug}/register`; the register endpoint returns `ParticipantOut`):

```python
def test_register_accepts_lightning_address(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "Payout Test", "team_count": 2}).json()  # team_count has ge=2
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    res = client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
        "name": "Ada", "email": "ada@example.com",
        "primary_strength": "technical", "experience_level": "advanced",
        "lightning_address": "ada@getalby.com",
    })
    assert res.status_code in (200, 201)
    assert res.json()["lightning_address"] == "ada@getalby.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_registration.py::test_register_accepts_lightning_address -v`
Expected: FAIL — `lightning_address` rejected/ignored (422 or missing key).

- [ ] **Step 3: Add the column and schema fields**

In `backend/app/models/participant.py`, after the `npub` column (line 34):

```python
    lightning_address = Column(String, nullable=True)
```

In `backend/app/schemas/participant.py`, add to `ParticipantRegister` (after `npub`):

```python
    lightning_address: Optional[str] = Field(default=None, max_length=255)

    @field_validator("lightning_address", mode="before")
    @classmethod
    def _normalize_lightning_address(cls, v):
        if v is None:
            return None
        v = str(v).strip().lower()
        if not v:
            return None
        if v.count("@") != 1 or not all(v.split("@")):
            raise ValueError("Lightning address must look like name@domain")
        return v
```

And add to `ParticipantOut`:

```python
    lightning_address: Optional[str]
```

(The registration service uses `**req.model_dump()`, so no service change is needed.)

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_registration.py -v`
Expected: PASS (all registration tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/participant.py backend/app/schemas/participant.py backend/tests/test_registration.py
git commit -m "feat(payout): capture optional lightning_address at registration"
```

---

## Task 2: `Payout` and `PayoutItem` models

**Files:**
- Create: `backend/app/models/payout.py`
- Modify: `backend/app/models/__init__.py`
- Test: `backend/tests/test_payout_endpoint.py` (model smoke test for now)

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_payout_endpoint.py`:

```python
def test_payout_models_importable_and_persist(db):
    import uuid
    from app.models.payout import Payout, PayoutItem

    payout = Payout(event_id=uuid.uuid4(), allocation_id=uuid.uuid4(),
                    team_label="Team Satoshi", total_sats=210, status="pending")
    db.add(payout)
    db.flush()
    item = PayoutItem(payout_id=payout.id, participant_id=uuid.uuid4(),
                      lightning_address="ada@getalby.com", amount_sats=105, status="pending")
    db.add(item)
    db.commit()
    assert payout.id is not None and item.payout_id == payout.id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py::test_payout_models_importable_and_persist -v`
Expected: FAIL — `ModuleNotFoundError: app.models.payout`.

- [ ] **Step 3: Create the models**

Create `backend/app/models/payout.py`:

```python
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Uuid
from sqlalchemy.sql import func

from app.core.database import Base


class Payout(Base):
    __tablename__ = "payouts"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(Uuid(as_uuid=True), ForeignKey("events.id"), nullable=False, index=True)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    team_label = Column(String, nullable=False)
    total_sats = Column(Integer, nullable=False)
    # pending | partial | complete | failed
    status = Column(String, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PayoutItem(Base):
    __tablename__ = "payout_items"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payout_id = Column(Uuid(as_uuid=True), ForeignKey("payouts.id"), nullable=False, index=True)
    participant_id = Column(Uuid(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    lightning_address = Column(String, nullable=True)
    amount_sats = Column(Integer, nullable=False)
    # pending | paid | failed
    status = Column(String, nullable=False, default="pending")
    bolt11 = Column(String, nullable=True)
    preimage = Column(String, nullable=True)
    error = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

In `backend/app/models/__init__.py`, add the import and `__all__` entries:

```python
from app.models.payout import Payout, PayoutItem
```

```python
    "UsedAuthEvent", "Feedback", "TeamNotification", "Payout", "PayoutItem",
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py::test_payout_models_importable_and_persist -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/payout.py backend/app/models/__init__.py backend/tests/test_payout_endpoint.py
git commit -m "feat(payout): add Payout and PayoutItem models"
```

---

## Task 3: Alembic migration `0007_lightning_payout`

**Files:**
- Create: `backend/alembic/versions/0007_lightning_payout.py`

(No unit test — tests build tables from models. Verify by running the migration against a scratch SQLite DB.)

- [ ] **Step 1: Write the migration**

Create `backend/alembic/versions/0007_lightning_payout.py`:

```python
"""lightning payout

Revision ID: 0007_lightning_payout
Revises: 0006_npub_and_team_notifications
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_lightning_payout"
down_revision: Union[str, None] = "0006_npub_and_team_notifications"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.add_column(sa.Column("lightning_address", sa.String(), nullable=True))

    op.create_table(
        "payouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("team_label", sa.String(), nullable=False),
        sa.Column("total_sats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payouts_event_id", "payouts", ["event_id"])
    op.create_index("ix_payouts_allocation_id", "payouts", ["allocation_id"])

    op.create_table(
        "payout_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payout_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("lightning_address", sa.String(), nullable=True),
        sa.Column("amount_sats", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("bolt11", sa.String(), nullable=True),
        sa.Column("preimage", sa.String(), nullable=True),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["payout_id"], ["payouts.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payout_items_payout_id", "payout_items", ["payout_id"])


def downgrade() -> None:
    op.drop_index("ix_payout_items_payout_id", table_name="payout_items")
    op.drop_table("payout_items")
    op.drop_index("ix_payouts_allocation_id", table_name="payouts")
    op.drop_index("ix_payouts_event_id", table_name="payouts")
    op.drop_table("payouts")
    with op.batch_alter_table("participants") as b:
        b.drop_column("lightning_address")
```

- [ ] **Step 2: Verify the migration applies on a scratch DB**

Run:
```bash
cd backend && DATABASE_URL="sqlite:///./scratch_migration.db" SECRET_KEY=x python -m alembic upgrade head && rm -f scratch_migration.db
```
Expected: ends at `0007_lightning_payout` with no error.

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/0007_lightning_payout.py
git commit -m "feat(payout): migration for lightning_address + payout tables"
```

---

## Task 4: `compute_split` (pure split math)

**Files:**
- Create: `backend/app/services/payout_service.py` (split function only in this task)
- Test: `backend/tests/test_split.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_split.py`:

```python
import pytest
from app.services.payout_service import compute_split


def test_even_split_no_remainder():
    # 300 sats over 3 members -> 100 each, order preserved
    assert compute_split(["a", "b", "c"], 300) == [("a", 100), ("b", 100), ("c", 100)]


def test_remainder_goes_to_earliest_members():
    # 100 sats over 3 -> 34, 33, 33 (remainder 1 to the first member)
    assert compute_split(["a", "b", "c"], 100) == [("a", 34), ("b", 33), ("c", 33)]


def test_single_member_gets_everything():
    assert compute_split(["a"], 210) == [("a", 210)]


def test_zero_members_raises():
    with pytest.raises(ValueError):
        compute_split([], 100)


def test_total_below_member_count_raises():
    # cannot give every member at least 1 sat
    with pytest.raises(ValueError):
        compute_split(["a", "b", "c"], 2)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_split.py -v`
Expected: FAIL — `ModuleNotFoundError` / `compute_split` undefined.

- [ ] **Step 3: Implement `compute_split`**

Create `backend/app/services/payout_service.py`:

```python
"""Lightning payout: deterministic split + orchestration.

`compute_split` is pure and reproducible: an integer even split with the
remainder assigned to the earliest members (by the order they are passed in).
The orchestration functions are added in a later task.
"""
from typing import Sequence, TypeVar

T = TypeVar("T")


def compute_split(recipients: Sequence[T], total_sats: int) -> list[tuple[T, int]]:
    """Split `total_sats` evenly across `recipients`, remainder to the first members.

    Raises ValueError if there are no recipients or fewer sats than recipients
    (every member must receive at least 1 sat).
    """
    n = len(recipients)
    if n == 0:
        raise ValueError("no recipients")
    if total_sats < n:
        raise ValueError("total_sats must be at least one sat per recipient")
    base, remainder = divmod(total_sats, n)
    return [(r, base + (1 if i < remainder else 0)) for i, r in enumerate(recipients)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_split.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/payout_service.py backend/tests/test_split.py
git commit -m "feat(payout): deterministic even-split with remainder rule"
```

---

## Task 5: LNURL-pay client

**Files:**
- Create: `backend/app/services/lnurl_service.py`
- Test: `backend/tests/test_lnurl_service.py`

> Confirm `httpx` is installed (`cd backend && python -c "import httpx"`). It ships with Starlette's TestClient, so it should be present. If not, add `httpx` to `backend/requirements.txt` and `pip install httpx`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_lnurl_service.py`:

```python
import pytest
from app.services import lnurl_service
from app.services.lnurl_service import LnurlError, lud16_to_url


def test_lud16_to_url():
    assert lud16_to_url("ada@getalby.com") == "https://getalby.com/.well-known/lnurlp/ada"


def test_lud16_to_url_rejects_malformed():
    with pytest.raises(LnurlError):
        lud16_to_url("not-an-address")


def test_request_invoice_amount_below_min_raises(monkeypatch):
    params = {"callback": "https://getalby.com/lnurlp/ada/callback",
              "minSendable": 100_000, "maxSendable": 1_000_000}  # 100..1000 sat

    def fake_get(url, **kwargs):
        raise AssertionError("callback should not be hit when amount is out of bounds")

    monkeypatch.setattr(lnurl_service.httpx, "get", fake_get)
    with pytest.raises(LnurlError):
        lnurl_service.request_invoice(params, amount_sats=50)  # 50 sat < 100 sat min


def test_request_invoice_returns_bolt11(monkeypatch):
    params = {"callback": "https://getalby.com/lnurlp/ada/callback",
              "minSendable": 1_000, "maxSendable": 1_000_000}

    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"pr": "lnbc100n1fakeinvoice"}

    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["url"] = url
        captured["params"] = params
        return FakeResp()

    monkeypatch.setattr(lnurl_service.httpx, "get", fake_get)
    bolt11 = lnurl_service.request_invoice(params, amount_sats=100)
    assert bolt11 == "lnbc100n1fakeinvoice"
    assert captured["params"]["amount"] == 100_000  # msat
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_lnurl_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.lnurl_service`.

- [ ] **Step 3: Implement the LNURL client**

Create `backend/app/services/lnurl_service.py`:

```python
"""LNURL-pay client: resolve a `name@domain` Lightning address to a bolt11 invoice.

Two steps per LNURL spec (LUD-06/LUD-16):
  1. GET https://{domain}/.well-known/lnurlp/{name}  -> {callback, minSendable, maxSendable, ...}
  2. GET {callback}?amount={msat}                    -> {pr: <bolt11>}

All errors raise LnurlError; the caller marks that payout item failed and continues.
"""
import httpx

_TIMEOUT = 10.0


class LnurlError(Exception):
    """Any failure resolving an address or fetching an invoice."""


def lud16_to_url(address: str) -> str:
    address = address.strip().lower()
    if address.count("@") != 1:
        raise LnurlError(f"malformed lightning address: {address!r}")
    name, domain = address.split("@")
    if not name or not domain:
        raise LnurlError(f"malformed lightning address: {address!r}")
    return f"https://{domain}/.well-known/lnurlp/{name}"


def resolve_lnurl(address: str) -> dict:
    """Return the LNURL-pay params dict for a `name@domain` address."""
    url = lud16_to_url(address)
    try:
        resp = httpx.get(url, timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 — normalize to LnurlError
        raise LnurlError(f"failed to resolve {address}: {exc}") from exc
    if "callback" not in data or "minSendable" not in data or "maxSendable" not in data:
        raise LnurlError(f"invalid LNURL-pay response for {address}")
    return data


def request_invoice(params: dict, amount_sats: int) -> str:
    """Request a bolt11 invoice for `amount_sats` from a resolved LNURL params dict."""
    amount_msat = amount_sats * 1000
    if amount_msat < params["minSendable"] or amount_msat > params["maxSendable"]:
        raise LnurlError(
            f"amount {amount_sats} sat outside payable range "
            f"[{params['minSendable'] // 1000}, {params['maxSendable'] // 1000}] sat"
        )
    try:
        resp = httpx.get(params["callback"], params={"amount": amount_msat},
                         timeout=_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise LnurlError(f"invoice request failed: {exc}") from exc
    pr = data.get("pr")
    if not pr:
        raise LnurlError("LNURL callback returned no invoice")
    return pr
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_lnurl_service.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/lnurl_service.py backend/tests/test_lnurl_service.py
git commit -m "feat(payout): LNURL-pay client (resolve + invoice)"
```

---

## Task 6: NWC (NIP-47) client

**Files:**
- Create: `backend/app/services/nwc_service.py`
- Test: `backend/tests/test_nwc_service.py`

This task has three pure, unit-testable pieces (`parse_nwc_uri`, `build_pay_invoice_request`, `decode_response`) plus a thin relay round-trip (`pay_invoice`) that tests monkeypatch.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_nwc_service.py`:

```python
import json
import pytest
from coincurve import PrivateKey

from app.services import nwc_service
from app.services.nwc_service import NwcError, parse_nwc_uri, build_pay_invoice_request, decode_response
from app.services.nostr_service import encrypt_nip04


def _make_uri(secret_hex: str, wallet_pub_hex: str, relay="wss://relay.example") -> str:
    return f"nostr+walletconnect://{wallet_pub_hex}?relay={relay}&secret={secret_hex}"


def test_parse_nwc_uri():
    secret = PrivateKey()
    wallet = PrivateKey()
    wallet_xonly = wallet.public_key_xonly.format().hex()
    uri = _make_uri(secret.to_hex(), wallet_xonly)
    parsed = parse_nwc_uri(uri)
    assert parsed.wallet_pubkey_hex == wallet_xonly
    assert parsed.relay == "wss://relay.example"
    assert parsed.secret_bytes == secret.secret


def test_parse_nwc_uri_rejects_garbage():
    with pytest.raises(NwcError):
        parse_nwc_uri("https://not-nwc")


def test_build_pay_invoice_request_is_signed_and_encrypted():
    secret = PrivateKey()
    wallet = PrivateKey()
    wallet_xonly = wallet.public_key_xonly.format().hex()
    event = build_pay_invoice_request(secret.secret, bytes.fromhex(wallet_xonly), "lnbc1fake")
    assert event["kind"] == 23194
    assert ["p", wallet_xonly] in event["tags"]
    # wallet decrypts the request with its privkey + our x-only pubkey
    our_xonly = secret.public_key_xonly.format()
    from app.services.nostr_service import decrypt_nip04
    body = json.loads(decrypt_nip04(wallet.secret, our_xonly, event["content"]))
    assert body["method"] == "pay_invoice"
    assert body["params"]["invoice"] == "lnbc1fake"


def test_decode_response_success():
    secret = PrivateKey()
    wallet = PrivateKey()
    our_xonly = secret.public_key_xonly.format()
    payload = json.dumps({"result_type": "pay_invoice", "result": {"preimage": "deadbeef"}})
    content = encrypt_nip04(wallet.secret, our_xonly, payload)
    result = decode_response(secret.secret, wallet.public_key_xonly.format(), content)
    assert result == {"preimage": "deadbeef"}


def test_decode_response_error_raises():
    secret = PrivateKey()
    wallet = PrivateKey()
    our_xonly = secret.public_key_xonly.format()
    payload = json.dumps({"error": {"code": "INSUFFICIENT_BALANCE", "message": "no funds"}})
    content = encrypt_nip04(wallet.secret, our_xonly, payload)
    with pytest.raises(NwcError) as exc:
        decode_response(secret.secret, wallet.public_key_xonly.format(), content)
    assert "no funds" in str(exc.value)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_nwc_service.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services.nwc_service`.

- [ ] **Step 3: Implement the NWC client**

Create `backend/app/services/nwc_service.py`:

```python
"""Nostr Wallet Connect (NIP-47) client — pay_invoice only.

Reuses nostr_service's NIP-04 encryption. The NWC URI carries the client's
secret key and the wallet service pubkey + relay:
    nostr+walletconnect://<wallet_pubkey_hex>?relay=<wss>&secret=<hex_privkey>

Flow over one short-lived websocket: subscribe (REQ) for the wallet's kind-23195
response tagged with our request id, publish the kind-23194 request, read frames
until the response arrives or we time out, decrypt it, return the preimage.

The NWC secret is a spend credential: it is used transiently and never persisted.
"""
import hashlib
import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from coincurve import PrivateKey

from app.services.nostr_service import encrypt_nip04, decrypt_nip04

logger = logging.getLogger(__name__)

_REQUEST_KIND = 23194
_RESPONSE_KIND = 23195
_TIMEOUT = 30.0


class NwcError(Exception):
    """Any NWC failure: bad URI, wallet error response, or relay timeout."""


@dataclass
class NwcConnection:
    wallet_pubkey_hex: str   # x-only hex
    relay: str
    secret_bytes: bytes


def parse_nwc_uri(uri: str) -> NwcConnection:
    uri = uri.strip()
    if not uri.startswith("nostr+walletconnect://"):
        raise NwcError("not a nostr+walletconnect URI")
    parsed = urlparse(uri)
    wallet_pubkey = parsed.netloc or parsed.path.lstrip("/")
    qs = parse_qs(parsed.query)
    relay = (qs.get("relay") or [None])[0]
    secret_hex = (qs.get("secret") or [None])[0]
    if not wallet_pubkey or not relay or not secret_hex:
        raise NwcError("NWC URI missing wallet pubkey, relay, or secret")
    try:
        secret_bytes = bytes.fromhex(secret_hex)
    except ValueError as exc:
        raise NwcError("NWC secret is not valid hex") from exc
    return NwcConnection(wallet_pubkey_hex=wallet_pubkey.lower(), relay=relay, secret_bytes=secret_bytes)


def build_pay_invoice_request(secret_bytes: bytes, wallet_xonly: bytes, bolt11: str) -> dict:
    """Build a signed, NIP-04-encrypted kind-23194 pay_invoice request event."""
    privkey = PrivateKey(secret_bytes)
    pubkey_hex = privkey.public_key_xonly.format().hex()
    created_at = int(time.time())
    body = json.dumps({"method": "pay_invoice", "params": {"invoice": bolt11}},
                      separators=(",", ":"))
    content = encrypt_nip04(secret_bytes, wallet_xonly, body)
    tags = [["p", wallet_xonly.hex()]]
    serialized = json.dumps(
        [0, pubkey_hex, created_at, _REQUEST_KIND, tags, content],
        separators=(",", ":"), ensure_ascii=False,
    )
    event_id = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    sig = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()
    return {"id": event_id, "pubkey": pubkey_hex, "created_at": created_at,
            "kind": _REQUEST_KIND, "tags": tags, "content": content, "sig": sig}


def decode_response(secret_bytes: bytes, wallet_xonly: bytes, content: str) -> dict:
    """Decrypt a kind-23195 response. Return {'preimage': ...} or raise NwcError."""
    plaintext = decrypt_nip04(secret_bytes, wallet_xonly, content)
    data = json.loads(plaintext)
    if data.get("error"):
        raise NwcError(data["error"].get("message", "wallet returned an error"))
    result = data.get("result") or {}
    preimage = result.get("preimage")
    if not preimage:
        raise NwcError("wallet response had no preimage")
    return {"preimage": preimage}


def _round_trip(conn: NwcConnection, request_event: dict) -> str:
    """Publish the request and read the wallet's response content. Monkeypatched in tests.

    Subscribe BEFORE publishing so we cannot miss a fast response. Returns the
    raw (still-encrypted) response event content; raises NwcError on timeout.
    """
    from websockets.sync.client import connect

    sub_id = request_event["id"][:16]
    req = json.dumps(["REQ", sub_id, {
        "kinds": [_RESPONSE_KIND],
        "authors": [conn.wallet_pubkey_hex],
        "#e": [request_event["id"]],
    }])
    event_msg = json.dumps(["EVENT", request_event])
    deadline = time.time() + _TIMEOUT
    try:
        with connect(conn.relay, open_timeout=10, close_timeout=5) as ws:
            ws.send(req)
            ws.send(event_msg)
            while time.time() < deadline:
                frame = json.loads(ws.recv(timeout=max(1.0, deadline - time.time())))
                if frame[0] == "EVENT" and frame[1] == sub_id:
                    return frame[2]["content"]
    except NwcError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise NwcError(f"NWC relay round-trip failed: {exc}") from exc
    raise NwcError("timed out waiting for wallet response")


def pay_invoice(uri: str, bolt11: str) -> str:
    """Pay `bolt11` via the wallet in `uri`. Return the payment preimage or raise NwcError."""
    conn = parse_nwc_uri(uri)
    wallet_xonly = bytes.fromhex(conn.wallet_pubkey_hex)
    request_event = build_pay_invoice_request(conn.secret_bytes, wallet_xonly, bolt11)
    content = _round_trip(conn, request_event)
    return decode_response(conn.secret_bytes, wallet_xonly, content)["preimage"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_nwc_service.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nwc_service.py backend/tests/test_nwc_service.py
git commit -m "feat(payout): NWC (NIP-47) pay_invoice client"
```

---

## Task 7: Payout orchestration + schemas + endpoint

**Files:**
- Modify: `backend/app/services/payout_service.py` (add orchestration)
- Create: `backend/app/schemas/payout.py`
- Create: `backend/app/api/v1/payouts.py`
- Modify: `backend/app/main.py:7,33` (import + include router)
- Test: `backend/tests/test_payout_endpoint.py` (add endpoint tests)

- [ ] **Step 1: Write the failing endpoint test**

Add to `backend/tests/test_payout_endpoint.py`. The helper uses routes confirmed in
`tests/test_find_my_team.py` and `app/api/v1/allocation.py`. IMPORTANT constraints learned from
Task 1: the event schema requires `team_count >= 2`, and the allocation engine assigns members
with a random seed — so we do NOT assume *which* participants land on a team. We register 4
participants with `team_count=2` (the engine balances to ~2 per team) and drive every assertion
off the **actual** members of `teams[0]` returned by the API. `all_have_addresses` toggles whether
registrations include a Lightning address.

```python
def _setup_team(client, auth_headers, all_have_addresses):
    """Register 4 participants, allocate into 2 teams, return the first team.

    Returns (event_id, allocation_id, team_id, members) where `members` is the
    list of member dicts (each has 'id' and 'name') on teams[0].
    """
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "BTC++ Payout", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    strengths = ["technical", "design", "planning", "coordination"]
    for i in range(4):
        body = {"name": f"P{i}", "email": f"p{i}@t.com",
                "primary_strength": strengths[i], "experience_level": "intermediate"}
        if all_have_addresses:
            body["lightning_address"] = f"p{i}@getalby.com"
        r = client.post(f"/api/v1/events/{e['registration_slug']}/register", json=body)
        assert r.status_code in (200, 201), r.text
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    teams = client.get(f"/api/v1/allocations/{a['id']}/teams", headers=auth_headers).json()
    assert teams and teams[0]["members"], "expected a non-empty first team"
    return e["id"], a["id"], teams[0]["id"], teams[0]["members"]


def _stub_lightning(monkeypatch):
    """Stub LNURL + NWC so no real network happens. Returns the list of paid bolt11s."""
    from app.services import lnurl_service, nwc_service
    monkeypatch.setattr(lnurl_service, "resolve_lnurl",
                        lambda addr: {"callback": "https://x/cb", "minSendable": 1000, "maxSendable": 10_000_000})
    monkeypatch.setattr(lnurl_service, "request_invoice", lambda params, amount_sats: f"lnbc{amount_sats}fake")
    paid = []
    monkeypatch.setattr(nwc_service, "pay_invoice",
                        lambda uri, bolt11: (paid.append(bolt11), "preimage_" + bolt11)[1])
    return paid


def test_payout_pays_team_and_records_results(client, auth_headers, monkeypatch):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    paid = _stub_lightning(monkeypatch)

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
    })

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "complete"
    assert len(body["items"]) == len(members)
    assert sum(i["amount_sats"] for i in body["items"]) == 210   # full pot paid, no sats lost
    assert all(i["status"] == "paid" and i["preimage"] for i in body["items"])
    assert len(paid) == len(members)


def test_payout_422_when_member_missing_address(client, auth_headers):
    # No participant has an address, so any team triggers the pre-flight 422.
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
    })
    assert res.status_code == 422
    assert "missing" in res.text.lower()


def test_payout_address_override_fills_missing(client, auth_headers, monkeypatch):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=False)
    _stub_lightning(monkeypatch)
    # Supply an address for every member of teams[0] via the override map.
    overrides = {m["id"]: f"{m['name']}@getalby.com" for m in members}

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
        "addresses": overrides,
    })
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "complete"
```

> `TeamOut.members` exposes member `id` and `name` (see `app/schemas/allocation.py` / `teams.py`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py -v`
Expected: FAIL — payouts route does not exist (404) / helpers undefined.

- [ ] **Step 3: Add orchestration to `payout_service.py`**

Append to `backend/app/services/payout_service.py`:

```python
import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.payout import Payout, PayoutItem
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.services import lnurl_service, nwc_service

logger = logging.getLogger(__name__)


def _team_members(db: Session, team_id: UUID) -> list[Participant]:
    """Members of a team, ordered by participant id for a reproducible split."""
    return (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team_id)
        .order_by(Participant.id)
        .all()
    )


def preflight(
    db: Session, team_id: UUID, total_sats: int, overrides: dict[str, str] | None = None,
) -> list[tuple[Participant, str, int]]:
    """Resolve each member's address + split.

    `overrides` maps `str(participant_id) -> lightning_address` and lets the organizer
    supply/correct addresses in the payout modal (the spec's editable `items`). The
    override wins over the registration value. Raise ValueError listing any member who
    still has no address. Returns (participant, address, amount_sats) tuples.
    """
    overrides = overrides or {}
    members = _team_members(db, team_id)
    resolved = [(m, overrides.get(str(m.id)) or m.lightning_address) for m in members]
    missing = [m.name for m, addr in resolved if not addr]
    if missing:
        raise ValueError(f"missing lightning address for: {', '.join(missing)}")
    # compute_split preserves order, so zip the amounts back onto (participant, address).
    amounts = compute_split([m for m, _ in resolved], total_sats)
    return [(m, addr, amount) for (m, addr), (_, amount) in zip(resolved, amounts)]


def execute_payout(
    db: Session, payout: Payout, splits: list[tuple[Participant, str, int]], nwc: str,
) -> Payout:
    """Pay each member, recording per-item status. Rolls payout.status up at the end."""
    paid = 0
    for participant, address, amount_sats in splits:
        item = PayoutItem(payout_id=payout.id, participant_id=participant.id,
                          lightning_address=address, amount_sats=amount_sats, status="pending")
        db.add(item)
        db.flush()
        try:
            params = lnurl_service.resolve_lnurl(address)
            bolt11 = lnurl_service.request_invoice(params, amount_sats)
            item.bolt11 = bolt11
            item.preimage = nwc_service.pay_invoice(nwc, bolt11)
            item.status = "paid"
            paid += 1
        except Exception as exc:  # noqa: BLE001 — record + continue
            item.status = "failed"
            item.error = str(exc)
            logger.warning("payout item %s failed: %s", item.id, exc)
    payout.status = "complete" if paid == len(splits) else ("partial" if paid else "failed")
    db.commit()
    db.refresh(payout)
    return payout


def retry_failed(db: Session, payout: Payout, nwc: str) -> Payout:
    """Retry only the failed items of an existing payout."""
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    for item in items:
        if item.status != "failed":
            continue
        participant = db.query(Participant).filter(Participant.id == item.participant_id).first()
        try:
            params = lnurl_service.resolve_lnurl(item.lightning_address)
            bolt11 = lnurl_service.request_invoice(params, item.amount_sats)
            item.bolt11 = bolt11
            item.preimage = nwc_service.pay_invoice(nwc, bolt11)
            item.status, item.error = "paid", None
        except Exception as exc:  # noqa: BLE001
            item.error = str(exc)
            logger.warning("payout retry item %s failed: %s", item.id, exc)
    paid = sum(1 for i in items if i.status == "paid")
    payout.status = "complete" if paid == len(items) else ("partial" if paid else "failed")
    db.commit()
    db.refresh(payout)
    return payout
```

- [ ] **Step 4: Create the schemas**

Create `backend/app/schemas/payout.py`:

```python
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class PayoutCreate(BaseModel):
    team_id: UUID
    total_sats: int = Field(gt=0)
    nwc: str = Field(min_length=1)
    # Optional per-member address overrides: {str(participant_id): "name@domain"}.
    # Lets the organizer fill/correct a missing address in the payout modal.
    addresses: Optional[dict[str, str]] = None


class PayoutRetry(BaseModel):
    nwc: str = Field(min_length=1)


class PayoutItemOut(BaseModel):
    id: UUID
    participant_id: UUID
    lightning_address: Optional[str]
    amount_sats: int
    status: str
    preimage: Optional[str]
    error: Optional[str]

    model_config = {"from_attributes": True}


class PayoutOut(BaseModel):
    id: UUID
    event_id: UUID
    allocation_id: UUID
    team_label: str
    total_sats: int
    status: str
    items: list[PayoutItemOut]

    model_config = {"from_attributes": True}
```

- [ ] **Step 5: Create the endpoint**

Create `backend/app/api/v1/payouts.py`:

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.allocation import Allocation
from app.models.payout import Payout, PayoutItem
from app.models.team import Team
from app.models.user import User
from app.schemas.payout import PayoutCreate, PayoutRetry, PayoutOut
from app.services.event_service import assert_allocation_organizer
from app.services import payout_service

router = APIRouter()


def _payout_out(db: Session, payout: Payout) -> PayoutOut:
    items = db.query(PayoutItem).filter(PayoutItem.payout_id == payout.id).all()
    return PayoutOut(
        id=payout.id, event_id=payout.event_id, allocation_id=payout.allocation_id,
        team_label=payout.team_label, total_sats=payout.total_sats, status=payout.status,
        items=items,
    )


@router.post("/{allocation_id}/payouts", response_model=PayoutOut,
             status_code=status.HTTP_201_CREATED)
def create_payout(
    allocation_id: UUID,
    req: PayoutCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation: Allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    team = db.query(Team).filter(Team.id == req.team_id, Team.allocation_id == allocation_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found in this allocation")

    # Pre-flight: split + verify every member has an address BEFORE spending anything.
    try:
        splits = payout_service.preflight(db, team.id, req.total_sats, req.addresses)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    payout = Payout(event_id=allocation.event_id, allocation_id=allocation_id,
                    team_label=team.name, total_sats=req.total_sats, status="pending")
    db.add(payout)
    db.flush()
    payout = payout_service.execute_payout(db, payout, splits, req.nwc)
    return _payout_out(db, payout)


@router.post("/payouts/{payout_id}/retry", response_model=PayoutOut)
def retry_payout(
    payout_id: UUID,
    req: PayoutRetry,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    payout = db.query(Payout).filter(Payout.id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")
    assert_allocation_organizer(db, payout.allocation_id, current_user.id)
    payout = payout_service.retry_failed(db, payout, req.nwc)
    return _payout_out(db, payout)
```

- [ ] **Step 6: Register the router**

In `backend/app/main.py`, line 7 import list, add `payouts`:

```python
from app.api.v1 import auth, events, participants, allocation, teams, export, public, feedback, payouts
```

After the `teams` router line (line 30), add:

```python
app.include_router(payouts.router, prefix="/api/v1/allocations", tags=["payouts"])
```

- [ ] **Step 7: Run the endpoint tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py -v`
Expected: PASS. If `assert_allocation_organizer`'s return value or signature differs, open `app/services/event_service.py` and adjust the call to match (it is the same helper `teams.py` uses).

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/payout_service.py backend/app/schemas/payout.py backend/app/api/v1/payouts.py backend/app/main.py backend/tests/test_payout_endpoint.py
git commit -m "feat(payout): payout orchestration + organizer endpoints"
```

---

## Task 8: Public results payout summary

**Files:**
- Modify: `backend/app/schemas/allocation.py` (add `PublicPayoutSummary` + a field on `PublicAllocationOut`)
- Modify: `backend/app/api/v1/public.py:29-53` (the `public_allocation` handler)
- Test: `backend/tests/test_payout_endpoint.py` (add a public-view test)

The public results route is `GET /api/v1/public/allocations/{allocation_id}` → `PublicAllocationOut`
(`app/api/v1/public.py:29`). It is **published-only**, so the test must publish first. Because the
route has a `response_model`, we must add a typed `payouts` field to `PublicAllocationOut` (a
`response_model` strips keys not on the model).

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_payout_endpoint.py` (`_setup_team` returns `event_id` so we can publish):

This test reuses `_setup_team` and `_stub_lightning` from Task 7 (same file).

```python
def test_public_results_include_payout_summary(client, auth_headers, monkeypatch):
    event_id, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    _stub_lightning(monkeypatch)
    client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
    })
    # Public results are published-only.
    client.post(f"/api/v1/events/{event_id}/allocations/{allocation_id}/publish", headers=auth_headers)

    res = client.get(f"/api/v1/public/allocations/{allocation_id}")
    assert res.status_code == 200, res.text
    summary = res.json()["payouts"]
    assert summary[0]["team_label"]
    assert summary[0]["total_sats"] == 210
    assert summary[0]["paid_count"] == len(members)
    assert summary[0]["member_count"] == len(members)
    # never leak the credential or invoice/preimage secrets
    for leaked in ("nwc", "preimage", "bolt11", "lightning_address"):
        assert leaked not in res.text.lower()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py::test_public_results_include_payout_summary -v`
Expected: FAIL — no `payouts` key.

- [ ] **Step 3: Add the schema field**

In `backend/app/schemas/allocation.py`, before `class PublicAllocationOut` (around line 76):

```python
class PublicPayoutSummary(BaseModel):
    team_label: str
    total_sats: int
    status: str
    paid_count: int
    member_count: int
```

And add to `PublicAllocationOut`:

```python
    payouts: list[PublicPayoutSummary] = []
```

- [ ] **Step 4: Populate it in the handler**

In `backend/app/api/v1/public.py`, add the import near the top:

```python
from app.models.payout import Payout, PayoutItem
from app.schemas.allocation import PublicPayoutSummary
```

In `public_allocation`, replace the final `return` (line 53) with:

```python
    payouts = []
    for p in db.query(Payout).filter(Payout.allocation_id == allocation.id).all():
        items = db.query(PayoutItem).filter(PayoutItem.payout_id == p.id).all()
        payouts.append(PublicPayoutSummary(
            team_label=p.team_label, total_sats=p.total_sats, status=p.status,
            paid_count=sum(1 for i in items if i.status == "paid"), member_count=len(items),
        ))
    return PublicAllocationOut(id=allocation.id, status=allocation.status, teams=teams, payouts=payouts)
```

The summary intentionally excludes `lightning_address`, `bolt11`, `preimage`, and any NWC data.

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_payout_endpoint.py -v`
Expected: PASS.

- [ ] **Step 6: Run the full backend suite (no regressions)**

Run: `cd backend && python -m pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/public.py backend/tests/test_payout_endpoint.py
git commit -m "feat(payout): redacted payout summary on public results"
```

---

## Task 9: Frontend — Lightning address at registration (prefilled from Nostr profile)

**Files:**
- Modify: the registration form component (find with: `grep -rl "primary_strength\|strength_other" frontend/`)
- Modify: the API/types module that defines the registration request body (find with: `grep -rln "npub" frontend/`)

- [ ] **Step 1: Add the field to the registration request type/body**

Wherever the registration payload type and POST body are built (the same place `npub` is sent), add an optional `lightning_address?: string` and include it in the POST body.

- [ ] **Step 2: Add the input to the form**

Add an optional text input labelled "Lightning address (optional)" with placeholder `you@walletofsatoshi.com`, bound to the same form state used for the other fields. Mirror the existing `npub` field's markup/validation styling exactly.

- [ ] **Step 3: Prefill from the logged-in Nostr profile**

If the registrant is logged in via Nostr (the app already has NIP-07 / nsec handling — find it with `grep -rln "nip07\|window.nostr\|getPublicKey" frontend/`), on form mount fetch their `kind:0` metadata from the app's configured relays, parse the JSON `content`, and if it has a `lud16` (or `lud06`), prefill the Lightning-address input (leave editable). If no profile or no `lud16`, leave the field blank. Reuse any existing relay/profile helper rather than adding a new Nostr client.

- [ ] **Step 4: Manual verification**

Run the frontend (`cd frontend && npm run dev`), open a registration page, confirm: (a) the field appears, (b) for a Nostr profile with a `lud16` it prefills, (c) submitting persists it (check the organizer participant view / DB).

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat(payout): lightning address field at registration, prefilled from Nostr profile"
```

---

## Task 10: Frontend — "Mark winner & pay out" modal on results

**Files:**
- Modify: the organizer results/teams page (find with: `grep -rln "fairness_score\|/teams" frontend/`)
- Modify: the frontend API client module (where authed POSTs to `/api/v1/...` are made)

- [ ] **Step 1: Add the API client calls**

Add `createPayout(allocationId, { team_id, total_sats, nwc })` → `POST /api/v1/allocations/{allocationId}/payouts`, and `retryPayout(payoutId, { nwc })` → `POST /api/v1/allocations/payouts/{payoutId}/retry`. Use the existing authed-fetch helper (NIP-98 header) the other organizer calls use.

- [ ] **Step 2: Add a "Mark winner & pay out" button per team**

On each team card (organizer view only), add the button. Clicking opens a modal.

- [ ] **Step 3: Build the modal**

Fields: total prize (sats, number input) and NWC connection string (password-style input, with helper text "Paste an NWC string from Alby, Coinos, or Alby Hub"). Show the computed even split client-side (`floor(total/n)` with the first `total mod n` members +1) next to each member name, and flag any member with no Lightning address (block submit, with a note to add it at registration). A "Send payout" button calls `createPayout`.

- [ ] **Step 4: Render live per-member status**

On the response, list each item: ✅ green with a shortened preimage (`preimage.slice(0,12)…`) when `status === "paid"`, ❌ red with `error` when `failed`. If any failed, show a "Retry failed" button that calls `retryPayout` and re-renders. Never store or log the NWC string beyond the in-memory modal state; clear it when the modal closes.

- [ ] **Step 5: Manual verification**

With a funded NWC wallet and two participants whose Lightning addresses you control, run a real payout of a small amount and confirm both members receive sats and the UI shows preimages.

- [ ] **Step 6: Commit**

```bash
git add frontend/
git commit -m "feat(payout): organizer payout modal with live NWC payment status"
```

---

## Task 11: Frontend — "⚡ Prize paid" badge on public results

**Files:**
- Modify: the public results page (find with: `grep -rln "results" frontend/app frontend/src 2>/dev/null`)

- [ ] **Step 1: Render the payout summary**

The public results response now includes `payouts: [{ team_label, total_sats, status, paid_count, member_count }]`. When present and non-empty, render a small "⚡ Prize paid" badge near the winning team plus a one-line summary (e.g. "210 sats → 2/2 paid"). Show nothing when the array is empty.

- [ ] **Step 2: Manual verification**

Open `/results/<id>` after a payout and confirm the badge shows; open one with no payout and confirm nothing renders.

- [ ] **Step 3: Commit**

```bash
git add frontend/
git commit -m "feat(payout): prize-paid badge on public results"
```

---

## Final verification

- [ ] Backend suite green: `cd backend && python -m pytest -q`
- [ ] Migration applies cleanly: `cd backend && DATABASE_URL="sqlite:///./scratch.db" SECRET_KEY=x python -m alembic upgrade head && rm -f scratch.db`
- [ ] End-to-end manual check: real NWC wallet, two real Lightning addresses, small payout, preimages shown, public badge appears.
- [ ] Confirm the NWC string never appears in DB, logs, or any API response (`grep -rin "nwc" backend/app` shows only transient request handling).
```
