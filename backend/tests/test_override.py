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
