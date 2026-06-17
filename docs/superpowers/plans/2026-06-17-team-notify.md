# npub at Registration + Team-Notify on Publish (B2b) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture an optional Nostr `npub` at registration and, on publish, best-effort DM each npub-having attendee their team — sent once per (allocation, participant), only recorded on success.

**Architecture:** A new `validate_npub` in the existing `nostr_service`; a nullable `participants.npub` column + a `team_notifications` dedup table (migration `0006`); the registration schema validates/normalizes npub; a new `team_notifications.notify_teams_task` runs in FastAPI `BackgroundTasks` (opens its own DB session) and is scheduled from `publish_allocation`. The registration form gains an optional npub field.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest; reuses B2a's `nostr_service` (`send_dm`, `bech32_decode`). Frontend: Next.js 16 / React 19 / react-hook-form + zod / Vitest.

**Spec:** `docs/superpowers/specs/2026-06-17-team-notify-design.md`
**Branch:** `feat/team-notify` (already cut from `main`, which now includes B2a). Commit messages must NOT include any Co-Authored-By line.

**Verified facts (do not re-derive):**
- `nostr_service.bech32_decode(s) -> (hrp, bytes)` exists (B2a) and raises `ValueError` on malformed input.
- `register_participant` builds the row via `Participant(..., **req.model_dump())`, so adding `npub` to the schema + a `npub` column means it flows through with **no service change**.
- Migration head is currently `0005_feedback`; next is `0006`.
- The app's real session factory is `app.core.database.SessionLocal` (bound to `DATABASE_URL`). In tests, conftest uses a *different* engine/`TestingSessionLocal` bound to `sqlite:///./test_squadsync.db` and overrides `get_db`. Therefore the background-task test MUST monkeypatch `app.services.team_notifications.SessionLocal` to the test factory (added as a conftest `session_factory` fixture in Task 4).
- NIP-19 test vectors: npub `npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6`; nsec `nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9`.
- Backend tests run from `backend/`: `python -m pytest -q` (the `pytest` console script is not on PATH; use `python -m pytest`).
- Frontend register POST sends the whole form object as `body` via `fetchAPI` (see `registration-form.tsx`).

---

## File Structure

**Backend (create):**
- `backend/app/models/team_notification.py` — `TeamNotification` dedup model.
- `backend/alembic/versions/0006_npub_and_team_notifications.py` — column + table.
- `backend/app/services/team_notifications.py` — `notify_teams_task` fan-out.
- `backend/tests/test_team_notify.py` — fan-out tests.

**Backend (modify):**
- `backend/app/services/nostr_service.py` — add `validate_npub`.
- `backend/app/models/participant.py` — add `npub` column.
- `backend/app/models/__init__.py` — register `TeamNotification`.
- `backend/app/schemas/participant.py` — `npub` field + validator on `ParticipantRegister`; `npub` on `ParticipantOut`.
- `backend/app/api/v1/allocation.py` — `publish_allocation` schedules `notify_teams_task`.
- `backend/tests/conftest.py` — add a `session_factory` fixture.
- `backend/tests/test_nostr_service.py` — `validate_npub` tests.
- `backend/tests/test_registration.py` (create if absent) — npub registration tests.

**Frontend (modify):**
- `frontend/components/registration/registration-form.tsx` — optional npub field.
- `frontend/tests/components/registration-form.test.tsx` — npub render + submit test.

---

## Task 1: `validate_npub` helper

**Files:**
- Modify: `backend/app/services/nostr_service.py`
- Test: `backend/tests/test_nostr_service.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_nostr_service.py`:

```python
import pytest


def test_validate_npub_accepts_valid():
    npub = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"
    assert nostr_service.validate_npub(npub) == npub


def test_validate_npub_rejects_nsec():
    with pytest.raises(ValueError):
        nostr_service.validate_npub("nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9")


def test_validate_npub_rejects_garbage():
    with pytest.raises(ValueError):
        nostr_service.validate_npub("not-an-npub")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_nostr_service.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'validate_npub'`.

- [ ] **Step 3: Implement `validate_npub`**

Append to `backend/app/services/nostr_service.py`:

```python
def validate_npub(npub: str) -> str:
    """Return `npub` unchanged if it is a well-formed bech32 npub, else raise ValueError.

    A valid npub has hrp `npub` and decodes to a 32-byte key. `bech32_decode` already
    raises ValueError on malformed input (bad chars / no separator).
    """
    hrp, key = bech32_decode(npub)
    if hrp != "npub" or len(key) != 32:
        raise ValueError("invalid npub")
    return npub
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd backend && python -m pytest tests/test_nostr_service.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/nostr_service.py backend/tests/test_nostr_service.py
git commit -m "feat(backend): add validate_npub helper"
```

---

## Task 2: `npub` column + `TeamNotification` model + migration `0006`

**Files:**
- Modify: `backend/app/models/participant.py`
- Create: `backend/app/models/team_notification.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/0006_npub_and_team_notifications.py`

- [ ] **Step 1: Add the `npub` column to Participant**

In `backend/app/models/participant.py`, add this line after `strength_source` (line 33) and before `tech_stack`:

```python
    npub = Column(String, nullable=True)
```

- [ ] **Step 2: Create the `TeamNotification` model**

Create `backend/app/models/team_notification.py`:

```python
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, Uuid, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class TeamNotification(Base):
    """One row per successfully-sent team DM, deduped on (allocation_id, participant_id)."""
    __tablename__ = "team_notifications"
    __table_args__ = (
        UniqueConstraint("allocation_id", "participant_id", name="uq_team_notification"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    participant_id = Column(Uuid(as_uuid=True), ForeignKey("participants.id"), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
```

- [ ] **Step 3: Register the model**

In `backend/app/models/__init__.py`, add the import after the `feedback` import and add `TeamNotification` to `__all__`:

```python
from app.models.user import User
from app.models.event import Event, EventCoOrganizer
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember
from app.models.used_event import UsedAuthEvent
from app.models.feedback import Feedback
from app.models.team_notification import TeamNotification

__all__ = [
    "User", "Event", "EventCoOrganizer", "Participant",
    "AllocationConfig", "Allocation", "Team", "TeamMember",
    "UsedAuthEvent", "Feedback", "TeamNotification",
]
```

- [ ] **Step 4: Create the migration**

Create `backend/alembic/versions/0006_npub_and_team_notifications.py`:

```python
"""npub and team_notifications

Revision ID: 0006_npub_and_team_notifications
Revises: 0005_feedback
Create Date: 2026-06-17
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_npub_and_team_notifications"
down_revision: Union[str, None] = "0005_feedback"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.add_column(sa.Column("npub", sa.String(), nullable=True))

    op.create_table(
        "team_notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("allocation_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["allocation_id"], ["allocations.id"]),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("allocation_id", "participant_id", name="uq_team_notification"),
    )
    op.create_index("ix_team_notifications_allocation_id", "team_notifications", ["allocation_id"])
    op.create_index("ix_team_notifications_created_at", "team_notifications", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_team_notifications_created_at", table_name="team_notifications")
    op.drop_index("ix_team_notifications_allocation_id", table_name="team_notifications")
    op.drop_table("team_notifications")
    with op.batch_alter_table("participants") as b:
        b.drop_column("npub")
```

- [ ] **Step 5: Verify models import and the migration chain is linear**

Run: `cd backend && python -c "import app.models; print(app.models.TeamNotification.__tablename__)"`
Expected: prints `team_notifications`.

Run: `cd backend && python -c "from alembic.config import Config; from alembic.script import ScriptDirectory; s=ScriptDirectory.from_config(Config('alembic.ini')); print(s.get_current_head())"`
Expected: prints `0006_npub_and_team_notifications` (single head).

Run the full suite (tables are built from models, so this proves the schema is valid):
`cd backend && python -m pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/participant.py backend/app/models/team_notification.py backend/app/models/__init__.py backend/alembic/versions/0006_npub_and_team_notifications.py
git commit -m "feat(backend): add npub column + team_notifications table (0006)"
```

---

## Task 3: Registration accepts + validates npub

**Files:**
- Modify: `backend/app/schemas/participant.py`
- Test: `backend/tests/test_registration.py` (create)

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_registration.py`:

```python
NPUB = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"


def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Reg", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def _register(client, slug, **overrides):
    body = {
        "name": "Alice", "email": "alice@t.com",
        "primary_strength": "technical", "experience_level": "intermediate",
    }
    body.update(overrides)
    return client.post(f"/api/v1/events/{slug}/register", json=body)


def test_register_accepts_and_normalizes_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    # Uppercased + surrounding whitespace must be normalized to canonical lowercase.
    res = _register(client, e["registration_slug"], npub=f"  {NPUB.upper()}  ")
    assert res.status_code == 201
    assert res.json()["npub"] == NPUB


def test_register_rejects_malformed_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="bad@t.com", npub="not-an-npub")
    assert res.status_code == 422


def test_register_rejects_nsec_as_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="nsec@t.com",
                    npub="nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9")
    assert res.status_code == 422


def test_register_blank_npub_stored_none(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="blank@t.com", npub="   ")
    assert res.status_code == 201
    assert res.json()["npub"] is None


def test_register_omitted_npub_stored_none(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="omit@t.com")
    assert res.status_code == 201
    assert res.json()["npub"] is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_registration.py -q`
Expected: FAIL — npub not accepted / not present in response (e.g. normalization assert fails or `KeyError`).

- [ ] **Step 3: Add the npub field + validator to the schemas**

In `backend/app/schemas/participant.py`:

Change the imports line (line 3) to add `field_validator`:
```python
from pydantic import BaseModel, EmailStr, Field, model_validator, field_validator
```

Add this import near the top (after the existing imports):
```python
from app.services.nostr_service import validate_npub
```

Add the `npub` field to `ParticipantRegister` (after `experience_level`, before `tech_stack`):
```python
    npub: Optional[str] = None
```

Add this validator method inside `ParticipantRegister` (after the existing `_require_other_text` validator):
```python
    @field_validator("npub", mode="before")
    @classmethod
    def _normalize_npub(cls, v):
        if v is None:
            return None
        v = str(v).strip().lower()
        if not v:
            return None
        validate_npub(v)  # raises ValueError (→ 422) if malformed
        return v
```

Add `npub` to `ParticipantOut` (after `experience_level`, before `composite_score`):
```python
    npub: Optional[str]
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd backend && python -m pytest tests/test_registration.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite (no regressions)**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/participant.py backend/tests/test_registration.py
git commit -m "feat(backend): accept + validate optional npub at registration"
```

---

## Task 4: `notify_teams_task` fan-out

**Files:**
- Create: `backend/app/services/team_notifications.py`
- Modify: `backend/tests/conftest.py` (add `session_factory` fixture)
- Test: `backend/tests/test_team_notify.py`

- [ ] **Step 1: Add the `session_factory` fixture to conftest**

In `backend/tests/conftest.py`, add this fixture (anywhere among the other fixtures, e.g. after the `db` fixture):

```python
@pytest.fixture
def session_factory():
    """The test session factory — used to monkeypatch SessionLocal in background-task tests."""
    return TestingSessionLocal
```

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_team_notify.py`:

```python
from uuid import UUID

import app.services.team_notifications as tn

NPUB = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"


def _published_with_npubs(client, auth_headers):
    """Create an active event, register 2 npub + 2 non-npub attendees, allocate, publish.

    NOTE: publish runs with SQUADSYNC_NSEC unset here, so any scheduled background
    notify task no-ops (writes nothing) — leaving the allocation clean for the
    direct notify_teams_task calls in each test.
    """
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "Notify", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    regs = [
        ("A", "a@t.com", "technical", NPUB),
        ("B", "b@t.com", "design", NPUB),
        ("C", "c@t.com", "planning", None),
        ("D", "d@t.com", "coordination", None),
    ]
    for name, email, strength, npub in regs:
        body = {"name": name, "email": email, "primary_strength": strength,
                "experience_level": "intermediate"}
        if npub:
            body["npub"] = npub
        assert client.post(f"/api/v1/events/{e['registration_slug']}/register", json=body).status_code == 201
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    return e, a


def test_notify_dms_only_npub_members_once(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)

    calls = []
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: calls.append((npub, msg)) or True)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", "nsec1bot", raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    tn.notify_teams_task(UUID(a["id"]))
    assert len(calls) == 2  # only the two npub-having members
    assert all(npub == NPUB for npub, _ in calls)
    assert all("results/" in msg for _, msg in calls)

    # Dedup: a second run for the same allocation sends nothing.
    calls.clear()
    tn.notify_teams_task(UUID(a["id"]))
    assert calls == []


def test_notify_writes_no_row_on_send_failure(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", "nsec1bot", raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    # All sends fail → no dedup rows written.
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: False)
    tn.notify_teams_task(UUID(a["id"]))

    # A later re-run (now succeeding) retries both, proving nothing was suppressed.
    sent = []
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: sent.append(npub) or True)
    tn.notify_teams_task(UUID(a["id"]))
    assert len(sent) == 2


def test_notify_noop_when_nsec_unset(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)
    calls = []
    monkeypatch.setattr(tn, "send_dm", lambda *args, **kwargs: calls.append(1) or True)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", None, raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    tn.notify_teams_task(UUID(a["id"]))
    assert calls == []
```

- [ ] **Step 3: Run to verify they fail**

Run: `cd backend && python -m pytest tests/test_team_notify.py -q`
Expected: FAIL — `ModuleNotFoundError: app.services.team_notifications`.

- [ ] **Step 4: Implement the fan-out**

Create `backend/app/services/team_notifications.py`:

```python
"""Best-effort team-notify fan-out: DM each npub-having attendee their team on publish.

Designed to run inside a FastAPI BackgroundTask (after the HTTP response is sent), so it
opens its OWN DB session. No-ops when SQUADSYNC_NSEC is unset (writes nothing, so enabling
the key later + re-publish still notifies). A dedup row is written ONLY on send success,
so a transient relay outage doesn't permanently suppress delivery — a later re-publish
retries. Per-participant failures are isolated and never abort the loop.
"""
import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.models.team_notification import TeamNotification
from app.services.nostr_service import send_dm

logger = logging.getLogger(__name__)


def _results_link(allocation_id: UUID) -> str:
    origins = settings.cors_origins
    base = origins[0] if origins else settings.FRONTEND_URL.rstrip("/")
    return f"{base}/results/{allocation_id}"


def notify_teams_task(allocation_id: UUID) -> None:
    if not settings.SQUADSYNC_NSEC:
        return
    with SessionLocal() as db:
        allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
        if not allocation or allocation.status != "published":
            return
        event = db.query(Event).filter(Event.id == allocation.event_id).first()
        event_title = event.title if event else "your event"
        link = _results_link(allocation_id)

        teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
        for team in teams:
            members = (
                db.query(Participant)
                .join(TeamMember, Participant.id == TeamMember.participant_id)
                .filter(TeamMember.team_id == team.id)
                .all()
            )
            for member in members:
                if not member.npub:
                    continue
                try:
                    already = (
                        db.query(TeamNotification)
                        .filter(
                            TeamNotification.allocation_id == allocation.id,
                            TeamNotification.participant_id == member.id,
                        )
                        .first()
                    )
                    if already:
                        continue
                    message = (
                        f"You're on {team.name} for {event_title}!\n\n"
                        f"See your team and teammates: {link}"
                    )
                    if not send_dm(member.npub, message):
                        logger.warning(
                            "Team DM not delivered for participant %s (allocation %s); will retry on re-publish",
                            member.id, allocation.id,
                        )
                        continue
                    db.add(TeamNotification(
                        allocation_id=allocation.id,
                        participant_id=member.id,
                        sent_at=datetime.now(timezone.utc),
                    ))
                    db.commit()
                except IntegrityError:
                    db.rollback()  # another writer already recorded this (allocation, participant)
                except Exception as exc:  # noqa: BLE001 — isolate per-participant failures
                    db.rollback()
                    logger.warning("Team notify failed for participant %s: %s", member.id, exc)
```

- [ ] **Step 5: Run to verify they pass**

Run: `cd backend && python -m pytest tests/test_team_notify.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/team_notifications.py backend/tests/conftest.py backend/tests/test_team_notify.py
git commit -m "feat(backend): add notify_teams_task team-notify fan-out"
```

---

## Task 5: Publish schedules the notify task

**Files:**
- Modify: `backend/app/api/v1/allocation.py`
- Test: `backend/tests/test_team_notify.py` (append)

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_team_notify.py`:

```python
import app.api.v1.allocation as alloc_mod


def test_publish_schedules_notify_task(client, auth_headers, monkeypatch):
    scheduled = []
    monkeypatch.setattr(alloc_mod, "notify_teams_task", lambda aid: scheduled.append(aid))

    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "Sched", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"s{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()

    res = client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    assert res.status_code == 200
    # TestClient runs BackgroundTasks after the response; the scheduled task ran.
    assert len(scheduled) == 1
    assert str(scheduled[0]) == a["id"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_team_notify.py::test_publish_schedules_notify_task -q`
Expected: FAIL — `AttributeError: ... 'notify_teams_task'` (not imported in the allocation module).

- [ ] **Step 3: Wire the publish endpoint**

In `backend/app/api/v1/allocation.py`:

Change the FastAPI import (line 4) to add `BackgroundTasks`:
```python
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
```

Add this import with the other service imports (near `from app.services.allocation_engine import run_allocation`):
```python
from app.services.team_notifications import notify_teams_task
```

Replace the `publish_allocation` signature and body so it accepts `background_tasks` and schedules the task after commit:
```python
@router.post("/{event_id}/allocations/{allocation_id}/publish")
def publish_allocation(
    event_id: UUID,
    allocation_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _assert_organizer(db, event_id, current_user.id)
    allocation = db.query(Allocation).filter(
        Allocation.id == allocation_id, Allocation.event_id == event_id
    ).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    allocation.status = "published"
    # Publishing announces teams, so close registration for the event.
    event = db.query(Event).filter(Event.id == event_id).first()
    if event and event.status != "archived":
        event.status = "allocated"
    db.commit()
    # Fire-and-forget: DM each npub-having attendee their team (no-op if Nostr unconfigured).
    background_tasks.add_task(notify_teams_task, allocation.id)
    return {"detail": "published"}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_team_notify.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/allocation.py backend/tests/test_team_notify.py
git commit -m "feat(backend): schedule team-notify DM fan-out on publish"
```

---

## Task 6: Registration form npub field (frontend)

**Files:**
- Modify: `frontend/components/registration/registration-form.tsx`
- Test: `frontend/tests/components/registration-form.test.tsx`

> Heed `frontend/AGENTS.md` (modified Next.js 16). This task only edits an existing client component using react-hook-form + zod — no Next routing/server APIs involved.

- [ ] **Step 1: Write the failing tests**

Append these two tests inside the `describe("RegistrationForm", ...)` block in `frontend/tests/components/registration-form.test.tsx`:

```tsx
  it("renders the optional npub field", () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    expect(screen.getByLabelText(/npub/i)).toBeInTheDocument();
  });

  it("includes npub in the submit body when provided", async () => {
    render(<RegistrationForm event={mockEvent} slug="abc123" />);
    fireEvent.change(screen.getByLabelText(/^name/i), { target: { value: "Alice" } });
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.change(screen.getByLabelText(/npub/i), { target: { value: "npub1abc" } });
    fireEvent.click(screen.getByRole("button", { name: /join event/i }));
    const { fetchAPI } = await import("@/lib/api");
    await waitFor(() => expect(fetchAPI).toHaveBeenCalledWith(
      "/api/v1/events/abc123/register",
      expect.objectContaining({ method: "POST", body: expect.objectContaining({ npub: "npub1abc" }) }),
    ));
  });
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd frontend && npm test -- registration-form`
Expected: FAIL — no element labeled `npub`.

- [ ] **Step 3: Add the npub field to the form**

In `frontend/components/registration/registration-form.tsx`:

Add `npub` to the zod schema (inside `z.object({...})`, after `experience_level`):
```tsx
  npub: z.string().optional(),
```

Add the input block in the form JSX, after the Phone field block (after line 94, the closing `</div>` of the phone field) and before the Primary Strength block:
```tsx
      <div className="space-y-1">
        <Label htmlFor="npub">Nostr npub (optional)</Label>
        <Input id="npub" placeholder="npub1…" {...register("npub")} />
        <p className="text-xs text-muted-foreground">
          Paste your Nostr npub to be DM&apos;d your team. Otherwise you can look it up after results are posted.
        </p>
      </div>
```

- [ ] **Step 4: Run to verify they pass**

Run: `cd frontend && npm test -- registration-form`
Expected: PASS.

- [ ] **Step 5: Typecheck, lint, full test, build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: tsc clean; lint clean (the pre-existing `react-hooks/incompatible-library` warning in this file is unrelated and may remain — 0 errors); all tests pass.

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/registration/registration-form.tsx frontend/tests/components/registration-form.test.tsx
git commit -m "feat(frontend): add optional npub field to registration form"
```

---

## Final verification (after all tasks)

- [ ] `cd backend && python -m pytest -q` → all pass.
- [ ] `cd frontend && npx tsc --noEmit && npm run lint && npm test` → all pass (0 lint errors).
- [ ] `cd frontend && npm run build` → succeeds.
- [ ] Migration chain head = `0006_npub_and_team_notifications` (single head).
- [ ] Then use **superpowers:finishing-a-development-branch** to open the PR to `main`.

---

## Self-Review notes (plan author)

- **Spec coverage:** `validate_npub` (T1); npub column + `team_notifications` table + `0006` (T2); npub capture/validate/normalize + organizer-only `ParticipantOut` exposure (T3); fan-out with no-op guard, success-only dedup row, per-participant isolation, own session (T4); publish wiring via BackgroundTasks (T5); frontend optional field (T6). All 4 adjustments are implemented: success-only row (T4 `if not send_dm(...): continue`), `created_at` indexed (T2), `.strip().lower()` normalization (T3), link stays `/results/{id}` (T4, anchor deferred).
- **Privacy:** `npub` added only to `ParticipantRegister`/`ParticipantOut` (organizer-auth) — no public schema touched.
- **Type consistency:** `validate_npub(str)->str`, `notify_teams_task(UUID)->None`, `TeamNotification(allocation_id, participant_id, sent_at, created_at)`, `_results_link(UUID)->str` are referenced consistently. Tests pass `UUID(a["id"])` because the column type is `Uuid(as_uuid=True)`.
- **Test-DB gotcha:** the fan-out test monkeypatches `tn.SessionLocal` to the conftest `session_factory` so the background task reads the same `test_squadsync.db` the API writes to.
