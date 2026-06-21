import uuid
import pytest
from app.models.allocation import Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember
from app.models.user import User
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


def test_generate_swallows_classify_failure(db, monkeypatch):
    _e, alloc, _team = _alloc_with_team(db)
    monkeypatch.setattr(rat.settings, "ANTHROPIC_API_KEY", "k")

    def _boom(event, payloads):
        raise RuntimeError("model down")

    monkeypatch.setattr(rat, "_classify", _boom)
    # best-effort: returns an empty mapping and commits without raising
    assert rat.generate(db, alloc) == {}
