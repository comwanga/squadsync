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
