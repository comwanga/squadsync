import hashlib
import statistics
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.allocation import AllocationConfig, Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember

_EXP_MAP = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 3}
_SKILL_MAP = {"beginner": 1, "intermediate": 2, "advanced": 3, "professional": 4}


class AllocationError(HTTPException):
    """HTTPException subclass whose str() exposes the detail field for pytest.raises(match=...)."""

    def __str__(self) -> str:
        return str(self.detail)


def compute_composite_score(years_exp: int, skill_level: str, w_exp: float = 0.5, w_skill: float = 0.5) -> float:
    e = 4 if years_exp >= 7 else _EXP_MAP.get(years_exp, 1)
    k = _SKILL_MAP[skill_level]
    return round((w_exp * e) + (w_skill * k), 4)


def run_allocation(db: Session, event_id: UUID, config: AllocationConfig) -> Allocation:
    participants = db.query(Participant).filter(Participant.event_id == event_id).all()
    if not participants:
        raise AllocationError(status_code=400, detail="No participants to allocate")

    event = db.query(Event).filter(Event.id == event_id).first()
    n_teams = event.team_count
    if n_teams > len(participants):
        raise AllocationError(status_code=400, detail="Fewer participants than teams")

    # Recompute composite scores with current weights
    for p in participants:
        p.composite_score = compute_composite_score(
            p.years_experience, p.skill_level,
            config.weight_experience, config.weight_skill,
        )
    db.flush()

    # Snapshot hash
    sorted_ids = sorted([str(p.id) for p in participants])
    snapshot_hash = hashlib.sha256(",".join(sorted_ids).encode()).hexdigest()

    # Team buckets
    buckets: list[dict] = [
        {"members": [], "score_sum": 0.0, "roles": []}
        for _ in range(n_teams)
    ]
    unassigned: set = {p.id for p in participants}

    # Pass 1: Anchors (Sc >= 3.0)
    anchors = sorted(
        [p for p in participants if p.composite_score >= 3.0],
        key=lambda x: -x.composite_score,
    )
    for i, anchor in enumerate(anchors):
        idx = i % n_teams
        buckets[idx]["members"].append(anchor)
        buckets[idx]["score_sum"] += anchor.composite_score
        buckets[idx]["roles"].append(anchor.role)
        unassigned.discard(anchor.id)

    # Pass 2: Intermediates (1.5 <= Sc < 3.0)
    intermediates = sorted(
        [p for p in participants if p.id in unassigned and 1.5 <= p.composite_score < 3.0],
        key=lambda x: -x.composite_score,
    )
    for p in intermediates:
        idx = min(range(n_teams), key=lambda i: buckets[i]["score_sum"])
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.role)
        unassigned.discard(p.id)

    # Pass 3: Role constraint enforcement
    role_constraints: dict = config.role_constraints or {}
    constraint_warnings: dict = {}
    remaining_pool = [p for p in participants if p.id in unassigned]

    if role_constraints:
        for i, bucket in enumerate(buckets):
            team_key = f"team_{i + 1:02d}"
            for role, min_count in role_constraints.items():
                current = bucket["roles"].count(role)
                needed = min_count - current
                for _ in range(needed):
                    candidates = [p for p in remaining_pool if p.role == role]
                    if candidates:
                        c = candidates[0]
                        remaining_pool.remove(c)
                        bucket["members"].append(c)
                        bucket["score_sum"] += c.composite_score
                        bucket["roles"].append(c.role)
                        unassigned.discard(c.id)
                    else:
                        constraint_warnings.setdefault(team_key, []).append(f"missing: {role}")

    # Pass 4: Beginner fill
    remaining = [p for p in participants if p.id in unassigned]
    for p in remaining:
        idx = min(range(n_teams), key=lambda i: len(buckets[i]["members"]))
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.role)

    # Compute global skill scores
    score_sums = [b["score_sum"] for b in buckets]
    mean_sc = statistics.mean(score_sums) if score_sums else 1.0
    std_sc = statistics.stdev(score_sums) if len(score_sums) > 1 else 0.0
    skill_score = max(0.0, 100 * (1 - std_sc / mean_sc)) if mean_sc else 0.0

    total_constraints = sum(n_teams * v for v in role_constraints.values()) if role_constraints else 0
    total_warnings = sum(len(v) for v in constraint_warnings.values())
    fulfilled = total_constraints - total_warnings
    role_balance_score = (100 * fulfilled / total_constraints) if total_constraints else 100.0
    fairness_score = (skill_score * 0.6) + (role_balance_score * 0.4)

    # Persist
    allocation = Allocation(
        event_id=event_id,
        snapshot_hash=snapshot_hash,
        status="draft",
        constraint_warnings=constraint_warnings,
    )
    db.add(allocation)
    db.flush()

    for i, bucket in enumerate(buckets):
        team = Team(
            allocation_id=allocation.id,
            name=f"Team {i + 1:02d}",
            skill_score=round(skill_score, 1),
            role_balance_score=round(role_balance_score, 1),
            fairness_score=round(fairness_score, 1),
        )
        db.add(team)
        db.flush()
        for member in bucket["members"]:
            db.add(TeamMember(team_id=team.id, participant_id=member.id))

    db.commit()
    db.refresh(allocation)
    return allocation
