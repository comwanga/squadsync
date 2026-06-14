# AI-Assisted Team Categorization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make SquadSync usable by any team for any event — replace developer-only roles with a universal "Primary Strength" + free-text "Other", normalize Other entries with Claude Haiku in the background, and keep team allocation fully deterministic.

**Architecture:** A shared taxonomy constant is the single source of truth. Registrants pick a Primary Strength (or type Other). The deterministic engine balances on a `normalized_strength` field. Claude (Haiku 4.5) only maps Other free-text → a universal category, called automatically before allocation, with a no-AI fallback. Organizer can override any category inline.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), Anthropic Python SDK (Haiku 4.5), Next.js 16 + React Hook Form + Zod (frontend), pytest + vitest.

**Spec:** `docs/superpowers/specs/2026-06-14-ai-assisted-team-categorization-design.md`

**Branch:** `feat/ai-team-categorization` (already created).

---

## Decisions locked (do not re-derive)

- **Universal categories** (value → label):
  `technical`→Technical / Hands-on · `design`→Design / Creative · `planning`→Planning / Strategy · `coordination`→Coordination / Operations · `communication`→Communication / Outreach · `research`→Research / Analysis · `domain_expert`→Domain Expert · `other`→Other (type your own)
- **Experience** is 3 levels: `beginner|intermediate|advanced`. `years_experience` and the `professional` level are **removed**.
- **Composite score** = single experience dimension: `beginner=1.0, intermediate=2.0, advanced=3.0`. (Anchors ≥3.0 = advanced; intermediates 1.5–3.0 = intermediate; <1.5 = beginner.) Engine still reads `AllocationConfig` but weights no longer affect the 1-D score.
- **Participant categorization fields:** `primary_strength` (one universal value), `strength_other` (free text when `other`), `normalized_strength` (value the engine uses), `strength_source` (`preset|ai|fallback|manual`).
- **Preset path:** `normalized_strength = primary_strength`, `strength_source = preset`. **Other path:** `normalized_strength = NULL` until AI/fallback fills it.
- **AI model:** `claude-haiku-4-5` (confirm exact id `claude-haiku-4-5-20251001` and params via the `claude-api` skill at build time). Only called for Other entries.
- **Override:** `strength_source = manual` is never overwritten by re-normalization.

---

## Phase 0 — Shared taxonomy constant (single source of truth)

**Files:**
- Create: `backend/app/core/taxonomy.py`
- Test: `backend/tests/test_taxonomy.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_taxonomy.py
from app.core.taxonomy import (
    PRIMARY_STRENGTHS, CONCRETE_STRENGTHS, EXPERIENCE_LEVELS, EXPERIENCE_SCORE,
)


def test_strength_values():
    assert "other" in PRIMARY_STRENGTHS
    assert "technical" in PRIMARY_STRENGTHS
    assert len(PRIMARY_STRENGTHS) == 8


def test_concrete_excludes_other():
    assert "other" not in CONCRETE_STRENGTHS
    assert set(CONCRETE_STRENGTHS) == set(PRIMARY_STRENGTHS) - {"other"}


def test_experience_scale():
    assert EXPERIENCE_LEVELS == ("beginner", "intermediate", "advanced")
    assert EXPERIENCE_SCORE == {"beginner": 1.0, "intermediate": 2.0, "advanced": 3.0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_taxonomy.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.core.taxonomy'`

- [ ] **Step 3: Create the constant**

```python
# backend/app/core/taxonomy.py
"""Single source of truth for the universal participant taxonomy.

Used by the registration schema, the AI normalization prompt, and the
allocation engine so the category set never drifts across layers.
"""

# Universal "Primary Strength" values the registrant can choose.
PRIMARY_STRENGTHS: tuple[str, ...] = (
    "technical",
    "design",
    "planning",
    "coordination",
    "communication",
    "research",
    "domain_expert",
    "other",
)

# Human-readable labels (frontend mirrors these; kept here for prompts/exports).
STRENGTH_LABELS: dict[str, str] = {
    "technical": "Technical / Hands-on",
    "design": "Design / Creative",
    "planning": "Planning / Strategy",
    "coordination": "Coordination / Operations",
    "communication": "Communication / Outreach",
    "research": "Research / Analysis",
    "domain_expert": "Domain Expert",
    "other": "Other",
}

# The concrete categories the AI must map an "Other" entry into (excludes "other").
CONCRETE_STRENGTHS: tuple[str, ...] = tuple(s for s in PRIMARY_STRENGTHS if s != "other")

EXPERIENCE_LEVELS: tuple[str, ...] = ("beginner", "intermediate", "advanced")
EXPERIENCE_SCORE: dict[str, float] = {"beginner": 1.0, "intermediate": 2.0, "advanced": 3.0}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_taxonomy.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/taxonomy.py backend/tests/test_taxonomy.py
git commit -m "feat(taxonomy): universal strength + experience constants"
```

---

## Phase 1 — Participant model + Alembic migration

**Files:**
- Modify: `backend/app/models/participant.py`
- Create: `backend/alembic/versions/0003_universal_strength_taxonomy.py`

- [ ] **Step 1: Update the model** — replace `role`, `skill_level`, `years_experience` lines (current lines 19–30) with the new fields. Final field block:

```python
    skill_level = None  # removed; see experience_level
    experience_level = Column(
        SAEnum("beginner", "intermediate", "advanced", name="experience_level"),
        nullable=False,
    )
    primary_strength = Column(
        SAEnum(
            "technical", "design", "planning", "coordination",
            "communication", "research", "domain_expert", "other",
            name="primary_strength",
        ),
        nullable=False,
    )
    strength_other = Column(String, nullable=True)
    normalized_strength = Column(String, nullable=True)
    strength_source = Column(String, nullable=False, default="preset")
    tech_stack = Column(JSON, nullable=False, default=list)
    interests = Column(JSON, nullable=False, default=list)
    composite_score = Column(Float, nullable=True)
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
```

Remove the literal `skill_level = None` placeholder line — it was only to show the deletion; the actual file must simply not contain `role`, `skill_level`, or `years_experience`. Keep imports (`Enum as SAEnum`, etc.) unchanged.

- [ ] **Step 2: Verify the model imports**

Run: `cd backend && python -c "from app.models.participant import Participant; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Write the migration** (model-driven; the DB is pre-launch so participant rows may be dropped/recreated)

```python
# backend/alembic/versions/0003_universal_strength_taxonomy.py
"""universal strength taxonomy

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pre-launch: clear participants so the not-null strength/experience columns
    # can be added without back-fill. Allocations reference participants, so clear
    # downstream rows first to respect FKs.
    op.execute("DELETE FROM team_members")
    op.execute("DELETE FROM teams")
    op.execute("DELETE FROM allocations")
    op.execute("DELETE FROM participants")

    with op.batch_alter_table("participants") as b:
        b.drop_column("role")
        b.drop_column("skill_level")
        b.drop_column("years_experience")
        b.add_column(sa.Column("experience_level", sa.String(), nullable=False, server_default="beginner"))
        b.add_column(sa.Column("primary_strength", sa.String(), nullable=False, server_default="other"))
        b.add_column(sa.Column("strength_other", sa.String(), nullable=True))
        b.add_column(sa.Column("normalized_strength", sa.String(), nullable=True))
        b.add_column(sa.Column("strength_source", sa.String(), nullable=False, server_default="preset"))


def downgrade() -> None:
    with op.batch_alter_table("participants") as b:
        b.drop_column("strength_source")
        b.drop_column("normalized_strength")
        b.drop_column("strength_other")
        b.drop_column("primary_strength")
        b.drop_column("experience_level")
        b.add_column(sa.Column("role", sa.String(), nullable=True))
        b.add_column(sa.Column("skill_level", sa.String(), nullable=True))
        b.add_column(sa.Column("years_experience", sa.Integer(), nullable=True))
```

> Note: enums are declared as `SAEnum` in the model but stored as strings; the migration uses `sa.String()` for portability (SQLite has no native ENUM). Confirm `down_revision = "0002"` matches the latest existing revision id in `backend/alembic/versions/0002_replay_and_unique_email.py`.

- [ ] **Step 4: Apply migration on a scratch DB**

Run: `cd backend && DATABASE_URL="sqlite:///./mig_check.db" python -m alembic upgrade head && rm -f mig_check.db`
Expected: ends at revision 0003 with no error.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/participant.py backend/alembic/versions/0003_universal_strength_taxonomy.py
git commit -m "feat(model): replace dev roles with universal strength + 3-level experience"
```

---

## Phase 2 — Pydantic schemas

**Files:**
- Modify: `backend/app/schemas/participant.py`
- Modify: `backend/app/schemas/allocation.py`

- [ ] **Step 1: Rewrite `participant.py`**

```python
# backend/app/schemas/participant.py
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, model_validator

ExperienceLevel = Literal["beginner", "intermediate", "advanced"]
PrimaryStrength = Literal[
    "technical", "design", "planning", "coordination",
    "communication", "research", "domain_expert", "other",
]


class ParticipantRegister(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=40)
    primary_strength: PrimaryStrength
    strength_other: Optional[str] = Field(default=None, max_length=120)
    experience_level: ExperienceLevel
    tech_stack: list[str] = []
    interests: list[str] = []

    @model_validator(mode="after")
    def _require_other_text(self):
        if self.primary_strength == "other" and not (self.strength_other and self.strength_other.strip()):
            raise ValueError("Please describe your strength when choosing 'Other'.")
        return self


class ParticipantOut(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    email: str
    phone: Optional[str]
    primary_strength: str
    strength_other: Optional[str]
    normalized_strength: Optional[str]
    strength_source: str
    experience_level: str
    composite_score: Optional[float]

    model_config = {"from_attributes": True}


class ParticipantCategoryUpdate(BaseModel):
    normalized_strength: str = Field(min_length=1, max_length=120)


class EventPublicInfo(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    participant_limit: Optional[int]
    status: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: Update `allocation.py`** — in `TeamMemberOut` (lines 22–30) and `PublicTeamMember` (lines 58–64) replace `role: str` + `skill_level: str` with `normalized_strength: Optional[str]` and `experience_level: str`:

```python
class TeamMemberOut(BaseModel):
    id: UUID
    name: str
    email: str
    normalized_strength: Optional[str]
    experience_level: str
    composite_score: Optional[float]

    model_config = {"from_attributes": True}
```

```python
class PublicTeamMember(BaseModel):
    id: UUID
    name: str
    normalized_strength: Optional[str]
    experience_level: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Verify imports**

Run: `cd backend && python -c "from app.schemas.participant import ParticipantRegister, ParticipantCategoryUpdate; from app.schemas.allocation import TeamMemberOut; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/schemas/participant.py backend/app/schemas/allocation.py
git commit -m "feat(schema): strength/experience fields + category update schema"
```

---

## Phase 3 — Composite score (3-level) + registration service

**Files:**
- Modify: `backend/app/services/allocation_engine.py` (lines 13–27)
- Modify: `backend/app/services/registration_service.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_composite_score.py
from app.services.allocation_engine import compute_composite_score


def test_beginner():
    assert compute_composite_score("beginner") == 1.0


def test_intermediate():
    assert compute_composite_score("intermediate") == 2.0


def test_advanced():
    assert compute_composite_score("advanced") == 3.0
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_composite_score.py -v`
Expected: FAIL — current signature requires `(years_exp, skill_level, ...)`.

- [ ] **Step 3: Replace the score helper in `allocation_engine.py`** (delete `_EXP_MAP`, `_SKILL_MAP`, and the old `compute_composite_score`, lines 13–27):

```python
from app.core.taxonomy import EXPERIENCE_SCORE


def compute_composite_score(experience_level: str) -> float:
    """Single-dimension experience score (1.0–3.0).

    Maps cleanly onto the engine's passes: advanced (3.0) = anchor,
    intermediate (2.0), beginner (1.0) = fill.
    """
    return EXPERIENCE_SCORE[experience_level]
```

- [ ] **Step 4: Update the engine's recompute loop** — in `run_allocation`, replace the score recompute (current lines 47–51):

```python
    for p in participants:
        p.composite_score = compute_composite_score(p.experience_level)
    db.flush()
```

- [ ] **Step 5: Swap `role` → `normalized_strength` in the engine.** Replace every `p.role` / `member.role` / `anchor.role` and the `"roles"` bucket usage with the normalized strength, defaulting to the preset when unset. Specifically:
  - line 74 `buckets[idx]["roles"].append(anchor.role)` → `.append(anchor.normalized_strength or anchor.primary_strength)`
  - line 86 `buckets[idx]["roles"].append(p.role)` → `.append(p.normalized_strength or p.primary_strength)`
  - `_take_from_pool`: `if p.role == role` → `if (p.normalized_strength or p.primary_strength) == role`
  - `_relocate_from_surplus`: `if member.role == role` → `if (member.normalized_strength or member.primary_strength) == role`
  - lines 118/133 `bucket["roles"].append(member.role)` / `.append(c.role)` → `.append(member.normalized_strength or member.primary_strength)` / `.append(c.normalized_strength or c.primary_strength)`
  - line 153 `buckets[idx]["roles"].append(p.role)` → `.append(p.normalized_strength or p.primary_strength)`

  (`config.role_constraints` keys now hold strength categories; field name unchanged to avoid a config migration.)

- [ ] **Step 6: Update `registration_service.py`** — delete the duplicated `_EXP_MAP/_SKILL_MAP/compute_composite_score` (lines 12–19), import the engine's version, and set strength fields on register. Replace the top imports + score line + register body:

```python
from app.services.allocation_engine import compute_composite_score
```

In `register_participant`, replace the score+construct block (current lines 49–54):

```python
    is_preset = req.primary_strength != "other"
    score = compute_composite_score(req.experience_level)
    participant = Participant(
        event_id=event.id,
        composite_score=score,
        normalized_strength=req.primary_strength if is_preset else None,
        strength_source="preset",
        **req.model_dump(),
    )
```

In `list_participants` (lines 66–74), replace the `role`/`skill` filters:

```python
def list_participants(db: Session, event_id: UUID, user_id: UUID, strength: str = None, experience: str = None) -> list[Participant]:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    q = db.query(Participant).filter(Participant.event_id == event_id)
    if strength:
        q = q.filter(Participant.normalized_strength == strength)
    if experience:
        q = q.filter(Participant.experience_level == experience)
    return q.all()
```

- [ ] **Step 7: Run the new score test**

Run: `cd backend && python -m pytest tests/test_composite_score.py -v`
Expected: PASS (3 passed)

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/allocation_engine.py backend/app/services/registration_service.py backend/tests/test_composite_score.py
git commit -m "feat(engine): 3-level composite score + balance on normalized_strength"
```

---

## Phase 4 — AI categorization service (Other only) + fallback

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/categorization_service.py`
- Test: `backend/tests/test_categorization.py`

- [ ] **Step 1: Add the dependency** — append to `backend/requirements.txt`:

```
anthropic>=0.39
```

Run: `cd backend && pip install "anthropic>=0.39"`
Expected: installs successfully.

- [ ] **Step 2: Add config** — append to `Settings` in `backend/app/core/config.py` (after `PUBLIC_API_URL`):

```python
    ANTHROPIC_API_KEY: str | None = None
    CATEGORIZATION_MODEL: str = "claude-haiku-4-5-20251001"
```

> Confirm the exact current Haiku model id and Messages/tool-use params via the `claude-api` skill before finalizing.

- [ ] **Step 3: Write the failing test** (Anthropic client fully mocked — no network)

```python
# backend/tests/test_categorization.py
from unittest.mock import patch
import uuid

from app.core.database import Base
from app.models.event import Event
from app.models.participant import Participant
from app.models.user import User
from app.services import categorization_service as cat
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

engine = create_engine("sqlite:///./test_cat.db", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = Session()
    try:
        yield s
    finally:
        s.close()


def _event_with_other(db):
    u = User(pubkey="b" * 64); db.add(u); db.commit()
    e = Event(owner_id=u.id, title="AI for Agriculture", description="Crop yields via satellite + AI",
              team_count=2, registration_slug="ag", status="active")
    db.add(e); db.commit()
    p = Participant(event_id=e.id, name="Carol", email=f"c{uuid.uuid4().hex[:4]}@t.com",
                    primary_strength="other", strength_other="Agronomist",
                    experience_level="advanced", strength_source="preset",
                    composite_score=3.0, tech_stack=[], interests=[])
    db.add(p); db.commit()
    return e, p


def test_ai_maps_other_to_category(db):
    e, p = _event_with_other(db)
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        cat.normalize_pending(db, e.id)
    db.refresh(p)
    assert p.normalized_strength == "domain_expert"
    assert p.strength_source == "ai"


def test_fallback_when_no_key(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", None)
    cat.normalize_pending(db, e.id)
    db.refresh(p)
    assert p.normalized_strength  # slug of "Agronomist"
    assert p.strength_source == "fallback"


def test_manual_override_not_touched(db):
    e, p = _event_with_other(db)
    p.normalized_strength = "research"; p.strength_source = "manual"; db.commit()
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        cat.normalize_pending(db, e.id)
    db.refresh(p)
    assert p.normalized_strength == "research"  # untouched
```

- [ ] **Step 4: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_categorization.py -v`
Expected: FAIL — `categorization_service` not found.

- [ ] **Step 5: Implement the service**

```python
# backend/app/services/categorization_service.py
"""Normalize free-text 'Other' strengths into universal categories.

Claude (Haiku) only interprets meaning; it never assigns teams. When no API key
is configured or the call fails, each Other entry becomes its own slug bucket so
allocation still works deterministically.
"""
import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.taxonomy import CONCRETE_STRENGTHS, STRENGTH_LABELS
from app.models.event import Event
from app.models.participant import Participant

logger = logging.getLogger(__name__)


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")
    return s or "other"


def _pending(db: Session, event_id: UUID) -> list[Participant]:
    return (
        db.query(Participant)
        .filter(
            Participant.event_id == event_id,
            Participant.primary_strength == "other",
            Participant.strength_source != "manual",
            Participant.normalized_strength.is_(None),
        )
        .all()
    )


def _classify(event: Event, participants: list[Participant]) -> dict[str, str]:
    """Call Claude; return {participant_id: concrete_category}. Raises on failure."""
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    categories = ", ".join(f"{v} ({STRENGTH_LABELS[v]})" for v in CONCRETE_STRENGTHS)
    people = "\n".join(f"- id={p.id}: {p.strength_other}" for p in participants)
    tool = {
        "name": "assign_categories",
        "description": "Assign each participant to the single best-fit category.",
        "input_schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "category": {"type": "string", "enum": list(CONCRETE_STRENGTHS)},
                        },
                        "required": ["id", "category"],
                    },
                }
            },
            "required": ["assignments"],
        },
    }
    msg = client.messages.create(
        model=settings.CATEGORIZATION_MODEL,
        max_tokens=1024,
        tools=[tool],
        tool_choice={"type": "tool", "name": "assign_categories"},
        messages=[{
            "role": "user",
            "content": (
                f"Event: {event.title}\nDescription: {event.description or '(none)'}\n\n"
                f"Available categories: {categories}\n\n"
                f"Map each participant's free-text strength to the best category.\n{people}"
            ),
        }],
    )
    out: dict[str, str] = {}
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use":
            for a in block.input["assignments"]:
                if a["category"] in CONCRETE_STRENGTHS:
                    out[a["id"]] = a["category"]
    return out


def normalize_pending(db: Session, event_id: UUID) -> None:
    """Fill normalized_strength for un-normalized Other entries. Never raises."""
    pending = _pending(db, event_id)
    if not pending:
        return
    event = db.query(Event).filter(Event.id == event_id).first()

    mapping: dict[str, str] = {}
    if settings.ANTHROPIC_API_KEY:
        try:
            mapping = _classify(event, pending)
        except Exception as exc:  # noqa: BLE001 — AI is best-effort
            logger.warning("Categorization AI failed, using fallback: %s", exc)
            mapping = {}

    for p in pending:
        ai_cat = mapping.get(str(p.id))
        if ai_cat:
            p.normalized_strength = ai_cat
            p.strength_source = "ai"
        else:
            p.normalized_strength = _slug(p.strength_other or "other")
            p.strength_source = "fallback"
    db.commit()
```

- [ ] **Step 6: Run the tests**

Run: `cd backend && python -m pytest tests/test_categorization.py -v && rm -f test_cat.db`
Expected: PASS (3 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/core/config.py backend/app/services/categorization_service.py backend/tests/test_categorization.py
git commit -m "feat(ai): Haiku categorization of Other strengths with deterministic fallback"
```

---

## Phase 5 — Wire normalization into allocation

**Files:**
- Modify: `backend/app/api/v1/allocation.py` (the `allocate` endpoint, lines 83–92)

- [ ] **Step 1: Call normalization before the engine.** Add import and one call:

```python
from app.services.categorization_service import normalize_pending
```

In `allocate`, insert before `allocation = run_allocation(...)`:

```python
    normalize_pending(db, event_id)
    allocation = run_allocation(db, event_id, config)
```

- [ ] **Step 2: Smoke-test the app imports**

Run: `cd backend && DATABASE_URL="sqlite:///./x.db" SECRET_KEY=x python -c "from app.main import app; print('ok')" && rm -f x.db`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/v1/allocation.py
git commit -m "feat(allocate): normalize Other strengths before deterministic allocation"
```

---

## Phase 6 — Inline category override endpoint

**Files:**
- Modify: `backend/app/services/registration_service.py` (add function)
- Modify: `backend/app/api/v1/participants.py` (add PATCH route)
- Test: `backend/tests/test_override.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_override.py
import uuid
from app.models.event import Event
from app.models.participant import Participant
from app.models.user import User
from app.services.registration_service import override_category
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
import pytest

engine = create_engine("sqlite:///./test_ovr.db", connect_args={"check_same_thread": False})
Session = sessionmaker(bind=engine)


@pytest.fixture(autouse=True)
def setup():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    s = Session()
    try:
        yield s
    finally:
        s.close()


def test_override_sets_manual(db):
    u = User(pubkey="c" * 64); db.add(u); db.commit()
    e = Event(owner_id=u.id, title="E", team_count=2, registration_slug="o", status="active")
    db.add(e); db.commit()
    p = Participant(event_id=e.id, name="A", email=f"a{uuid.uuid4().hex[:4]}@t.com",
                    primary_strength="other", strength_other="GIS Analyst",
                    experience_level="advanced", normalized_strength="research",
                    strength_source="ai", composite_score=3.0, tech_stack=[], interests=[])
    db.add(p); db.commit()
    override_category(db, e.id, p.id, u.id, "domain_expert")
    db.refresh(p)
    assert p.normalized_strength == "domain_expert"
    assert p.strength_source == "manual"
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_override.py -v`
Expected: FAIL — `override_category` not defined.

- [ ] **Step 3: Add the service function** to `registration_service.py`:

```python
def override_category(db: Session, event_id: UUID, participant_id: UUID, user_id: UUID, normalized_strength: str) -> Participant:
    from app.services.event_service import _assert_organizer
    _assert_organizer(db, event_id, user_id)
    p = db.query(Participant).filter(
        Participant.id == participant_id, Participant.event_id == event_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    p.normalized_strength = normalized_strength
    p.strength_source = "manual"
    db.commit()
    db.refresh(p)
    return p
```

- [ ] **Step 4: Add the PATCH route** to `participants.py` (import `ParticipantCategoryUpdate` and `override_category`):

```python
from app.schemas.participant import ParticipantRegister, ParticipantOut, EventPublicInfo, ParticipantCategoryUpdate
from app.services.registration_service import (
    get_public_event, register_participant, list_participants, delete_participant, override_category,
)


@router.patch("/{event_id}/participants/{participant_id}", response_model=ParticipantOut)
def patch_category(
    event_id: UUID,
    participant_id: UUID,
    req: ParticipantCategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return override_category(db, event_id, participant_id, current_user.id, req.normalized_strength)
```

Also update the `list_all` query param names to match Phase 3 (`strength`, `experience`):

```python
@router.get("/{event_id}/participants", response_model=list[ParticipantOut])
def list_all(
    event_id: UUID,
    strength: Optional[str] = Query(None),
    experience: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_participants(db, event_id, current_user.id, strength, experience)
```

- [ ] **Step 5: Run the test**

Run: `cd backend && python -m pytest tests/test_override.py -v && rm -f test_ovr.db`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/registration_service.py backend/app/api/v1/participants.py backend/tests/test_override.py
git commit -m "feat(api): inline category override endpoint"
```

---

## Phase 7 — Update existing backend tests to the new model

**Files:**
- Modify: `backend/tests/test_allocation_engine.py`
- Modify: `backend/tests/test_registration.py`
- Modify: `backend/tests/test_validation.py`
- Modify: `backend/tests/test_export.py` (if it references `role`/`skill_level`)

> First read each file fully. Replace participant construction and assertions per the mapping below. Do not invent fields.

- [ ] **Step 1: Rewrite `test_allocation_engine.py` helpers + score tests.** Replace the `add_participant` helper (lines 59–72) and the four composite-score tests (lines 76–92):

```python
def add_participant(db, event_id, experience, strength, _years=0):
    p = Participant(
        event_id=event_id,
        name=f"{strength}-{experience}",
        email=f"{strength}{experience}{uuid.uuid4().hex[:4]}@test.com",
        experience_level=experience,
        primary_strength=strength,
        normalized_strength=strength,
        strength_source="preset",
        tech_stack=[],
        interests=[],
    )
    db.add(p)
    db.commit()
    return p


def test_score_beginner():
    assert compute_composite_score("beginner") == pytest.approx(1.0)


def test_score_advanced():
    assert compute_composite_score("advanced") == pytest.approx(3.0)


def test_score_intermediate():
    assert compute_composite_score("intermediate") == pytest.approx(2.0)
```

Then update every `add_participant(...)` call and `.role`/`.skill_level` assertion in this file:
- Replace skill arg values: `"professional"` → `"advanced"`; keep `beginner/intermediate/advanced`.
- Replace role arg values (`"frontend"`, `"backend"`, `"ux"`, `"fullstack"`, `"devops"`, `"mobile"`, `"product"`) with universal values (`"technical"`, `"design"`, `"coordination"`, `"research"`, `"domain_expert"`, etc.) — any concrete strength is fine; keep them varied.
- `role_constraints={"frontend": 1}` → `{"technical": 1}` (and matching participants use `strength="technical"`).
- Assertions `m.skill_level == "professional"` → `m.experience_level == "advanced"`; `p.role for p in ...` / `"backend" in roles` → `p.normalized_strength` / `"technical" in strengths`.
- `add_participant(db, e.id, "professional", "backend", 10)` style calls keep 4th arg (ignored) or drop it.

- [ ] **Step 2: Run the engine tests**

Run: `cd backend && python -m pytest tests/test_allocation_engine.py -v && rm -f test_engine.db`
Expected: PASS (all).

- [ ] **Step 3: Update `test_registration.py`** — read it, then in every register payload replace `"skill_level": "..."` → `"experience_level": "..."` (drop `"professional"`), `"role": "<dev>"` → `"primary_strength": "<universal>"`, and remove `"years_experience"`. Add a case for `primary_strength="other"` requiring `strength_other`.

- [ ] **Step 4: Update `test_validation.py`** — read it; any enum-rejection cases for `role`/`skill_level` become `primary_strength`/`experience_level`. Add: posting `primary_strength="other"` without `strength_other` returns 422.

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all pass (remove leftover `test_*.db` files if any: `rm -f backend/*.db`).

- [ ] **Step 6: Commit**

```bash
git add backend/tests/
git commit -m "test: migrate suite to universal strength + 3-level experience"
```

---

## Phase 8 — Frontend registration form

**Files:**
- Create: `frontend/lib/taxonomy.ts` (mirror of backend constant)
- Modify: `frontend/components/registration/registration-form.tsx`
- Modify: `frontend/tests/components/registration-form.test.tsx`

- [ ] **Step 1: Create the shared frontend taxonomy**

```ts
// frontend/lib/taxonomy.ts
export const PRIMARY_STRENGTHS = [
  { value: "technical", label: "Technical / Hands-on" },
  { value: "design", label: "Design / Creative" },
  { value: "planning", label: "Planning / Strategy" },
  { value: "coordination", label: "Coordination / Operations" },
  { value: "communication", label: "Communication / Outreach" },
  { value: "research", label: "Research / Analysis" },
  { value: "domain_expert", label: "Domain Expert" },
  { value: "other", label: "Other (type your own)" },
] as const;

export const EXPERIENCE_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
] as const;

export type PrimaryStrength = (typeof PRIMARY_STRENGTHS)[number]["value"];
```

- [ ] **Step 2: Rewrite the form schema + fields** in `registration-form.tsx`. Replace the Zod schema (lines 17–24) and the Skill Level / Preferred Role / Years blocks (lines 86–127) with Primary Strength (+ conditional Other) and an Experience segmented control. New schema:

```tsx
import { PRIMARY_STRENGTHS, EXPERIENCE_LEVELS } from "@/lib/taxonomy";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().min(1, "Email is required").email("Invalid email"),
  phone: z.string().optional(),
  primary_strength: z.enum([
    "technical","design","planning","coordination","communication","research","domain_expert","other",
  ]),
  strength_other: z.string().optional(),
  experience_level: z.enum(["beginner","intermediate","advanced"]),
}).refine(
  d => d.primary_strength !== "other" || (d.strength_other?.trim().length ?? 0) > 0,
  { message: "Please describe your strength", path: ["strength_other"] },
);
```

Default values: `{ primary_strength: "technical", experience_level: "intermediate" }`. Watch `primary_strength` (via `watch("primary_strength")`) to conditionally render the `strength_other` `<Input>` when it equals `"other"`. Render Primary Strength with the existing `Select` (mapping `PRIMARY_STRENGTHS`) and Experience as a 3-button segmented control (radio group styled as buttons) so it's clearly visible on mobile/dark backgrounds — the visibility complaint. Submit `data` unchanged to `/api/v1/events/${slug}/register`.

- [ ] **Step 3: Update the component test** — read `registration-form.test.tsx`; update field labels/queries from "Skill Level"/"Preferred Role"/"Years" to "Primary Strength"/"Experience", and add a test that choosing "Other" reveals the text input and that submitting Other-without-text shows the error.

- [ ] **Step 4: Run frontend unit tests**

Run: `cd frontend && npm test`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/taxonomy.ts frontend/components/registration/registration-form.tsx frontend/tests/components/registration-form.test.tsx
git commit -m "feat(ui): universal Primary Strength + Other + visible Experience control"
```

---

## Phase 9 — Frontend attendees table (category column + inline edit + filters)

**Files:**
- Modify: `frontend/components/attendees/attendees-table.tsx`

- [ ] **Step 1: Update the `Participant` interface** — replace `role`, `skill_level`, `years_experience` with:

```tsx
interface Participant {
  id: string;
  name: string;
  email: string;
  primary_strength: string;
  strength_other?: string;
  normalized_strength?: string;
  strength_source: string;
  experience_level: string;
  composite_score?: number;
  registered_at: string;
}
```

- [ ] **Step 2: Replace filters + table.** Use `PRIMARY_STRENGTHS`/`EXPERIENCE_LEVELS` from `@/lib/taxonomy` for the two `Select`s; change query params to `strength`/`experience`. Replace the `skillColor` map keys to the 3 experience levels (drop `professional`). Change headers to `["Name","Email","Category","Experience","Source","Score"]`. The Category cell shows `normalized_strength ?? strength_other ?? primary_strength` and, on click, becomes a `Select` (from `PRIMARY_STRENGTHS` minus `other`) that PATCHes `/api/v1/events/${eventId}/participants/${p.id}` with `{ normalized_strength }` then revalidates SWR (`mutate`). The Source cell shows `strength_source` (preset/ai/fallback/manual) so the organizer sees where a category came from.

```tsx
const experienceColor: Record<string, string> = {
  beginner: "bg-green-100 text-green-800",
  intermediate: "bg-blue-100 text-blue-800",
  advanced: "bg-purple-100 text-purple-800",
};

async function saveCategory(eventId: string, id: string, normalized_strength: string, token: string) {
  await fetchAPI(`/api/v1/events/${eventId}/participants/${id}`, {
    method: "PATCH", body: { normalized_strength }, token,
  });
}
```

- [ ] **Step 3: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/attendees/attendees-table.tsx
git commit -m "feat(ui): attendees category column with inline override + source"
```

---

## Phase 10 — Create-event dialog: prominent description

**Files:**
- Modify: `frontend/components/events/create-event-dialog.tsx`

- [ ] **Step 1: Promote the description field.** Keep it optional but move it directly under the title, make it a multi-line control (textarea styling), and add helper text under the label: `"Describe the event — this helps SquadSync group attendees more accurately."` Use the existing `Input` or a `textarea` styled with the project's input classes. Do not change the POST payload shape (description already supported).

- [ ] **Step 2: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/events/create-event-dialog.tsx
git commit -m "feat(ui): make event description prominent (feeds categorization)"
```

---

## Phase 11 — Remove the dead notification bell

**Files:**
- Modify: `frontend/components/layout/topbar.tsx`

- [ ] **Step 1: Remove the bell.** Delete the `<Button variant="ghost" size="icon"><Bell …/></Button>` block (lines 37–39 of the current file) and remove `Bell` from the `lucide-react` import. Leave the account dropdown intact.

- [ ] **Step 2: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean (no unused `Bell` import).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/layout/topbar.tsx
git commit -m "chore(ui): remove non-functional notification bell"
```

---

## Phase 12 — Config, docs, and full verification

**Files:**
- Modify: `render.yaml`
- Modify: `DEPLOYMENT.md`
- Modify: `frontend/app/dashboard/events/[eventId]/configure/page.tsx` and `.../engine/page.tsx` (only if they hard-code dev roles for constraints)

- [ ] **Step 1: Add the API key env** to `render.yaml` under the api service `envVars` (after `PUBLIC_API_URL`):

```yaml
      # Optional: enables AI normalization of free-text "Other" strengths.
      # Unset = deterministic slug fallback (no AI).
      - key: ANTHROPIC_API_KEY
        sync: false
```

Add a row to the env table in `DEPLOYMENT.md` describing `ANTHROPIC_API_KEY` (optional; absence → fallback).

- [ ] **Step 2: Fix any dev-role references in the constraint UI** — read `configure/page.tsx` and `engine/page.tsx`; if they list the old dev roles for `role_constraints`, swap to the universal categories from `@/lib/taxonomy` (the constraint dict keys are now strengths). If they don't reference roles, skip.

- [ ] **Step 3: Full backend suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q`
Expected: all pass.

- [ ] **Step 4: Full frontend checks**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: all clean; build succeeds.

- [ ] **Step 5: Migration end-to-end**

Run: `cd backend && DATABASE_URL="sqlite:///./e2e_mig.db" python -m alembic upgrade head && rm -f e2e_mig.db`
Expected: upgrades to 0003 cleanly.

- [ ] **Step 6: Commit**

```bash
git add render.yaml DEPLOYMENT.md frontend/app/dashboard/events/
git commit -m "chore(deploy): document ANTHROPIC_API_KEY; align constraint UI with strengths"
```

---

## Self-Review (completed by author)

- **Spec coverage:** registration fields (P8), universal set (P0/P8), AI Other-only normalization (P4) + auto-trigger (P5), fallback (P4), persistence/determinism (P1/P3/P4), background + inline override (P6/P9), data model + migration (P1/P2), engine on `normalized_strength` + 3-level (P3), description prominence (P10), bell removal (P11), config/env (P12), tests (every phase + P7). ✅
- **Type consistency:** `normalize_pending`, `_classify`, `override_category`, `compute_composite_score(experience_level)`, `ParticipantCategoryUpdate.normalized_strength`, query params `strength`/`experience`, and frontend `@/lib/taxonomy` values are used identically across phases. ✅
- **Placeholders:** none — code provided for new/changed files; test-only files (test_registration/test_validation/configure page) include explicit, bounded edit instructions with the exact field mappings because their full contents must be read at execution time. ✅
