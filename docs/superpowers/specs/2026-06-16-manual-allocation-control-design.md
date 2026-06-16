# Manual Allocation Control (Move + Regenerate) Design

**Date:** 2026-06-16
**Status:** Approved design (pending spec review)
**Branch:** `feat/manual-allocation-control` (off `main`)
**Scope note:** This is **Spec A** of two. Spec B (participant round-trip: optional npub + find-my-team + Nostr DM notify) is a separate later cycle.

## Overview

The allocation engine forms teams deterministically, but the organizer cannot
correct the result — they can't move a participant between teams, and re-running
produces the identical allocation (it's fully deterministic). In real events the
organizer always needs the final say ("split these two", "rebalance team 4").
This adds two abilities, **draft-only** (publishing locks the allocation):

1. **Move** a participant from one team to another (per-member dropdown).
2. **Regenerate** — produce a different *valid* allocation (seeded shuffle).

Pre-generation keep-together/keep-apart constraints are intentionally **deferred**
(manual move covers that need by hand).

## Goals
- Let organizers trust the allocator by being able to correct it.
- Keep displayed team scores honest after manual edits.
- Preserve the engine's determinism (same inputs+seed → same teams).

## Non-Goals (this spec)
- Pairwise keep-together / keep-apart constraints (fast-follow).
- Editing after publish (publishing locks; re-notify is Spec B territory).
- Drag-and-drop (per-member dropdown instead).

## Decisions (locked)
- Move UX = per-member "Move to team" `Select`.
- Editing/regenerate allowed only while `allocation.status == "draft"`.
- Regenerate seed is ephemeral (not persisted); each regenerate rolls a new seed.

## Components

### 1. Scoring helper (extract + reuse) — `allocation_engine.py`
Extract the engine's inline team-scoring into a pure function:
```
score_teams(team_score_sums: list[float], role_counts_per_team, role_constraints) -> (skill_score, role_balance_score, fairness_score)
```
- `skill_score = max(0, 100*(1 - stdev/mean))` over team score-sums (0 if mean 0 / <2 teams).
- `role_balance_score = 100 * fulfilled / total_required` (100 if no constraints), where
  `fulfilled` sums `min(count_of_strength_in_team, required)` across teams, capped at `required` per team.
- `fairness_score = 0.6*skill_score + 0.4*role_balance_score`.
`run_allocation` is refactored to call this (same numbers as today). Unit-tested directly.

### 2. Seedable tiebreak — `allocation_engine.py`
`run_allocation(db, event_id, config, seed: int = 0)`. Tiebreak key:
```
def _tiebreak(participant_id, seed):
    return str(participant_id) if seed == 0 else hashlib.sha256(f"{participant_id}:{seed}".encode()).hexdigest()
```
All anchor/intermediate sorts use `(-composite_score, _tiebreak(p.id, seed))`. `seed=0`
preserves today's exact ordering (existing determinism tests unchanged); a non-zero
seed yields a different valid allocation. The balance passes are otherwise untouched.

### 3. Regenerate = allocate replaces the draft — `allocation.py` + engine
At the start of `run_allocation`, delete the event's prior **draft** allocations and
their teams/team_members (published allocations untouched), so there's at most one
draft per event. The `allocate` endpoint passes a fresh `seed = random.randint(1, 2**31)`
on each call, so calling it again ("Regenerate") yields a new draft. No migration.

### 4. Move endpoint — `allocation.py` + a service function
`PATCH /api/v1/allocations/{allocation_id}/members/{participant_id}` body `{ "team_id": "<uuid>" }`.
- `assert_allocation_organizer` (org-only).
- `409` if `allocation.status != "draft"`.
- Validate the target team belongs to this allocation; validate the participant is a
  member of some team in this allocation.
- Update the `team_members` row (move participant_id to the target team).
- Recompute all team scores for the allocation via `score_teams` and persist.
- Return the updated `AllocationOut` (reusing `_build_allocation_out`).

### 5. Frontend — `results-grid.tsx` (+ `use-allocation.ts`)
- `use-allocation.ts`: add `moveMember(token, allocationId, participantId, teamId)` (PATCH) and
  `regenerateAllocation(token, eventId)` (= `runAllocation` again); both revalidate.
- `results-grid.tsx`: when `allocation.status === "draft"`, each member row (in the
  "View members" list of `team-card.tsx`) shows a compact "Move to team" `Select` listing
  the other teams; changing it calls `moveMember` then refreshes the allocation. Add a
  **Regenerate** button beside Publish (draft only). Published view stays read-only.
- This requires `team-card.tsx` (or the results grid) to know the full team list and an
  `onMove` callback; pass `teams` + `onMove` down, gated on a `draft` flag.

## Testing
- **`score_teams`** (pure): even teams → high skill_score; lopsided → lower; no constraints → role_balance 100; partial fulfillment → proportional.
- **Engine seed**: `seed=0` reproduces current deterministic membership (existing tests pass unchanged); two different non-zero seeds can produce different memberships but every participant is still assigned exactly once and team count is correct.
- **Regenerate/cleanup**: a second `allocate` for an event leaves exactly one draft allocation (prior draft + its teams/members deleted); a published allocation is preserved across a regenerate.
- **Move**: moving a participant updates membership and recomputes scores; `409` on a published allocation; `403` for a non-organizer; moving to a team outside the allocation → `404/400`.
- **Frontend**: move `Select` and Regenerate button render only for draft; absent when published.
- Gates: `pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Out of Scope
- keep-together / keep-apart constraints.
- Post-publish editing and re-notification.
- Persisting/seeding reproducibility of a specific regenerate across restarts.
