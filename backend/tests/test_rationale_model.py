import uuid
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.team import Team
from app.models.user import User


def _allocation(db, snapshot_hash):
    user = User(pubkey=uuid.uuid4().hex * 2)
    db.add(user)
    db.flush()
    event = Event(owner_id=user.id, title="Rationale model", team_count=2,
                  registration_slug=uuid.uuid4().hex[:8])
    db.add(event)
    db.flush()
    allocation = Allocation(event_id=event.id, snapshot_hash=snapshot_hash, status="draft",
                            constraint_warnings={})
    db.add(allocation)
    db.flush()
    return allocation


def test_team_rationale_persists_json(db):
    alloc = _allocation(db, "h")
    team = Team(allocation_id=alloc.id, name="Team 01",
                rationale={"title": "Build squad", "summary": "Strong delivery.",
                           "strengths": ["2 advanced engineers"], "gaps": ["limited outreach"]})
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.rationale["title"] == "Build squad"
    assert team.rationale["gaps"] == ["limited outreach"]
    assert team.rationale["summary"] == "Strong delivery."
    assert team.rationale["strengths"] == ["2 advanced engineers"]


def test_team_rationale_defaults_none(db):
    alloc = _allocation(db, "h2")
    team = Team(allocation_id=alloc.id, name="Team 02")
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.rationale is None
