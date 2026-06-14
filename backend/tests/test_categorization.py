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


def test_ai_maps_other_to_category(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "test-key")  # enable the AI branch
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


def test_manual_override_not_touched(db, monkeypatch):
    e, p = _event_with_other(db)
    monkeypatch.setattr(cat.settings, "ANTHROPIC_API_KEY", "test-key")
    p.normalized_strength = "research"; p.strength_source = "manual"; db.commit()
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        cat.normalize_pending(db, e.id)
    db.refresh(p)
    assert p.normalized_strength == "research"  # untouched
