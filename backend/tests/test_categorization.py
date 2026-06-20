from unittest.mock import patch
import uuid

from app.core.database import Base
from app.core.taxonomy import CONCRETE_STRENGTHS
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


def test_ai_maps_other_to_category(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "test-key")  # enable the AI branch
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        counts = cat.normalize_pending(db, e.id)
    assert counts == {"ai": 1, "fallback": 0}
    db.refresh(p)
    assert p.normalized_strength == "domain_expert"
    assert p.strength_source == "ai"


def test_fallback_when_no_key(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", None)
    counts = cat.normalize_pending(db, e.id)
    assert counts == {"ai": 0, "fallback": 1}
    db.refresh(p)
    assert p.normalized_strength  # slug of "Agronomist"
    assert p.strength_source == "fallback"


def _add_other(db, event_id, n, prefix):
    for i in range(n):
        db.add(Participant(
            event_id=event_id, name=f"{prefix}{i}", email=f"{prefix}{i}@t.com",
            primary_strength="other", strength_other=f"role {i}",
            experience_level="beginner", strength_source="preset",
            composite_score=1.0, tech_stack=[], interests=[],
        ))
    db.commit()


def test_build_request_has_cached_system_and_raised_max_tokens(db):
    e, p = _event_with_other(db)
    req = cat._build_request(e, [p])
    # Static taxonomy + instructions live in a cacheable system block.
    assert isinstance(req["system"], list)
    assert req["system"][0]["cache_control"]["type"] == "ephemeral"
    # Headroom so a full batch's tool output can't truncate (was 1024).
    assert req["max_tokens"] >= 2048
    # The tool still constrains output to the concrete categories.
    enum = req["tools"][0]["input_schema"]["properties"]["assignments"]["items"]["properties"]["category"]["enum"]
    assert enum == list(CONCRETE_STRENGTHS)
    # The participant and an abstention instruction both reach the model.
    user_text = req["messages"][0]["content"]
    assert str(p.id) in user_text
    blob = (req["system"][0]["text"] + user_text).lower()
    assert "omit" in blob


def test_parse_assignments_keeps_valid_drops_invalid():
    class Block:
        type = "tool_use"
        input = {"assignments": [
            {"id": "a", "category": "research"},
            {"id": "b", "category": "not_a_category"},  # outside the taxonomy -> dropped
        ]}
    assert cat._parse_assignments([Block()]) == {"a": "research"}


def test_normalize_batches_large_pending(db, monkeypatch):
    e, _ = _event_with_other(db)  # 1 existing "other"
    extra = cat._BATCH_SIZE + 4
    _add_other(db, e.id, extra, "x")
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "k")
    sizes = []

    def fake_classify(event, parts):
        sizes.append(len(parts))
        return {str(pp.id): "research" for pp in parts}

    monkeypatch.setattr(cat, "_classify", fake_classify)
    counts = cat.normalize_pending(db, e.id)
    assert counts["ai"] == extra + 1          # everyone categorized, none lost
    assert len(sizes) >= 2                     # split across batches
    assert max(sizes) <= cat._BATCH_SIZE       # no batch exceeds the cap


def test_normalize_isolates_batch_failure(db, monkeypatch):
    e, _ = _event_with_other(db)  # 1 in batch 2
    _add_other(db, e.id, cat._BATCH_SIZE, "y")  # fills batch 1
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "k")
    calls = {"n": 0}

    def flaky(event, parts):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")  # only the first batch fails
        return {str(pp.id): "research" for pp in parts}

    monkeypatch.setattr(cat, "_classify", flaky)
    counts = cat.normalize_pending(db, e.id)
    # A single failed batch falls back locally; the rest still get AI — never all-or-nothing.
    assert counts["ai"] >= 1 and counts["fallback"] >= 1


def test_manual_override_not_touched(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "test-key")
    p.normalized_strength = "research"; p.strength_source = "manual"; db.commit()
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        cat.normalize_pending(db, e.id)
    db.refresh(p)
    assert p.normalized_strength == "research"  # untouched
