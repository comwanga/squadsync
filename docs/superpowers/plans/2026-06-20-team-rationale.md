# Team Rationale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an on-demand, PII-free AI "why this team works" rationale per team, cached on the team and shown to organizers and on public results.

**Architecture:** A new `rationale_service` builds one batched Claude (Haiku) request from PII-free team composition, parses a structured tool response, and persists `{title, summary, strengths, gaps}` JSON on each `Team`. An organizer-only endpoint triggers it; the organizer and public team views surface it. Descriptive only — the deterministic allocation engine is untouched. Mirrors the existing `categorization_service` pattern (pure `_build_request`/`_parse_*` helpers + a monkeypatchable `_classify`).

**Tech Stack:** FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, `anthropic` SDK; Next.js 16 / React 19 / Vitest frontend.

## Global Constraints

- Python deps pinned in `backend/requirements.txt`; do not add new ones (`anthropic==0.40.0` is present).
- AI calls must degrade gracefully: no `ANTHROPIC_API_KEY` → a clear error, never a crash. No deterministic fallback for rationale.
- The AI request must contain **no participant name or email**. Public output is PII-free by construction.
- Backend tests run on SQLite via the existing `tests/conftest.py` fixtures (`client`, `auth_headers`, `db`, `nostr_privkey`).
- Frontend: this is Next.js 16 — read `node_modules/next/dist/docs/` before using Next APIs. No new deps.
- Reuse the batched, system-cacheable Claude pattern from `app/services/categorization_service.py`.

---

### Task 1: `teams.rationale` column + migration

**Files:**
- Modify: `backend/app/models/team.py`
- Create: `backend/alembic/versions/0009_team_rationale.py`
- Test: `backend/tests/test_rationale_model.py`

**Interfaces:**
- Produces: `Team.rationale` — nullable `JSON` column holding `{"title": str, "summary": str, "strengths": [str], "gaps": [str]}` or `None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rationale_model.py
import uuid
from app.models.allocation import Allocation
from app.models.team import Team


def test_team_rationale_persists_json(db):
    alloc = Allocation(event_id=uuid.uuid4(), snapshot_hash="h", status="draft",
                       constraint_warnings={})
    db.add(alloc)
    db.flush()
    team = Team(allocation_id=alloc.id, name="Team 01",
                rationale={"title": "Build squad", "summary": "Strong delivery.",
                           "strengths": ["2 advanced engineers"], "gaps": ["limited outreach"]})
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.rationale["title"] == "Build squad"
    assert team.rationale["gaps"] == ["limited outreach"]


def test_team_rationale_defaults_none(db):
    alloc = Allocation(event_id=uuid.uuid4(), snapshot_hash="h2", status="draft",
                       constraint_warnings={})
    db.add(alloc)
    db.flush()
    team = Team(allocation_id=alloc.id, name="Team 02")
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.rationale is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rationale_model.py -v`
Expected: FAIL — `TypeError: 'rationale' is an invalid keyword argument for Team`.

- [ ] **Step 3: Add the column to the model**

In `backend/app/models/team.py`, update the import line and add the column to `Team`:

```python
import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Uuid, JSON

from app.core.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    allocation_id = Column(Uuid(as_uuid=True), ForeignKey("allocations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    fairness_score = Column(Float, nullable=True)
    skill_score = Column(Float, nullable=True)
    role_balance_score = Column(Float, nullable=True)
    # Cached AI explanation: {"title","summary","strengths":[...],"gaps":[...]} or None.
    rationale = Column(JSON, nullable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rationale_model.py -v`
Expected: PASS (2 passed). The `conftest.py` `setup_database` fixture creates tables from the model, so no migration is needed for tests.

- [ ] **Step 5: Write the Alembic migration (for Postgres prod)**

```python
# backend/alembic/versions/0009_team_rationale.py
"""team rationale

Adds teams.rationale (cached AI explanation per team).

Revision ID: 0009_team_rationale
Revises: 0008_payout_team_unique
Create Date: 2026-06-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0009_team_rationale"
down_revision: Union[str, None] = "0008_payout_team_unique"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("teams") as b:
        b.add_column(sa.Column("rationale", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("teams") as b:
        b.drop_column("rationale")
```

- [ ] **Step 6: Verify the migration applies and reverses**

Run: `cd backend && DATABASE_URL="sqlite:///./_mig.db" SECRET_KEY=x python -m alembic upgrade head && DATABASE_URL="sqlite:///./_mig.db" SECRET_KEY=x python -m alembic downgrade -1 && rm -f _mig.db`
Expected: both run without error; `alembic heads` shows `0009_team_rationale`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/models/team.py backend/alembic/versions/0009_team_rationale.py backend/tests/test_rationale_model.py
git commit -m "feat(rationale): add teams.rationale JSON column + migration"
```

---

### Task 2: `rationale_service` pure helpers + config

**Files:**
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/rationale_service.py`
- Test: `backend/tests/test_rationale_service.py`

**Interfaces:**
- Consumes: `Event`, `Team`, `Participant` models; `settings.RATIONALE_MODEL`, `settings.ANTHROPIC_API_KEY`.
- Produces:
  - `RationaleUnavailable(Exception)`
  - `_team_payloads(db, allocation) -> list[dict]` — each `{"id": str(team.id), "name": str, "members": [{"role": str, "experience": str, "tech_stack": [...], "interests": [...]}]}`, **no names/emails**.
  - `_build_request(event, payloads: list[dict]) -> dict` — Messages API kwargs.
  - `_parse_rationales(content_blocks) -> dict[str, dict]` — `{team_id: {"title","summary","strengths","gaps"}}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rationale_service.py
from app.services import rationale_service as rat


def _payloads():
    return [{
        "id": "team-1", "name": "Team 01",
        "members": [
            {"role": "technical", "experience": "advanced", "tech_stack": [], "interests": []},
            {"role": "design", "experience": "beginner", "tech_stack": [], "interests": []},
        ],
    }]


class _Event:
    title = "Hack Night"
    description = "Build something"


def test_build_request_is_cacheable_and_pii_free():
    req = rat._build_request(_Event(), _payloads())
    # static instructions in a cacheable system block
    assert req["system"][0]["cache_control"]["type"] == "ephemeral"
    assert req["max_tokens"] >= 2048
    # the team id reaches the model; the tool returns the structured shape
    blob = req["system"][0]["text"] + req["messages"][0]["content"]
    assert "team-1" in blob
    props = req["tools"][0]["input_schema"]["properties"]["rationales"]["items"]["properties"]
    assert set(props) >= {"team_id", "title", "summary", "strengths", "gaps"}


def test_build_request_contains_no_pii():
    payloads = _payloads()
    # composition only — names/emails never appear in the payload
    req = rat._build_request(_Event(), payloads)
    serialized = str(req)
    for leaked in ("@", "Alice", "Bob"):
        assert leaked not in serialized


def test_parse_rationales_keeps_valid_drops_malformed():
    class Block:
        type = "tool_use"
        input = {"rationales": [
            {"team_id": "a", "title": "T", "summary": "S", "strengths": ["x"], "gaps": []},
            {"team_id": "b", "title": "only-title"},  # missing required keys -> dropped
        ]}
    out = rat._parse_rationales([Block()])
    assert out["a"]["summary"] == "S"
    assert "b" not in out


def test_parse_rationales_tolerates_omitted_team():
    class Block:
        type = "tool_use"
        input = {"rationales": []}
    assert rat._parse_rationales([Block()]) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rationale_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.rationale_service'`.

- [ ] **Step 3: Add the config setting**

In `backend/app/core/config.py`, directly under the `CATEGORIZATION_MODEL` line, add:

```python
    # Model for AI team rationales (separate from categorization so it can be tuned).
    RATIONALE_MODEL: str = "claude-haiku-4-5-20251001"
```

- [ ] **Step 4: Create the service with the pure helpers**

```python
# backend/app/services/rationale_service.py
"""Generate a short, PII-free "why this team works" rationale per team.

Descriptive only — never reads into or changes the deterministic allocation
engine. Mirrors categorization_service: pure _build_request/_parse helpers plus a
monkeypatchable _classify. The AI input carries no participant names or emails.
"""
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember

logger = logging.getLogger(__name__)

_MAX_TOKENS = 4096

_SYSTEM_INSTRUCTIONS = (
    "You explain why each already-formed team is balanced. You do NOT form or change "
    "teams — you describe what exists. For each team return a short title (<=5 words), a "
    "one-sentence summary, a list of strengths, and a list of coverage gaps, grounded in "
    "the members' roles and experience. Never name or invent individuals; describe the "
    "composition only. If a team is too sparse to assess, omit it from the response."
)


class RationaleUnavailable(Exception):
    """Raised when AI rationale cannot run (no ANTHROPIC_API_KEY configured)."""


def _team_payloads(db: Session, allocation: Allocation) -> list[dict]:
    """PII-free composition per team: roles, experience, and any tech_stack/interests."""
    payloads: list[dict] = []
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        payloads.append({
            "id": str(team.id),
            "name": team.name,
            "members": [{
                "role": m.normalized_strength or m.primary_strength,
                "experience": m.experience_level,
                "tech_stack": m.tech_stack or [],
                "interests": m.interests or [],
            } for m in members],
        })
    return payloads


def _build_request(event: Event, payloads: list[dict]) -> dict:
    import json

    tool = {
        "name": "explain_teams",
        "description": "Return a structured rationale for each team.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rationales": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "team_id": {"type": "string"},
                            "title": {"type": "string"},
                            "summary": {"type": "string"},
                            "strengths": {"type": "array", "items": {"type": "string"}},
                            "gaps": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["team_id", "title", "summary", "strengths", "gaps"],
                    },
                }
            },
            "required": ["rationales"],
        },
    }
    return {
        "model": settings.RATIONALE_MODEL,
        "max_tokens": _MAX_TOKENS,
        "system": [{
            "type": "text",
            "text": _SYSTEM_INSTRUCTIONS,
            "cache_control": {"type": "ephemeral"},
        }],
        "tools": [tool],
        "tool_choice": {"type": "tool", "name": "explain_teams"},
        "messages": [{
            "role": "user",
            "content": (
                f"Event: {event.title}\nDescription: {event.description or '(none)'}\n\n"
                f"Explain each team from this composition (JSON):\n{json.dumps(payloads)}"
            ),
        }],
    }


_REQUIRED_KEYS = {"team_id", "title", "summary", "strengths", "gaps"}


def _parse_rationales(content_blocks) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for block in content_blocks:
        if getattr(block, "type", None) == "tool_use":
            for r in block.input.get("rationales", []):
                if _REQUIRED_KEYS.issubset(r) and r["team_id"]:
                    out[r["team_id"]] = {
                        "title": r["title"], "summary": r["summary"],
                        "strengths": list(r["strengths"]), "gaps": list(r["gaps"]),
                    }
    return out
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rationale_service.py -v`
Expected: PASS (4 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/core/config.py backend/app/services/rationale_service.py backend/tests/test_rationale_service.py
git commit -m "feat(rationale): PII-free prompt build + structured parse helpers"
```

---

### Task 3: `rationale_service.generate` (persist)

**Files:**
- Modify: `backend/app/services/rationale_service.py`
- Test: `backend/tests/test_rationale_service.py`

**Interfaces:**
- Consumes: `_team_payloads`, `_build_request`, `_parse_rationales`.
- Produces:
  - `_classify(event, payloads: list[dict]) -> dict[str, dict]` — does the Anthropic call (monkeypatched in tests).
  - `generate(db, allocation) -> dict[str, dict]` — persists `Team.rationale`; raises `RationaleUnavailable` when no key.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_rationale_service.py
import uuid
import pytest
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.models.user import User


def _alloc_with_team(db):
    u = User(pubkey="c" * 64); db.add(u); db.commit()
    e = Event(owner_id=u.id, title="Hack", description="d", team_count=1,
              registration_slug=f"s{uuid.uuid4().hex[:6]}", status="allocated")
    db.add(e); db.commit()
    alloc = Allocation(event_id=e.id, snapshot_hash=uuid.uuid4().hex, status="draft",
                       constraint_warnings={})
    db.add(alloc); db.flush()
    team = Team(allocation_id=alloc.id, name="Team 01"); db.add(team); db.flush()
    p = Participant(event_id=e.id, name="Alice", email="a@t.com", primary_strength="technical",
                    experience_level="advanced", strength_source="preset", composite_score=3.0,
                    tech_stack=[], interests=[]); db.add(p); db.flush()
    db.add(TeamMember(team_id=team.id, participant_id=p.id)); db.commit()
    return e, alloc, team


def test_generate_persists_rationale(db, monkeypatch):
    e, alloc, team = _alloc_with_team(db)
    monkeypatch.setattr(rat.settings, "ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(rat, "_classify", lambda event, payloads: {
        str(team.id): {"title": "Builders", "summary": "Strong.", "strengths": ["x"], "gaps": []},
    })
    out = rat.generate(db, alloc)
    assert out[str(team.id)]["title"] == "Builders"
    db.refresh(team)
    assert team.rationale["summary"] == "Strong."


def test_generate_without_key_raises(db, monkeypatch):
    _e, alloc, _team = _alloc_with_team(db)
    monkeypatch.setattr(rat.settings, "ANTHROPIC_API_KEY", None)
    with pytest.raises(rat.RationaleUnavailable):
        rat.generate(db, alloc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rationale_service.py -k generate -v`
Expected: FAIL — `AttributeError: module 'app.services.rationale_service' has no attribute 'generate'`.

- [ ] **Step 3: Implement `_classify` and `generate`**

Append to `backend/app/services/rationale_service.py`:

```python
def _classify(event: Event, payloads: list[dict]) -> dict[str, dict]:
    """Call Claude for all teams; return {team_id: rationale}. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    msg = client.messages.create(**_build_request(event, payloads))
    return _parse_rationales(msg.content)


def generate(db: Session, allocation: Allocation) -> dict[str, dict]:
    """Generate + persist a rationale per team. Raises RationaleUnavailable with no key."""
    if not settings.ANTHROPIC_API_KEY:
        raise RationaleUnavailable("AI rationale requires ANTHROPIC_API_KEY")
    event = db.query(Event).filter(Event.id == allocation.event_id).first()
    payloads = _team_payloads(db, allocation)

    mapping: dict[str, dict] = {}
    try:
        mapping = _classify(event, payloads)
    except Exception as exc:  # noqa: BLE001 — best-effort; teams without a rationale just stay null
        logger.warning("Rationale generation failed: %s", exc)

    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        r = mapping.get(str(team.id))
        if r:
            team.rationale = r
    db.commit()
    return mapping
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rationale_service.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/rationale_service.py backend/tests/test_rationale_service.py
git commit -m "feat(rationale): generate + persist team rationales"
```

---

### Task 4: Rationale endpoint

**Files:**
- Create: `backend/app/api/v1/rationale.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_rationale_endpoint.py`

**Interfaces:**
- Consumes: `rationale_service.generate`, `RationaleUnavailable`, `assert_allocation_organizer`.
- Produces: `POST /api/v1/allocations/{allocation_id}/rationale` → `{team_id: {title,summary,strengths,gaps}}`. `400` when AI unconfigured; organizer-only.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rationale_endpoint.py
from tests.test_payout_endpoint import _setup_team


def test_rationale_requires_api_key_returns_400(client, auth_headers, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None, raising=False)
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    assert res.status_code == 400
    assert "anthropic" in res.text.lower()


def test_rationale_generates_and_persists(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": ["b"]}
        for p in payloads
    })
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)

    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert all(r["title"] == "Squad" for r in body.values())
    # persisted: the organizer teams view now carries the rationale
    teams = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    assert all(t["rationale"]["summary"] == "Balanced." for t in teams)


def test_rationale_requires_organizer(client, auth_headers, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    from tests.conftest import make_nostr_event
    from coincurve import PrivateKey
    other = PrivateKey()
    pubkey = other.public_key.format(compressed=True)[1:].hex()
    token = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(other)}).json()["access_token"]
    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale",
                      headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in (401, 403, 404)
```

> Note: `test_rationale_generates_and_persists` also exercises Task 5 (rationale in `TeamOut`). Implement Task 5 before expecting that assertion to pass; until then it will fail on the missing `rationale` key — that is expected and resolved in Task 5.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rationale_endpoint.py -v`
Expected: FAIL — 404 (route not mounted) on all three.

- [ ] **Step 3: Create the router**

```python
# backend/app/api/v1/rationale.py
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
```

- [ ] **Step 4: Mount the router**

In `backend/app/main.py`, add the import to the existing `from app.api.v1 import ...` line (append `rationale`) and add, after the `payouts` router include:

```python
app.include_router(rationale.router, prefix="/api/v1/allocations", tags=["rationale"])
```

- [ ] **Step 5: Run tests**

Run: `cd backend && python -m pytest tests/test_rationale_endpoint.py -v`
Expected: `test_rationale_requires_api_key_returns_400` and `test_rationale_requires_organizer` PASS; `test_rationale_generates_and_persists` still FAILS on the `rationale` key (resolved in Task 5).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/rationale.py backend/app/main.py backend/tests/test_rationale_endpoint.py
git commit -m "feat(rationale): organizer endpoint to generate team rationales"
```

---

### Task 5: Surface rationale in organizer + public team views

**Files:**
- Modify: `backend/app/schemas/allocation.py`
- Modify: `backend/app/api/v1/teams.py`
- Modify: `backend/app/api/v1/public.py`
- Test: `backend/tests/test_rationale_endpoint.py` (existing `test_rationale_generates_and_persists`), `backend/tests/test_rationale_public.py`

**Interfaces:**
- Consumes: persisted `Team.rationale`.
- Produces: `TeamOut.rationale: Optional[dict]`, `PublicTeam.rationale: Optional[dict]`.

- [ ] **Step 1: Write the failing public test**

```python
# backend/tests/test_rationale_public.py
from tests.test_payout_endpoint import _setup_team


def test_public_results_include_rationale(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": []}
        for p in payloads
    })
    event_id, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    client.post(f"/api/v1/events/{event_id}/allocations/{allocation_id}/publish", headers=auth_headers)

    res = client.get(f"/api/v1/public/allocations/{allocation_id}")
    assert res.status_code == 200, res.text
    teams = res.json()["teams"]
    assert any(t.get("rationale") and t["rationale"]["title"] == "Squad" for t in teams)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_rationale_public.py tests/test_rationale_endpoint.py::test_rationale_generates_and_persists -v`
Expected: FAIL — responses have no `rationale` key.

- [ ] **Step 3: Add `rationale` to the schemas**

In `backend/app/schemas/allocation.py`, add `rationale: Optional[dict] = None` to **both** `TeamOut` (after `members`) and `PublicTeam` (after `members`):

```python
class TeamOut(BaseModel):
    id: UUID
    allocation_id: UUID
    name: str
    fairness_score: Optional[float]
    skill_score: Optional[float]
    role_balance_score: Optional[float]
    members: list[TeamMemberOut] = []
    rationale: Optional[dict] = None

    model_config = {"from_attributes": True}
```

```python
class PublicTeam(BaseModel):
    id: UUID
    name: str
    fairness_score: Optional[float]
    members: list[PublicTeamMember] = []
    rationale: Optional[dict] = None
```

- [ ] **Step 4: Populate `rationale` in the organizer team views**

In `backend/app/api/v1/teams.py`, add `rationale=team.rationale,` to the `TeamOut(...)` constructions in **both** `list_teams` and `get_team` (right after the `members=[...]` argument).

- [ ] **Step 5: Populate `rationale` in the public view**

In `backend/app/api/v1/public.py`, in `public_allocation`, add `rationale=team.rationale,` to the `PublicTeam(...)` construction (after `members=[...]`).

- [ ] **Step 6: Run tests**

Run: `cd backend && python -m pytest tests/test_rationale_public.py tests/test_rationale_endpoint.py -v`
Expected: PASS (all rationale endpoint + public tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/allocation.py backend/app/api/v1/teams.py backend/app/api/v1/public.py backend/tests/test_rationale_public.py
git commit -m "feat(rationale): expose rationale on organizer + public team views"
```

---

### Task 6: Clear rationale on manual edit

**Files:**
- Modify: `backend/app/services/allocation_engine.py` (in `move_participant`, after the score recompute loop, before/with `db.commit()`)
- Test: `backend/tests/test_rationale_move.py`

**Interfaces:**
- Consumes: `Team.rationale`.
- Produces: after `move_participant`, every team in the allocation has `rationale = None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rationale_move.py
from tests.test_payout_endpoint import _setup_team


def test_move_clears_rationale(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": []}
        for p in payloads
    })
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=False)
    client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)

    teams = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    target = next(t["id"] for t in teams if t["id"] != team_id)
    mover = members[0]["id"]
    client.patch(f"/api/v1/allocations/{allocation_id}/members/{mover}",
                 headers=auth_headers, json={"team_id": target})

    teams_after = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    assert all(t["rationale"] is None for t in teams_after)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rationale_move.py -v`
Expected: FAIL — rationale survives the move (still `{"title": "Squad", ...}`).

- [ ] **Step 3: Clear rationale in `move_participant`**

In `backend/app/services/allocation_engine.py`, inside `move_participant`, in the existing loop that sets each team's scores (`for team in teams:` near the end), add a line so the loop also clears the stale rationale:

```python
    for team in teams:
        team.skill_score = round(skill_score, 1)
        team.role_balance_score = round(role_balance_score, 1)
        team.fairness_score = round(fairness_score, 1)
        team.rationale = None  # composition changed; the cached explanation is stale
    db.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rationale_move.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/allocation_engine.py backend/tests/test_rationale_move.py
git commit -m "feat(rationale): clear cached rationale when a member is moved"
```

---

### Task 7: Frontend — types, API, engine UI

**Files:**
- Modify: `frontend/hooks/use-allocation.ts`
- Modify: `frontend/components/engine/results-grid.tsx`
- Modify: `frontend/components/engine/team-card.tsx`
- Test: `frontend/tests/components/team-card.test.tsx`

**Interfaces:**
- Consumes: `POST /api/v1/allocations/{id}/rationale`.
- Produces:
  - `TeamRationale` type `{ title: string; summary: string; strengths: string[]; gaps: string[] }`.
  - `Team.rationale?: TeamRationale | null`.
  - `generateRationales(token, allocationId) -> Promise<Record<string, TeamRationale>>`.

- [ ] **Step 1: Write the failing component test**

```tsx
// frontend/tests/components/team-card.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { TeamCard } from "@/components/engine/team-card";
import type { Team } from "@/hooks/use-allocation";

const team: Team = {
  id: "t1", name: "Team 01", fairness_score: 80, skill_score: 75, role_balance_score: 90,
  members: [{ id: "m1", name: "Ada", email: "a@x.com", experience_level: "advanced",
              normalized_strength: "technical" }],
  rationale: { title: "Build squad", summary: "Strong delivery.",
               strengths: ["2 advanced engineers"], gaps: ["limited outreach"] },
};

describe("TeamCard rationale", () => {
  it("renders the rationale summary and strengths/gaps when present", () => {
    render(<TeamCard team={team} />);
    expect(screen.getByText("Strong delivery.")).toBeInTheDocument();
    expect(screen.getByText("2 advanced engineers")).toBeInTheDocument();
    expect(screen.getByText("limited outreach")).toBeInTheDocument();
  });

  it("renders no rationale block when absent", () => {
    render(<TeamCard team={{ ...team, rationale: null }} />);
    expect(screen.queryByText("Strong delivery.")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run tests/components/team-card.test.tsx`
Expected: FAIL — summary text not found (and `rationale` not on `Team` type → tsc/test error).

- [ ] **Step 3: Add the type, the field, and the API call**

In `frontend/hooks/use-allocation.ts`: add the type, extend `Team`, and add the API function.

```typescript
export interface TeamRationale {
  title: string;
  summary: string;
  strengths: string[];
  gaps: string[];
}
```

In the `Team` interface, add: `rationale?: TeamRationale | null;`

At the end of the file, add:

```typescript
export async function generateRationales(token: string, allocationId: string) {
  return fetchAPI<Record<string, TeamRationale>>(
    `/api/v1/allocations/${allocationId}/rationale`,
    { method: "POST", token }
  );
}
```

- [ ] **Step 4: Render the rationale in `TeamCard`**

In `frontend/components/engine/team-card.tsx`, add this block inside `<CardContent>` (after the strength-count badges `<div className="flex flex-wrap gap-1"> ... </div>`):

```tsx
        {team.rationale && (
          <div className="rounded-md bg-violet-50 border border-violet-100 p-2 space-y-1">
            <p className="text-xs font-semibold text-violet-900">{team.rationale.title}</p>
            <p className="text-xs text-violet-800">{team.rationale.summary}</p>
            {team.rationale.strengths.length > 0 && (
              <ul className="text-xs text-violet-700 list-disc list-inside">
                {team.rationale.strengths.map((s, i) => <li key={`s-${i}`}>{s}</li>)}
              </ul>
            )}
            {team.rationale.gaps.length > 0 && (
              <ul className="text-xs text-amber-700 list-disc list-inside">
                {team.rationale.gaps.map((g, i) => <li key={`g-${i}`}>{g}</li>)}
              </ul>
            )}
          </div>
        )}
```

- [ ] **Step 5: Run the component test**

Run: `cd frontend && npx vitest run tests/components/team-card.test.tsx`
Expected: PASS (2 passed).

- [ ] **Step 6: Add the "Explain teams" button to `ResultsGrid`**

In `frontend/components/engine/results-grid.tsx`:

Update the import from `@/hooks/use-allocation` to also import `generateRationales`. Add a handler inside the component (next to `handleRegenerate`):

```tsx
  const [explaining, setExplaining] = useState(false);

  const handleExplain = async () => {
    if (!session?.accessToken || explaining) return;
    setExplaining(true);
    try {
      const map = await generateRationales(session.accessToken, allocation.id);
      const teams = allocation.teams.map(t => ({ ...t, rationale: map[t.id] ?? t.rationale }));
      onChanged({ ...allocation, teams });
      toast.success("Teams explained");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Could not explain teams");
    } finally {
      setExplaining(false);
    }
  };
```

In the action-button row (the `<div className="flex flex-wrap gap-2 pt-2">`), add as the first button (always shown, draft or published):

```tsx
        <Button variant="outline" onClick={handleExplain} disabled={explaining || working}>
          <Sparkles className="mr-2 h-4 w-4" /> {explaining ? "Explaining…" : "Explain teams"}
        </Button>
```

Add `Sparkles` to the `lucide-react` import at the top of the file.

- [ ] **Step 7: Typecheck + lint + run the frontend unit suite**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npx vitest run`
Expected: tsc exit 0; lint 0 errors; all tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/hooks/use-allocation.ts frontend/components/engine/results-grid.tsx frontend/components/engine/team-card.tsx frontend/tests/components/team-card.test.tsx
git commit -m "feat(rationale): Explain teams button + rationale on team cards"
```

---

### Task 8: Frontend — public results rendering

**Files:**
- Modify: `frontend/app/results/[allocationId]/page.tsx` (render `team.rationale` per team)
- Test: `frontend/tests/components/...` (only if the page is decomposed into a testable component; otherwise verify via typecheck + manual)

**Interfaces:**
- Consumes: `team.rationale` from the public allocation response (already typed via the shared `Team`/public shape).

- [ ] **Step 1: Inspect the public results page**

Run: `sed -n '1,200p' frontend/app/results/[allocationId]/page.tsx` (read it) to find where each team is rendered and what type it uses for teams.

- [ ] **Step 2: Render the rationale block per team**

Where each public team is rendered, add the same violet rationale block as in `TeamCard` (title + summary + strengths + gaps), guarded by `team.rationale &&`. If the public team type is local to the page, add an optional `rationale?: { title: string; summary: string; strengths: string[]; gaps: string[] } | null` to it.

```tsx
{team.rationale && (
  <div className="rounded-md bg-violet-50 border border-violet-100 p-3 mt-2 space-y-1">
    <p className="text-sm font-semibold text-violet-900">{team.rationale.title}</p>
    <p className="text-sm text-violet-800">{team.rationale.summary}</p>
    {team.rationale.strengths.length > 0 && (
      <ul className="text-xs text-violet-700 list-disc list-inside">
        {team.rationale.strengths.map((s: string, i: number) => <li key={i}>{s}</li>)}
      </ul>
    )}
    {team.rationale.gaps.length > 0 && (
      <ul className="text-xs text-amber-700 list-disc list-inside">
        {team.rationale.gaps.map((g: string, i: number) => <li key={i}>{g}</li>)}
      </ul>
    )}
  </div>
)}
```

- [ ] **Step 3: Typecheck + lint + build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=x npm run build`
Expected: tsc exit 0; lint 0 errors; build succeeds.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/results/[allocationId]/page.tsx
git commit -m "feat(rationale): show team rationale on public results"
```

---

## Self-Review

**Spec coverage:**
- On-demand trigger → Task 4 endpoint + Task 7 button. ✓
- Structured JSON `{title,summary,strengths,gaps}` → Tasks 1–3. ✓
- Cached on team + cleared on re-run/edit → Task 1 column, Task 6 clears on move; regenerate makes new teams (no rationale) by existing behavior. ✓
- PII-free input + public surface → Task 2 (`_team_payloads` excludes name/email; PII test), Task 5 public schema. ✓
- No-key → 400 "AI not configured" → Task 3 raises, Task 4 maps to 400, Task 7 toast. ✓
- Separate `RATIONALE_MODEL` → Task 2. ✓
- Determinism untouched → rationale never read by `allocation_engine` generation; only cleared on edit. ✓

**Placeholder scan:** Task 8 Step 1 intentionally inspects an unread file before editing; the edit code is fully specified. No "TBD"/"handle errors" placeholders elsewhere.

**Type consistency:** `TeamRationale {title, summary, strengths[], gaps[]}` matches the backend `_parse_rationales` output and `Team.rationale` JSON shape across all tasks. `generateRationales` returns `Record<string, TeamRationale>` matching the endpoint's `{team_id: rationale}`.
