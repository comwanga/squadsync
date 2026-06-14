import hashlib
import statistics
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.taxonomy import EXPERIENCE_SCORE
from app.models.allocation import AllocationConfig, Allocation
from app.models.event import Event
from app.models.participant import Participant
from app.models.team import Team, TeamMember


class AllocationError(HTTPException):
    """HTTPException subclass whose str() exposes the detail field for pytest.raises(match=...)."""

    def __str__(self) -> str:
        return str(self.detail)


def compute_composite_score(experience_level: str) -> float:
    """Single-dimension experience score (1.0-3.0).

    Maps cleanly onto the engine's passes: advanced (3.0) = anchor,
    intermediate (2.0), beginner (1.0) = fill.
    """
    return EXPERIENCE_SCORE[experience_level]


def run_allocation(db: Session, event_id: UUID, config: AllocationConfig) -> Allocation:
    # Deterministic base ordering so ties break the same way on every run / DB engine.
    participants = (
        db.query(Participant)
        .filter(Participant.event_id == event_id)
        .order_by(Participant.id)
        .all()
    )
    if not participants:
        raise AllocationError(status_code=400, detail="No participants to allocate")

    event = db.query(Event).filter(Event.id == event_id).first()
    n_teams = event.team_count
    if n_teams > len(participants):
        raise AllocationError(status_code=400, detail="Fewer participants than teams")

    # Recompute composite scores
    for p in participants:
        p.composite_score = compute_composite_score(p.experience_level)
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
        key=lambda x: (-x.composite_score, str(x.id)),
    )
    for i, anchor in enumerate(anchors):
        idx = i % n_teams
        buckets[idx]["members"].append(anchor)
        buckets[idx]["score_sum"] += anchor.composite_score
        buckets[idx]["roles"].append(anchor.normalized_strength or anchor.primary_strength)
        unassigned.discard(anchor.id)

    # Pass 2: Intermediates (1.5 <= Sc < 3.0)
    intermediates = sorted(
        [p for p in participants if p.id in unassigned and 1.5 <= p.composite_score < 3.0],
        key=lambda x: (-x.composite_score, str(x.id)),
    )
    for p in intermediates:
        idx = min(range(n_teams), key=lambda i: buckets[i]["score_sum"])
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.normalized_strength or p.primary_strength)
        unassigned.discard(p.id)

    # Pass 3: Role constraint enforcement
    role_constraints: dict = config.role_constraints or {}
    constraint_warnings: dict = {}
    remaining_pool = [p for p in participants if p.id in unassigned]

    def _take_from_pool(role: str):
        """Pull an as-yet-unassigned participant with the given role, if any."""
        for idx, p in enumerate(remaining_pool):
            if (p.normalized_strength or p.primary_strength) == role:
                return remaining_pool.pop(idx)
        return None

    def _relocate_from_surplus(role: str, min_count: int, needy_idx: int) -> bool:
        """Move a participant with `role` from a team that has it to spare.

        A donor can spare one only if doing so keeps the donor at/above its own
        requirement for that role (constraints are global, so the donor's
        requirement is the same min_count) and leaves the donor non-empty.
        """
        for j, donor in enumerate(buckets):
            if j == needy_idx:
                continue
            if donor["roles"].count(role) > min_count and len(donor["members"]) > 1:
                for k, member in enumerate(donor["members"]):
                    if (member.normalized_strength or member.primary_strength) == role:
                        donor["members"].pop(k)
                        donor["roles"].remove(role)
                        donor["score_sum"] -= member.composite_score
                        buckets[needy_idx]["members"].append(member)
                        buckets[needy_idx]["roles"].append(member.normalized_strength or member.primary_strength)
                        buckets[needy_idx]["score_sum"] += member.composite_score
                        return True
        return False

    if role_constraints:
        for i, bucket in enumerate(buckets):
            team_key = f"team_{i + 1:02d}"
            for role, min_count in role_constraints.items():
                while bucket["roles"].count(role) < min_count:
                    # 1) Prefer an unassigned participant with this role.
                    c = _take_from_pool(role)
                    if c is not None:
                        bucket["members"].append(c)
                        bucket["score_sum"] += c.composite_score
                        bucket["roles"].append(c.normalized_strength or c.primary_strength)
                        unassigned.discard(c.id)
                        continue
                    # 2) Otherwise rebalance the role from a team that has a surplus.
                    if _relocate_from_surplus(role, min_count, i):
                        continue
                    # 3) Genuinely unsatisfiable — one warning per still-missing slot.
                    shortage = min_count - bucket["roles"].count(role)
                    constraint_warnings.setdefault(team_key, []).extend(
                        [f"missing: {role}"] * shortage
                    )
                    break

    # Pass 4: Beginner fill
    remaining = [p for p in participants if p.id in unassigned]
    for p in remaining:
        idx = min(range(n_teams), key=lambda i: len(buckets[i]["members"]))
        buckets[idx]["members"].append(p)
        buckets[idx]["score_sum"] += p.composite_score
        buckets[idx]["roles"].append(p.normalized_strength or p.primary_strength)

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
