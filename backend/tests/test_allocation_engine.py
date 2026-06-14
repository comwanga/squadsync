import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.models.event import Event
from app.models.participant import Participant
from app.models.allocation import AllocationConfig, Allocation
from app.models.team import Team, TeamMember
from app.models.user import User
from app.services.allocation_engine import run_allocation, compute_composite_score
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


def add_participant(db, event_id, skill, role, years):
    p = Participant(
        event_id=event_id,
        name=f"{role}-{skill}",
        email=f"{role}{skill}{uuid.uuid4().hex[:4]}@test.com",
        skill_level=skill,
        role=role,
        years_experience=years,
        tech_stack=[],
        interests=[],
    )
    db.add(p)
    db.commit()
    return p


# Composite score formula tests
def test_score_beginner_no_experience():
    assert compute_composite_score(0, "beginner", 0.5, 0.5) == pytest.approx(1.0)


def test_score_professional_senior():
    # E=4 (7+y), K=4 (professional): Sc = 0.5*4 + 0.5*4 = 4.0
    assert compute_composite_score(10, "professional", 0.5, 0.5) == pytest.approx(4.0)


def test_score_advanced_midlevel():
    # E=3 (4-6y), K=3 (advanced): Sc = 0.5*3 + 0.5*3 = 3.0
    assert compute_composite_score(5, "advanced", 0.5, 0.5) == pytest.approx(3.0)


def test_score_custom_weights():
    # E=2, K=1, w_exp=0.8, w_skill=0.2: Sc = 0.8*2 + 0.2*1 = 1.8
    assert compute_composite_score(2, "beginner", 0.8, 0.2) == pytest.approx(1.8)


# Engine tests
def test_allocation_creates_correct_team_count(db, event, config):
    for i in range(9):
        add_participant(db, event.id, "intermediate", "frontend", 3)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    assert len(teams) == 3


def test_allocation_all_participants_assigned(db, event, config):
    for _ in range(9):
        add_participant(db, event.id, "beginner", "backend", 0)
    allocation = run_allocation(db, event.id, config)
    assigned = db.query(TeamMember).join(Team).filter(Team.allocation_id == allocation.id).count()
    assert assigned == 9


def test_allocation_anchors_distributed(db, event, config):
    # 3 professionals -> one per team
    for _ in range(3):
        add_participant(db, event.id, "professional", "fullstack", 10)
    for _ in range(6):
        add_participant(db, event.id, "beginner", "frontend", 0)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    # Each team should have exactly 1 professional anchor + 2 beginners
    for team in teams:
        members = db.query(Participant).join(TeamMember, Participant.id == TeamMember.participant_id)\
            .filter(TeamMember.team_id == team.id).all()
        pro_count = sum(1 for m in members if m.skill_level == "professional")
        assert pro_count == 1


def test_allocation_role_constraint_warning(db, event, config):
    # Require frontend but provide none
    config.role_constraints = {"frontend": 1}
    db.commit()
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings  # should have warnings


def test_allocation_role_constraint_satisfied(db, event, config):
    config.role_constraints = {"frontend": 1}
    db.commit()
    # One frontend per team
    for _ in range(3):
        add_participant(db, event.id, "intermediate", "frontend", 3)
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    assert allocation.constraint_warnings == {}


def test_allocation_no_participants_raises(db, event, config):
    from fastapi import HTTPException
    with pytest.raises(HTTPException, match="No participants"):
        run_allocation(db, event.id, config)


def test_allocation_more_teams_than_participants_raises(db, event, config):
    from fastapi import HTTPException
    add_participant(db, event.id, "beginner", "frontend", 0)  # only 1, but 3 teams
    with pytest.raises(HTTPException, match="Fewer participants"):
        run_allocation(db, event.id, config)


def test_fairness_scores_stored(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
    allocation = run_allocation(db, event.id, config)
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    for team in teams:
        assert team.fairness_score is not None
        assert 0 <= team.fairness_score <= 100


def test_snapshot_hash_deterministic(db, event, config):
    for _ in range(6):
        add_participant(db, event.id, "intermediate", "backend", 3)
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
    # Mixed skills/roles/experience to exercise every pass and tie-breaking.
    add_participant(db, event.id, "professional", "backend", 10)
    add_participant(db, event.id, "advanced", "frontend", 5)
    add_participant(db, event.id, "intermediate", "ux", 2)
    add_participant(db, event.id, "intermediate", "backend", 3)
    add_participant(db, event.id, "beginner", "frontend", 0)
    add_participant(db, event.id, "beginner", "devops", 1)
    add_participant(db, event.id, "advanced", "fullstack", 6)
    add_participant(db, event.id, "beginner", "mobile", 0)
    add_participant(db, event.id, "intermediate", "product", 2)

    a1 = run_allocation(db, event.id, config)
    a2 = run_allocation(db, event.id, config)
    assert _memberships(db, a1.id) == _memberships(db, a2.id)


def test_role_constraint_relocates_from_surplus(db, owner):
    # Two teams, one backend required per team. The two backends both get anchored
    # onto team 0 by the round-robin, starving team 1 — which the engine must fix
    # by relocating a surplus backend rather than emitting a false warning.
    e = Event(owner_id=owner.id, title="Reloc", team_count=2, registration_slug="reloc", status="active")
    db.add(e)
    db.commit()
    cfg = AllocationConfig(event_id=e.id, weight_experience=0.5, weight_skill=0.5,
                           role_constraints={"backend": 1})
    db.add(cfg)
    db.commit()

    add_participant(db, e.id, "professional", "backend", 10)  # Sc 4.0 (anchor)
    add_participant(db, e.id, "professional", "frontend", 5)  # Sc 3.5 (anchor)
    add_participant(db, e.id, "advanced", "backend", 5)       # Sc 3.0 (anchor)

    allocation = run_allocation(db, e.id, cfg)

    # No team should be reported as missing a backend.
    assert allocation.constraint_warnings == {}
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    assert len(teams) == 2
    for t in teams:
        roles = [
            p.role for p in db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == t.id).all()
        ]
        assert "backend" in roles
