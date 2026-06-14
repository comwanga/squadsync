import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.event import Event
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember
from app.models.user import User
from app.services.allocation_engine import run_allocation
import uuid

TEST_DB = "sqlite:///./test_engine.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
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


@pytest.fixture
def owner(db):
    u = User(pubkey="a" * 64)
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def event(db, owner):
    e = Event(owner_id=owner.id, title="Test Event", team_count=3, registration_slug="testslug", status="active")
    db.add(e)
    db.commit()
    return e


@pytest.fixture
def config(db, event):
    c = AllocationConfig(event_id=event.id, weight_experience=0.5, weight_skill=0.5, role_constraints={})
    db.add(c)
    db.commit()
    return c


def add_participant(db, event_id, experience, strength):
    """Add a preset-strength participant. `strength` is a universal category value."""
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


# Engine tests
def test_allocation_creates_correct_team_count(db, event, config):
    for _ in range(9):
        add_participant(db, event.id, "intermediate", "technical")
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    assert len(teams) == 3


def test_allocation_all_participants_assigned(db, event, config):
    for _ in range(9):
        add_participant(db, event.id, "beginner", "technical")
    allocation = run_allocation(db, event.id, config)
    assigned = db.query(TeamMember).join(Team).filter(Team.allocation_id == allocation.id).count()
    assert assigned == 9


def test_allocation_anchors_distributed(db, event, config):
    # 3 advanced anchors -> one per team
    for _ in range(3):
        add_participant(db, event.id, "advanced", "technical")
    for _ in range(6):
        add_participant(db, event.id, "beginner", "technical")
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    # Each team should have exactly 1 advanced anchor + 2 beginners
    for team in teams:
        members = db.query(Participant).join(TeamMember, Participant.id == TeamMember.participant_id)\
            .filter(TeamMember.team_id == team.id).all()
        adv_count = sum(1 for m in members if m.experience_level == "advanced")
        assert adv_count == 1


def test_allocation_strength_constraint_warning(db, event, config):
    # Require technical but provide none
    config.role_constraints = {"technical": 1}
    db.commit()
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "design")
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings  # should have warnings


def test_allocation_strength_constraint_satisfied(db, event, config):
    config.role_constraints = {"technical": 1}
    db.commit()
    # One technical per team
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "technical")
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "design")
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings == {}


def test_allocation_no_participants_raises(db, event, config):
    from fastapi import HTTPException
    with pytest.raises(HTTPException, match="No participants"):
        run_allocation(db, event.id, config)


def test_allocation_more_teams_than_participants_raises(db, event, config):
    from fastapi import HTTPException
    add_participant(db, event.id, "beginner", "technical")  # only 1, but 3 teams
    with pytest.raises(HTTPException, match="Fewer participants"):
        run_allocation(db, event.id, config)


def test_fairness_scores_stored(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "technical")
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        assert team.fairness_score is not None
        assert 0 <= team.fairness_score <= 100


def test_snapshot_hash_deterministic(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "technical")
    a1 = run_allocation(db, event.id, config)
    # Run again (same participants)
    a2 = run_allocation(db, event.id, config)
    assert a1.snapshot_hash == a2.snapshot_hash


def _memberships(db, allocation_id):
    """Return team membership as a set of frozensets of participant ids (order-free)."""
    teams = db.query(Team).filter(Team.allocation_id == allocation_id).all()
    result = []
    for t in teams:
        members = db.query(TeamMember).filter(TeamMember.team_id == t.id).all()
        result.append(frozenset(str(m.participant_id) for m in members))
    return set(result)


def test_allocation_assignments_are_deterministic(db, event, config):
    # Mixed experience/strengths to exercise every pass and tie-breaking.
    add_participant(db, event.id, "advanced", "technical")
    add_participant(db, event.id, "advanced", "design")
    add_participant(db, event.id, "intermediate", "design")
    add_participant(db, event.id, "intermediate", "technical")
    add_participant(db, event.id, "beginner", "technical")
    add_participant(db, event.id, "beginner", "coordination")
    add_participant(db, event.id, "advanced", "technical")
    add_participant(db, event.id, "beginner", "technical")
    add_participant(db, event.id, "intermediate", "planning")

    a1 = run_allocation(db, event.id, config)
    a2 = run_allocation(db, event.id, config)
    assert _memberships(db, a1.id) == _memberships(db, a2.id)


def test_strength_constraint_relocates_from_surplus(db, owner):
    # Two teams, one technical required per team. With explicit ascending ids the
    # anchor tie-break (-score, str(id)) orders them a,b,c; round-robin (i%2) puts
    # both technical anchors (a,c) on team 0 and the design anchor (b) on team 1,
    # starving team 1 — which the engine must fix by relocating a surplus technical
    # rather than emitting a false warning.
    e = Event(owner_id=owner.id, title="Reloc", team_count=2, registration_slug="reloc", status="active")
    db.add(e)
    db.commit()
    cfg = AllocationConfig(event_id=e.id, weight_experience=0.5, weight_skill=0.5,
                           role_constraints={"technical": 1})
    db.add(cfg)
    db.commit()

    def add(strength, n):
        p = Participant(
            id=uuid.UUID(int=n), event_id=e.id, name=f"p{n}", email=f"p{n}@t.com",
            experience_level="advanced", primary_strength=strength,
            normalized_strength=strength, strength_source="preset",
            tech_stack=[], interests=[],
        )
        db.add(p)
        db.commit()

    add("technical", 1)
    add("design", 2)
    add("technical", 3)

    allocation = run_allocation(db, e.id, cfg)

    # No team should be reported as missing a technical member.
    assert allocation.constraint_warnings == {}
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    assert len(teams) == 2
    for t in teams:
        strengths = [
            p.normalized_strength for p in db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == t.id).all()
        ]
        assert "technical" in strengths
