# Find My Team (B1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an attendee on the public results page enter the email they registered with and see their team + teammates.

**Architecture:** A public, published-only `POST …/find-team` endpoint matches the email (case-insensitive) to a participant and returns their `PublicTeam` (names only). A small client `FindMyTeam` widget on the results page calls it. While there, fix a stale `role`/`skill_level` render on the results page.

**Tech Stack:** FastAPI + SQLAlchemy + pytest; Next.js 16 + React + Vitest.

**Spec:** `docs/superpowers/specs/2026-06-17-find-my-team-design.md`
**Branch:** `feat/find-my-team` (off `main`).

---

## Phase 1 — Backend: find-team endpoint

**Files:**
- Modify: `backend/app/schemas/allocation.py` (add `FindTeamRequest`)
- Modify: `backend/app/api/v1/public.py` (add endpoint)
- Test: `backend/tests/test_find_my_team.py` (new)

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/test_find_my_team.py
def _published(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "FMT", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    return e, a


def test_find_team_returns_my_team(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "p0@t.com"})
    assert res.status_code == 200
    team = res.json()
    assert "name" in team
    assert any(m["name"] == "P0" for m in team["members"])
    assert all("email" not in m for m in team["members"])  # no PII leak


def test_find_team_case_insensitive(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "P0@T.COM"})
    assert res.status_code == 200


def test_find_team_unknown_email_404(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "nobody@t.com"})
    assert res.status_code == 404


def test_find_team_unpublished_404(client, auth_headers):
    # Draft allocation (not published) must not be queryable.
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "D", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"d{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "d0@t.com"})
    assert res.status_code == 404
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_find_my_team.py -q; rm -f *.db`
Expected: FAIL (404 from unknown route / endpoint missing).

- [ ] **Step 3: Add the request schema.** In `backend/app/schemas/allocation.py`, add `EmailStr` to the pydantic import (`from pydantic import BaseModel, EmailStr`) and add:

```python
class FindTeamRequest(BaseModel):
    email: EmailStr
```

(`EmailStr` needs `email-validator`, already a dependency — `ParticipantRegister.email` uses it.)

- [ ] **Step 4: Add the endpoint** to `backend/app/api/v1/public.py`. Add imports `from sqlalchemy import func` and add `FindTeamRequest` to the `from app.schemas.allocation import (...)` line. Add:

```python
@router.post("/allocations/{allocation_id}/find-team", response_model=PublicTeam)
def find_my_team(allocation_id: UUID, req: FindTeamRequest, db: Session = Depends(get_db)):
    """Public lookup: which team is this registered email on? Published-only.

    Returns the matching team (names only, no PII). 404 for unpublished allocations
    or emails not registered on the event — an opaque message so it can't be used to
    probe for draft existence beyond what the public results page already shows.
    """
    allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
    if not allocation or allocation.status != "published":
        raise HTTPException(status_code=404, detail="Results not found")

    participant = (
        db.query(Participant)
        .filter(
            Participant.event_id == allocation.event_id,
            func.lower(Participant.email) == req.email.lower(),
        )
        .first()
    )
    team = None
    if participant:
        team = (
            db.query(Team)
            .join(TeamMember, Team.id == TeamMember.team_id)
            .filter(Team.allocation_id == allocation.id, TeamMember.participant_id == participant.id)
            .first()
        )
    if not team:
        raise HTTPException(status_code=404, detail="Not found on this event")

    members = (
        db.query(Participant)
        .join(TeamMember, Participant.id == TeamMember.participant_id)
        .filter(TeamMember.team_id == team.id)
        .all()
    )
    return PublicTeam(
        id=team.id,
        name=team.name,
        fairness_score=team.fairness_score,
        members=[PublicTeamMember.model_validate(m) for m in members],
    )
```

- [ ] **Step 5: Run the tests + full suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_find_my_team.py -q; rm -f *.db`
Expected: 4 passed.
Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/allocation.py backend/app/api/v1/public.py backend/tests/test_find_my_team.py
git commit -m "feat(public): find-my-team endpoint (published-only, email lookup)"
```

---

## Phase 2 — Frontend: `FindMyTeam` component

**Files:**
- Create: `frontend/components/results/find-my-team.tsx`
- Test: `frontend/tests/components/find-my-team.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/tests/components/find-my-team.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchAPI } from "@/lib/api";
import { FindMyTeam } from "@/components/results/find-my-team";

vi.mock("@/lib/api", () => ({ fetchAPI: vi.fn() }));

beforeEach(() => vi.clearAllMocks());

describe("FindMyTeam", () => {
  it("shows the matched team and teammates on success", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "t1", name: "Team 01", members: [{ id: "a", name: "Alice" }, { id: "b", name: "Bob" }],
    });
    render(<FindMyTeam allocationId="alloc-1" />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "alice@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /find my team/i }));
    await waitFor(() => expect(screen.getByText(/Team 01/)).toBeInTheDocument());
    expect(screen.getByText(/Alice/)).toBeInTheDocument();
  });

  it("shows a not-found message on error", async () => {
    (fetchAPI as ReturnType<typeof vi.fn>).mockRejectedValue(new Error("404"));
    render(<FindMyTeam allocationId="alloc-1" />);
    fireEvent.change(screen.getByLabelText(/email/i), { target: { value: "nobody@test.com" } });
    fireEvent.click(screen.getByRole("button", { name: /find my team/i }));
    await waitFor(() => expect(screen.getByText(/couldn't find that email/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run, expect FAIL**

Run: `cd frontend && npx vitest run tests/components/find-my-team.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

```tsx
// frontend/components/results/find-my-team.tsx
"use client";

import { useState } from "react";
import { fetchAPI } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface Member { id: string; name: string }
interface Team { id: string; name: string; members: Member[] }

export function FindMyTeam({ allocationId }: { allocationId: string }) {
  const [email, setEmail] = useState("");
  const [team, setTeam] = useState<Team | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "notfound">("idle");

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    setState("loading");
    setTeam(null);
    try {
      const t = await fetchAPI<Team>(
        `/api/v1/public/allocations/${allocationId}/find-team`,
        { method: "POST", body: { email } }
      );
      setTeam(t);
      setState("idle");
    } catch {
      setState("notfound");
    }
  };

  return (
    <div className="rounded-lg border bg-white p-4 max-w-md mx-auto">
      <form onSubmit={onSubmit} className="flex gap-2">
        <Input
          aria-label="Email"
          type="email"
          placeholder="Email you registered with"
          value={email}
          onChange={e => setEmail(e.target.value)}
        />
        <Button type="submit" disabled={state === "loading"}>
          {state === "loading" ? "Finding…" : "Find my team"}
        </Button>
      </form>
      {team && (
        <p className="text-sm mt-3">
          You&apos;re on <strong>{team.name}</strong> — with {team.members.map(m => m.name).join(", ")}.
        </p>
      )}
      {state === "notfound" && (
        <p className="text-sm text-muted-foreground mt-3">
          We couldn&apos;t find that email on this event. Check the address you registered with.
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run, expect PASS**

Run: `cd frontend && npx vitest run tests/components/find-my-team.test.tsx`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/results/find-my-team.tsx frontend/tests/components/find-my-team.test.tsx
git commit -m "feat(ui): FindMyTeam lookup component"
```

---

## Phase 3 — Wire into results page (+ fix stale member render)

**Files:**
- Modify: `frontend/app/dashboard/../results/[allocationId]/page.tsx` → exact path `frontend/app/results/[allocationId]/page.tsx`

- [ ] **Step 1: Fix the stale member fields + render the widget.** Edit `frontend/app/results/[allocationId]/page.tsx`:

Add the import:
```tsx
import { FindMyTeam } from "@/components/results/find-my-team";
```

Replace the `TeamMember` interface (currently `{ id; name; role; skill_level }`) with:
```tsx
interface TeamMember { id: string; name: string; normalized_strength?: string; experience_level: string; }
```

Render `<FindMyTeam>` between the header block and the team grid — insert after the closing `</div>` of the `text-center` header `<div>` and before the `<div className="grid ...">`:
```tsx
        <FindMyTeam allocationId={allocationId} />
```

Fix the member line so it shows the real field (the current `{m.role}` is always undefined). Replace:
```tsx
                      <span className="text-muted-foreground capitalize text-xs">{m.role}</span>
```
with:
```tsx
                      <span className="text-muted-foreground capitalize text-xs">{(m.normalized_strength ?? "").replaceAll("_", " ")}</span>
```

- [ ] **Step 2: Verify**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: tsc clean (no remaining `m.role`/`skill_level`); 0 lint errors (pre-existing react-hooks warning OK); all tests pass.

- [ ] **Step 3: Commit**

```bash
git add "frontend/app/results/[allocationId]/page.tsx"
git commit -m "feat(ui): find-my-team on results page; fix stale member role render"
```

---

## Phase 4 — Full verification

- [ ] **Step 1: Backend suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 2: Frontend gates + build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: tsc clean; lint no new errors; all tests pass; build succeeds (`/results/[allocationId]` present).

- [ ] **Step 3: Commit any fixes** (only if needed)

```bash
git add -A && git commit -m "chore(find-my-team): verification fixes"
```

---

## Self-Review (completed by author)

- **Spec coverage:** endpoint (P1: published-only, case-insensitive, no-PII, 404s), `FindTeamRequest` schema (P1), `FindMyTeam` component success/not-found (P2), results-page wiring (P3), testing (P1/P2 + P4). Plus the in-scope stale-render fix (P3). ✅
- **Type consistency:** `FindTeamRequest.email` (EmailStr) ↔ frontend `{ email }`; endpoint returns `PublicTeam` ↔ component `Team { id, name, members }` (subset, fine); `PublicTeamMember` (name, no email) ↔ asserted no-PII test. ✅
- **Placeholders:** none — full code per step; the only judgment point (results page path) is given exactly. ✅
- **YAGNI:** no rate limiting, no auth on the public lookup, no multi-allocation handling. ✅
