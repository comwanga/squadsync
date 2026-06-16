# Manual Allocation Control (Move + Regenerate) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let organizers correct a draft allocation — move a participant between teams and regenerate a different valid allocation — with team scores recomputed honestly. Publishing locks it.

**Architecture:** Extract the engine's scoring into a pure `score_teams` reused by generation and by move-recompute; add a seeded tiebreak so regenerate yields a different valid allocation; the allocate endpoint reseeds + replaces the prior draft; a new move endpoint reassigns membership (draft-only) and recomputes scores; the results UI gains a per-member move `<select>` and a Regenerate button (draft only).

**Tech Stack:** FastAPI + SQLAlchemy + pytest; Next.js 16 + SWR + Vitest.

**Spec:** `docs/superpowers/specs/2026-06-16-manual-allocation-control-design.md`
**Branch:** `feat/manual-allocation-control` (off `main`).

---

## Phase 1 — Extract `score_teams` (pure) and refactor the engine to use it

**Files:**
- Modify: `backend/app/services/allocation_engine.py`
- Test: `backend/tests/test_score_teams.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_score_teams.py
from collections import Counter
from app.services.allocation_engine import score_teams


def test_even_teams_high_skill():
    skill, role, fair = score_teams([3.0, 3.0, 3.0], [Counter(), Counter(), Counter()], {})
    assert skill == 100.0           # zero variance
    assert role == 100.0            # no constraints
    assert fair == 100.0


def test_lopsided_teams_lower_skill():
    skill, _, _ = score_teams([6.0, 1.0], [Counter(), Counter()], {})
    assert 0.0 <= skill < 100.0


def test_role_balance_partial_fulfillment():
    # 2 teams, require 1 "technical" each; only team A has one.
    counts = [Counter({"technical": 1}), Counter()]
    _, role, _ = score_teams([2.0, 2.0], counts, {"technical": 1})
    assert role == 50.0             # 1 of 2 required slots filled

def test_role_balance_full():
    counts = [Counter({"technical": 1}), Counter({"technical": 1})]
    _, role, _ = score_teams([2.0, 2.0], counts, {"technical": 1})
    assert role == 100.0
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd backend && python -m pytest tests/test_score_teams.py -q`
Expected: FAIL — `score_teams` not defined.

- [ ] **Step 3: Add `score_teams` to `allocation_engine.py`** (near the top, after `compute_composite_score`):

```python
def score_teams(team_score_sums, team_strength_counts, role_constraints):
    """Pure team-quality scoring, shared by generation and post-edit recompute.

    Returns (skill_score, role_balance_score, fairness_score), unrounded (0-100).
    - skill: 100*(1 - stdev/mean) of team score-sums (even = high).
    - role_balance: % of required (strength, count) slots filled across teams.
    - fairness: 0.6*skill + 0.4*role_balance.
    """
    mean_sc = statistics.mean(team_score_sums) if team_score_sums else 1.0
    std_sc = statistics.stdev(team_score_sums) if len(team_score_sums) > 1 else 0.0
    skill_score = max(0.0, 100 * (1 - std_sc / mean_sc)) if mean_sc else 0.0

    n_teams = len(team_score_sums)
    total_required = sum(n_teams * v for v in role_constraints.values()) if role_constraints else 0
    fulfilled = 0
    for counts in team_strength_counts:
        for role, req in role_constraints.items():
            fulfilled += min(counts.get(role, 0), req)
    role_balance_score = (100 * fulfilled / total_required) if total_required else 100.0

    fairness_score = (skill_score * 0.6) + (role_balance_score * 0.4)
    return skill_score, role_balance_score, fairness_score
```

Add `from collections import Counter` at the top of the file (with the other imports).

- [ ] **Step 4: Refactor `run_allocation` to use it.** Replace the "Compute global skill scores" block (the `score_sums`/`mean_sc`/`std_sc`/`skill_score`/`total_constraints`/`role_balance_score`/`fairness_score` lines) with:

```python
    # Team scores (shared with post-edit recompute). constraint_warnings above
    # already records shortfalls; score_teams derives the same role balance from counts.
    team_score_sums = [b["score_sum"] for b in buckets]
    team_strength_counts = [Counter(b["roles"]) for b in buckets]
    skill_score, role_balance_score, fairness_score = score_teams(
        team_score_sums, team_strength_counts, role_constraints
    )
```

(The `import statistics` stays; it's now used inside `score_teams`.)

- [ ] **Step 5: Run the new test + the full engine suite**

Run: `cd backend && python -m pytest tests/test_score_teams.py -q`
Expected: 4 passed.
Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_allocation_engine.py -q; rm -f *.db`
Expected: all pass (scores unchanged — `score_teams`'s count-based role balance equals the prior warning-based value).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/allocation_engine.py backend/tests/test_score_teams.py
git commit -m "refactor(engine): extract pure score_teams; reuse in run_allocation"
```

---

## Phase 2 — Seedable tiebreak (enables regenerate)

**Files:**
- Modify: `backend/app/services/allocation_engine.py`
- Test: `backend/tests/test_allocation_engine.py` (add cases)

- [ ] **Step 1: Add the seed helper + param.** In `allocation_engine.py`, add above `run_allocation`:

```python
def _tiebreak(participant_id, seed: int) -> str:
    """Stable tiebreak key. seed=0 preserves insertion-independent id ordering;
    a non-zero seed reshuffles ties to produce a different valid allocation."""
    if seed == 0:
        return str(participant_id)
    return hashlib.sha256(f"{participant_id}:{seed}".encode()).hexdigest()
```

Change the signature to `def run_allocation(db, event_id, config, seed: int = 0) -> Allocation:`.

In the anchors sort and the intermediates sort, replace `str(x.id)` with `_tiebreak(x.id, seed)`:
```python
    anchors = sorted(
        [p for p in participants if p.composite_score >= 3.0],
        key=lambda x: (-x.composite_score, _tiebreak(x.id, seed)),
    )
```
```python
    intermediates = sorted(
        [p for p in participants if p.id in unassigned and 1.5 <= p.composite_score < 3.0],
        key=lambda x: (-x.composite_score, _tiebreak(x.id, seed)),
    )
```

- [ ] **Step 2: Add tests** to `backend/tests/test_allocation_engine.py` (append):

```python
def test_seed_zero_is_deterministic(db, event, config):
    for _ in range(9):
        add_participant(db, event.id, "intermediate", "technical")
    a1 = run_allocation(db, event.id, config, seed=0)
    a2 = run_allocation(db, event.id, config, seed=0)
    assert _memberships(db, a1.id) == _memberships(db, a2.id)


def test_different_seeds_assign_everyone(db, event, config):
    # Distinct names so ordering can differ; every participant assigned exactly once.
    for i in range(9):
        add_participant(db, event.id, "intermediate", "technical")
    a = run_allocation(db, event.id, config, seed=12345)
    from app.models.team import Team, TeamMember
    assigned = db.query(TeamMember).join(Team).filter(Team.allocation_id == a.id).count()
    assert assigned == 9
    teams = db.query(Team).filter(Team.allocation_id == a.id).all()
    assert len(teams) == 3
```

- [ ] **Step 3: Run engine suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_engine.db" SECRET_KEY=test python -m pytest tests/test_allocation_engine.py -q; rm -f *.db`
Expected: all pass (existing tests use default `seed=0`, unchanged).

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/allocation_engine.py backend/tests/test_allocation_engine.py
git commit -m "feat(engine): seedable tiebreak for regenerate"
```

---

## Phase 3 — Allocate endpoint: reseed + replace prior draft

**Files:**
- Modify: `backend/app/api/v1/allocation.py`
- Test: `backend/tests/test_regenerate.py` (new)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_regenerate.py
def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "RG", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def _register(client, slug, n):
    for i, s in enumerate(["technical", "design", "planning", "coordination"][:n]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})


def test_regenerate_replaces_draft(client, auth_headers):
    e = _active_event(client, auth_headers); _register(client, e["registration_slug"], 4)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    allocs = client.get(f"/api/v1/events/{e['id']}/allocations", headers=auth_headers).json()
    assert len([a for a in allocs if a["status"] == "draft"]) == 1


def test_regenerate_preserves_published(client, auth_headers):
    e = _active_event(client, auth_headers); _register(client, e["registration_slug"], 4)
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    allocs = client.get(f"/api/v1/events/{e['id']}/allocations", headers=auth_headers).json()
    assert any(x["id"] == a["id"] and x["status"] == "published" for x in allocs)
    assert len([x for x in allocs if x["status"] == "draft"]) == 1
```

- [ ] **Step 2: Run, expect FAIL** (today each allocate makes a new draft → 2 drafts)

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_regenerate.py -q; rm -f *.db`
Expected: `test_regenerate_replaces_draft` FAILS (2 drafts).

- [ ] **Step 3: Add cleanup + reseed in `allocation.py`.** Add imports at the top:

```python
import random
from app.models.team import Team, TeamMember
```

Add a helper above the routes:

```python
def _delete_draft_allocations(db: Session, event_id: UUID) -> None:
    """Remove the event's unpublished draft allocations (+ their teams/members)
    so 'Regenerate' replaces the draft rather than piling up. Published ones stay."""
    draft_ids = [
        a.id for a in db.query(Allocation).filter(
            Allocation.event_id == event_id, Allocation.status == "draft"
        ).all()
    ]
    if not draft_ids:
        return
    team_ids = [t.id for t in db.query(Team).filter(Team.allocation_id.in_(draft_ids)).all()]
    if team_ids:
        db.query(TeamMember).filter(TeamMember.team_id.in_(team_ids)).delete(synchronize_session=False)
    db.query(Team).filter(Team.allocation_id.in_(draft_ids)).delete(synchronize_session=False)
    db.query(Allocation).filter(Allocation.id.in_(draft_ids)).delete(synchronize_session=False)
    db.commit()
```

In the `allocate` route, replace the `allocation = run_allocation(db, event_id, config)` line with:

```python
    normalize_pending(db, event_id)
    _delete_draft_allocations(db, event_id)
    allocation = run_allocation(db, event_id, config, seed=random.randint(1, 2**31 - 1))
```

(`normalize_pending` import already present. Note `Team`/`TeamMember` may already be imported in this module — if so, don't duplicate.)

- [ ] **Step 4: Run the regenerate tests + full suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_regenerate.py -q; rm -f *.db`
Expected: 2 passed.
Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/allocation.py backend/tests/test_regenerate.py
git commit -m "feat(allocate): reseed + replace prior draft on regenerate"
```

---

## Phase 4 — Move endpoint (draft-only) + score recompute

**Files:**
- Modify: `backend/app/schemas/allocation.py` (add `MemberMove`)
- Modify: `backend/app/services/allocation_engine.py` (add `move_participant`)
- Modify: `backend/app/api/v1/allocation.py` (add route)
- Test: `backend/tests/test_move_member.py` (new)

- [ ] **Step 1: Add the request schema.** In `backend/app/schemas/allocation.py`, add:

```python
class MemberMove(BaseModel):
    team_id: UUID
```

- [ ] **Step 2: Add `move_participant` to `allocation_engine.py`:**

```python
def move_participant(db: Session, allocation: Allocation, participant_id: UUID, target_team_id: UUID) -> None:
    """Reassign a participant to another team within a draft allocation, then
    recompute the allocation's team scores. Raises 404 on bad team/participant."""
    teams = db.query(Team).filter(Team.allocation_id == allocation.id).all()
    team_ids = {t.id for t in teams}
    if target_team_id not in team_ids:
        raise AllocationError(status_code=404, detail="Target team not in this allocation")

    tm = (
        db.query(TeamMember)
        .filter(TeamMember.participant_id == participant_id, TeamMember.team_id.in_(team_ids))
        .first()
    )
    if tm is None:
        raise AllocationError(status_code=404, detail="Participant not in this allocation")

    tm.team_id = target_team_id
    db.flush()

    # Recompute scores from the new memberships.
    config = db.query(AllocationConfig).filter(AllocationConfig.event_id == allocation.event_id).first()
    role_constraints = (config.role_constraints if config else {}) or {}
    team_score_sums, team_strength_counts = [], []
    for team in teams:
        members = (
            db.query(Participant)
            .join(TeamMember, Participant.id == TeamMember.participant_id)
            .filter(TeamMember.team_id == team.id)
            .all()
        )
        team_score_sums.append(sum(m.composite_score or 0.0 for m in members))
        team_strength_counts.append(Counter((m.normalized_strength or m.primary_strength) for m in members))
    skill_score, role_balance_score, fairness_score = score_teams(
        team_score_sums, team_strength_counts, role_constraints
    )
    for team in teams:
        team.skill_score = round(skill_score, 1)
        team.role_balance_score = round(role_balance_score, 1)
        team.fairness_score = round(fairness_score, 1)
    db.commit()
```

- [ ] **Step 3: Add the route to `allocation.py`.** Add `MemberMove` to the schema import line, then add:

```python
from app.services.allocation_engine import run_allocation, move_participant
```
(merge with the existing `run_allocation` import). Add the route:

```python
@router.patch("/{allocation_id}/members/{participant_id}", response_model=AllocationOut)
def move_member(
    allocation_id: UUID,
    participant_id: UUID,
    req: MemberMove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = assert_allocation_organizer(db, allocation_id, current_user.id)
    if allocation.status != "draft":
        raise HTTPException(status_code=409, detail="Allocation is published; teams are locked")
    move_participant(db, allocation, participant_id, req.team_id)
    return _build_allocation_out(db, allocation)
```

`assert_allocation_organizer` is already imported. Update the `schemas.allocation` import to include `MemberMove`.

- [ ] **Step 4: Write the test**

```python
# backend/tests/test_move_member.py
import pytest
from coincurve import PrivateKey
from tests.conftest import make_nostr_event


@pytest.fixture
def other_headers(client):
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(pk)})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _alloc(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "MV", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    return e, a


def _members(team):
    return {m["id"] for m in team["members"]}


def test_move_reassigns_member(client, auth_headers):
    _, a = _alloc(client, auth_headers)
    src, dst = a["teams"][0], a["teams"][1]
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=auth_headers, json={"team_id": dst["id"]})
    assert res.status_code == 200
    body = res.json()
    by_id = {t["id"]: t for t in body["teams"]}
    assert pid not in _members(by_id[src["id"]])
    assert pid in _members(by_id[dst["id"]])


def test_move_rejected_when_published(client, auth_headers):
    _, a = _alloc(client, auth_headers)
    client.post(f"/api/v1/events/{a['event_id']}/allocations/{a['id']}/publish", headers=auth_headers)
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=auth_headers, json={"team_id": a["teams"][1]["id"]})
    assert res.status_code == 409


def test_move_requires_organizer(client, auth_headers, other_headers):
    _, a = _alloc(client, auth_headers)
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=other_headers, json={"team_id": a["teams"][1]["id"]})
    assert res.status_code == 403
```

- [ ] **Step 5: Run move tests + full suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_move_member.py -q; rm -f *.db`
Expected: 3 passed.
Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/allocation.py backend/app/services/allocation_engine.py backend/app/api/v1/allocation.py backend/tests/test_move_member.py
git commit -m "feat(allocate): draft-only move endpoint with score recompute"
```

---

## Phase 5 — Frontend hooks

**Files:**
- Modify: `frontend/hooks/use-allocation.ts`

- [ ] **Step 1: Add the hooks.** Append to `frontend/hooks/use-allocation.ts`:

```ts
export async function moveMember(token: string, allocationId: string, participantId: string, teamId: string) {
  return fetchAPI<Allocation>(
    `/api/v1/allocations/${allocationId}/members/${participantId}`,
    { method: "PATCH", body: { team_id: teamId }, token }
  );
}

export async function regenerateAllocation(token: string, eventId: string) {
  // The allocate endpoint reseeds and replaces the draft, so this yields a new draft.
  return runAllocation(token, eventId);
}
```

`fetchAPI`, `runAllocation`, and the `Allocation` type are already in this file.

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/hooks/use-allocation.ts
git commit -m "feat(ui): moveMember + regenerateAllocation hooks"
```

---

## Phase 6 — Results grid: move `<select>` + Regenerate (draft only)

**Files:**
- Modify: `frontend/components/engine/team-card.tsx`
- Modify: `frontend/components/engine/results-grid.tsx`
- Modify: `frontend/app/dashboard/events/[eventId]/engine/page.tsx`

- [ ] **Step 1: Add optional move control to `team-card.tsx`.** Extend the component props and the member list. Change the signature and the `<details>` member `<li>`:

```tsx
export function TeamCard({
  team,
  otherTeams,
  onMove,
}: {
  team: Team;
  otherTeams?: { id: string; name: string }[];
  onMove?: (participantId: string, teamId: string) => void;
}) {
```

In the members list, replace each `<li>` with:

```tsx
            {team.members.map(m => (
              <li key={m.id} className="flex items-center justify-between gap-2">
                <span className="font-medium">{m.name}</span>
                <span className="flex items-center gap-2">
                  <span className="text-muted-foreground capitalize">
                    {(m.normalized_strength ?? "—").replaceAll("_", " ")} · {m.experience_level}
                  </span>
                  {onMove && otherTeams && otherTeams.length > 0 && (
                    <select
                      aria-label={`Move ${m.name} to another team`}
                      defaultValue=""
                      onChange={e => { if (e.target.value) onMove(m.id, e.target.value); }}
                      className="text-xs rounded border border-input bg-background px-1 py-0.5"
                    >
                      <option value="" disabled>Move…</option>
                      {otherTeams.map(t => <option key={t.id} value={t.id}>→ {t.name}</option>)}
                    </select>
                  )}
                </span>
              </li>
            ))}
```

- [ ] **Step 2: Wire move + Regenerate into `results-grid.tsx`.** Add imports:

```tsx
import { publishAllocation, moveMember, regenerateAllocation } from "@/hooks/use-allocation";
import { RefreshCw } from "lucide-react";
```

Add an `onChanged` prop:

```tsx
interface ResultsGridProps {
  allocation: Allocation;
  eventId: string;
  onPublished: () => void;
  onChanged: (a: Allocation) => void;
}

export function ResultsGrid({ allocation, eventId, onPublished, onChanged }: ResultsGridProps) {
```

Add handlers (near `handlePublish`):

```tsx
  const isDraft = allocation.status === "draft";

  const handleMove = async (participantId: string, teamId: string) => {
    if (!session?.accessToken) return;
    try {
      const updated = await moveMember(session.accessToken, allocation.id, participantId, teamId);
      onChanged(updated);
      toast.success("Moved");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Move failed");
    }
  };

  const handleRegenerate = async () => {
    if (!session?.accessToken) return;
    try {
      const a = await regenerateAllocation(session.accessToken, eventId);
      onChanged(a);
      toast.success("Regenerated");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Regenerate failed");
    }
  };
```

Pass move props to each `TeamCard` (replace the `allocation.teams.map(...)` line):

```tsx
        {allocation.teams.map(team => (
          <TeamCard
            key={team.id}
            team={team}
            otherTeams={isDraft ? allocation.teams.filter(t => t.id !== team.id).map(t => ({ id: t.id, name: t.name })) : undefined}
            onMove={isDraft ? handleMove : undefined}
          />
        ))}
```

Add a **Regenerate** button in the draft action row (next to Publish — inside the `allocation.status === "draft"` block, before the Publish button):

```tsx
        {isDraft && (
          <Button variant="outline" onClick={handleRegenerate}>
            <RefreshCw className="mr-2 h-4 w-4" /> Regenerate
          </Button>
        )}
```

- [ ] **Step 3: Pass `onChanged` from the engine page.** In `frontend/app/dashboard/events/[eventId]/engine/page.tsx`, the `<ResultsGrid ... />` already gets `onPublished={handlePublished}`. Add:

```tsx
        <ResultsGrid
          allocation={allocation}
          eventId={eventId}
          onPublished={handlePublished}
          onChanged={handleComplete}
        />
```

(`handleComplete` already does `setFresh(a); mutateAllocations()`.)

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: tsc clean; 0 lint errors (pre-existing react-hooks warning OK); all tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/engine/team-card.tsx frontend/components/engine/results-grid.tsx "frontend/app/dashboard/events/[eventId]/engine/page.tsx"
git commit -m "feat(ui): per-member move select + Regenerate on draft allocation"
```

---

## Phase 7 — Full verification

- [ ] **Step 1: Backend suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 2: Frontend gates + build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: tsc clean; lint no new errors; all tests pass; build succeeds.

- [ ] **Step 3: Commit any fixes** (only if needed)

```bash
git add -A && git commit -m "chore(manual-allocation): verification fixes"
```

---

## Self-Review (completed by author)

- **Spec coverage:** score_teams extraction (P1), seedable tiebreak/regenerate (P2), allocate reseed+replace-draft (P3), draft-only move + recompute (P4), hooks (P5), move `<select>` + Regenerate UI (P6), testing (each phase + P7). ✅
- **Type consistency:** `score_teams(team_score_sums, team_strength_counts, role_constraints) -> (skill, role_balance, fairness)` used identically in `run_allocation` and `move_participant`; `move_participant(db, allocation, participant_id, target_team_id)`; `MemberMove.team_id` ↔ frontend `{ team_id }`; `moveMember`/`regenerateAllocation`/`onChanged` names consistent across hook, results-grid, engine page; `_tiebreak(id, seed)` with `seed=0` default preserves existing tests. ✅
- **Placeholders:** none — full code per step; cleanup placed in the endpoint (not the engine) so the deterministic engine tests that compare two allocations stay valid. ✅
- **YAGNI:** no keep-together/apart constraints; native `<select>` (no DnD lib); ephemeral seed (no migration). ✅
