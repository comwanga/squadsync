# Event Date + Lifecycle (Archive / Delete) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional event date/time and give organizers explicit Archive (keep history) vs Permanent-delete (hard cascade) actions, with an Archived view.

**Architecture:** Add `Event.event_at`; repurpose `DELETE /events/{id}` to a hard cascade delete and keep archive as `PATCH status:"archived"`; add an `archived` filter to the events list; surface date + lifecycle actions + an Archived toggle in the frontend.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic + pytest; Next.js 16 + React Hook Form + Zod + Vitest.

**Spec:** `docs/superpowers/specs/2026-06-16-event-date-and-lifecycle-design.md`
**Branch:** `feat/event-date-and-lifecycle` (off `main`).

---

## Phase 1 — Model + migration (`event_at`)

**Files:**
- Modify: `backend/app/models/event.py`
- Create: `backend/alembic/versions/0004_event_at.py`

- [ ] **Step 1: Add the column.** In `backend/app/models/event.py`, in the `Event` class, add after the `description` line:

```python
    event_at = Column(DateTime(timezone=False), nullable=True)
```

`DateTime` is already imported in this file (used by `created_at`).

- [ ] **Step 2: Create the migration** `backend/alembic/versions/0004_event_at.py`:

```python
"""event_at

Revision ID: 0004_event_at
Revises: 0003_universal_strength_taxonomy
Create Date: 2026-06-16
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_event_at"
down_revision: Union[str, None] = "0003_universal_strength_taxonomy"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("events") as b:
        b.add_column(sa.Column("event_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("events") as b:
        b.drop_column("event_at")
```

- [ ] **Step 3: Verify model + migration**

Run: `cd backend && python -c "from app.models.event import Event; print('model ok')"`
Run: `cd backend && DATABASE_URL="sqlite:///./mig.db" python -m alembic upgrade head && python -m alembic history | head -2 && rm -f mig.db`
Expected: `model ok`; history shows `0003… -> 0004_event_at (head)`.

- [ ] **Step 4: Commit**

```bash
git add backend/app/models/event.py backend/alembic/versions/0004_event_at.py
git commit -m "feat(model): add optional Event.event_at"
```

---

## Phase 2 — Schemas (`event_at`)

**Files:**
- Modify: `backend/app/schemas/event.py`

- [ ] **Step 1: Add `event_at` to the three schemas.** Edit `backend/app/schemas/event.py`:

Add `datetime` import at the top:
```python
from datetime import datetime
```

In `EventCreate`, add:
```python
    event_at: Optional[datetime] = None
```
In `EventUpdate`, add:
```python
    event_at: Optional[datetime] = None
```
In `EventOut`, add (after `description`):
```python
    event_at: Optional[datetime]
```

- [ ] **Step 2: Verify**

Run: `cd backend && python -c "from app.schemas.event import EventCreate, EventUpdate, EventOut; EventCreate(title='x', team_count=2, event_at='2026-07-15T14:00:00'); print('schemas ok')"`
Expected: `schemas ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas/event.py
git commit -m "feat(schema): event_at on event create/update/out"
```

---

## Phase 3 — Hard delete + archived list (service, route, tests)

**Files:**
- Modify: `backend/app/services/event_service.py`
- Modify: `backend/app/api/v1/events.py`
- Test: `backend/tests/test_event_lifecycle.py` (new)

- [ ] **Step 1: Write the failing tests.** Create `backend/tests/test_event_lifecycle.py`:

```python
def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "LC", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def test_event_at_roundtrips(client, auth_headers):
    res = client.post("/api/v1/events", headers=auth_headers,
                      json={"title": "Dated", "team_count": 2, "event_at": "2026-07-15T14:00:00"})
    assert res.status_code == 201
    assert res.json()["event_at"].startswith("2026-07-15T14:00")


def test_archive_keeps_row_and_filters(client, auth_headers):
    e = _active_event(client, auth_headers)
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "archived"})
    active = client.get("/api/v1/events", headers=auth_headers).json()
    assert all(x["id"] != e["id"] for x in active)
    archived = client.get("/api/v1/events?archived=true", headers=auth_headers).json()
    assert any(x["id"] == e["id"] for x in archived)


def test_delete_hard_removes_event_and_children(client, auth_headers, db):
    from app.models.participant import Participant
    from app.models.allocation import Allocation
    e = _active_event(client, auth_headers)
    slug = e["registration_slug"]
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    res = client.delete(f"/api/v1/events/{e['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert client.get(f"/api/v1/events/{e['id']}", headers=auth_headers).status_code == 404
    import uuid as _uuid
    eid = _uuid.UUID(e["id"])
    assert db.query(Participant).filter(Participant.event_id == eid).count() == 0
    assert db.query(Allocation).filter(Allocation.event_id == eid).count() == 0


def test_delete_requires_organizer(client, auth_headers, other_headers):
    e = _active_event(client, auth_headers)
    assert client.delete(f"/api/v1/events/{e['id']}", headers=other_headers).status_code == 403
```

This reuses the `other_headers` fixture; add it to this file (copied pattern from test_authz.py) at the top:

```python
import pytest
from coincurve import PrivateKey
from tests.conftest import make_nostr_event


@pytest.fixture
def other_headers(client):
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(pk)
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}
```

- [ ] **Step 2: Run to verify failures**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_event_lifecycle.py -q; rm -f *.db`
Expected: failures — archived filter/hard-delete not implemented yet.

- [ ] **Step 3: Rewrite `delete_event` as a hard cascade.** In `backend/app/services/event_service.py`, update the import line to add `EventOut`:

```python
from app.schemas.event import EventCreate, EventUpdate, CoOrganizerInvite, EventOut
```

Replace the whole `delete_event` function with:

```python
def delete_event(db: Session, event_id: UUID, user_id: UUID) -> EventOut:
    """Permanently delete an event and all of its child rows (hard delete)."""
    from app.models.allocation import Allocation, AllocationConfig
    from app.models.team import Team, TeamMember
    from app.models.participant import Participant

    event = _assert_organizer(db, event_id, user_id)
    snapshot = EventOut.model_validate(event)  # capture before deletion

    alloc_ids = [a.id for a in db.query(Allocation).filter(Allocation.event_id == event_id).all()]
    if alloc_ids:
        team_ids = [t.id for t in db.query(Team).filter(Team.allocation_id.in_(alloc_ids)).all()]
        if team_ids:
            db.query(TeamMember).filter(TeamMember.team_id.in_(team_ids)).delete(synchronize_session=False)
        db.query(Team).filter(Team.allocation_id.in_(alloc_ids)).delete(synchronize_session=False)
        db.query(Allocation).filter(Allocation.event_id == event_id).delete(synchronize_session=False)
    db.query(AllocationConfig).filter(AllocationConfig.event_id == event_id).delete(synchronize_session=False)
    db.query(Participant).filter(Participant.event_id == event_id).delete(synchronize_session=False)
    db.query(EventCoOrganizer).filter(EventCoOrganizer.event_id == event_id).delete(synchronize_session=False)
    db.delete(event)
    db.commit()
    return snapshot
```

- [ ] **Step 4: Add the `archived` filter to `list_events`.** Replace `list_events` with:

```python
def list_events(db: Session, user_id: UUID, archived: bool = False) -> list[Event]:
    status_filter = (Event.status == "archived") if archived else (Event.status != "archived")
    owned = db.query(Event).filter(Event.owner_id == user_id, status_filter).all()
    co_event_ids = [
        row.event_id for row in db.query(EventCoOrganizer).filter(EventCoOrganizer.user_id == user_id).all()
    ]
    co_events = db.query(Event).filter(Event.id.in_(co_event_ids), status_filter).all()
    seen = {str(e.id) for e in owned}
    return owned + [e for e in co_events if str(e.id) not in seen]
```

- [ ] **Step 5: Wire the route param.** In `backend/app/api/v1/events.py`, update the imports and the `list_all` route. Change the FastAPI import line to include `Query`:

```python
from fastapi import APIRouter, Depends, status, Query
```

Replace the `list_all` route with:

```python
@router.get("", response_model=list[EventOut])
def list_all(
    archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_events(db, current_user.id, archived)
```

(The `delete` route already returns `delete_event(...)`; its `response_model=EventOut` now receives an `EventOut` instance — fine.)

- [ ] **Step 6: Run the lifecycle tests**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_event_lifecycle.py -q; rm -f *.db`
Expected: 5 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/event_service.py backend/app/api/v1/events.py backend/tests/test_event_lifecycle.py
git commit -m "feat(events): hard cascade delete + archived list filter"
```

---

## Phase 4 — Frontend hooks

**Files:**
- Modify: `frontend/hooks/use-events.ts`

- [ ] **Step 1: Extend types + hooks.** In `frontend/hooks/use-events.ts`:

Add `event_at?: string;` to the `Event` interface (after `description`):
```ts
  description?: string;
  event_at?: string;
```

Add `event_at?: string;` to `CreateEventPayload`:
```ts
  participant_limit?: number;
  event_at?: string;
```

Change `useEvents` to accept an `archived` flag:
```ts
export function useEvents(archived = false) {
  const { token, isSessionLoading } = useToken();
  const path = archived ? "/api/v1/events?archived=true" : "/api/v1/events";
  const { data, error, isLoading } = useSWR(
    token ? [path, token] : null,
    ([p, t]) => fetchAPI<Event[]>(p, { token: t })
  );
  return { events: data ?? [], error, isLoading: isLoading || isSessionLoading };
}
```

Add two functions at the end of the file:
```ts
export async function archiveEvent(token: string, eventId: string) {
  const result = await updateEvent(token, eventId, { status: "archived" });
  mutate(["/api/v1/events", token]);
  return result;
}

export async function deleteEvent(token: string, eventId: string) {
  await fetchAPI(`/api/v1/events/${eventId}`, { method: "DELETE", token });
  mutate(["/api/v1/events", token]);
}
```

`updateEvent` already accepts `{ status }` (its payload type is `Partial<CreateEventPayload & { status: string }>`). `mutate` and `fetchAPI` are already imported.

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/hooks/use-events.ts
git commit -m "feat(ui): event_at type, archived fetch, archive/delete hooks"
```

---

## Phase 5 — Create-event dialog: date field

**Files:**
- Modify: `frontend/components/events/create-event-dialog.tsx`

- [ ] **Step 1: Add the field.** In the zod `schema` object, add:
```ts
  event_at: z.string().optional(),
```

In the form JSX, add this block immediately after the description field's closing `</div>` (before the `grid grid-cols-2` block):
```tsx
          <div className="space-y-1">
            <Label htmlFor="event_at">Event date &amp; time (optional)</Label>
            <Input id="event_at" type="datetime-local" {...register("event_at")} />
          </div>
```

In `onSubmit`, pass `event_at` only when set. Change the `createEvent(...)` call's payload object to include:
```tsx
        event_at: data.event_at || undefined,
```
(Add that line alongside the existing `title`, `description`, etc.)

- [ ] **Step 2: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean (pre-existing react-hooks warning OK).

- [ ] **Step 3: Commit**

```bash
git add frontend/components/events/create-event-dialog.tsx
git commit -m "feat(ui): optional event date/time in create dialog"
```

---

## Phase 6 — Event card: date display

**Files:**
- Create: `frontend/lib/format-date.ts`
- Test: `frontend/tests/lib/format-date.test.ts`
- Modify: `frontend/components/events/event-card.tsx`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/tests/lib/format-date.test.ts
import { describe, it, expect } from "vitest";
import { formatEventDate } from "@/lib/format-date";

describe("formatEventDate", () => {
  it("returns 'No date' when missing", () => {
    expect(formatEventDate(undefined)).toBe("No date");
    expect(formatEventDate("")).toBe("No date");
  });
  it("formats a datetime to a readable string containing the year", () => {
    expect(formatEventDate("2026-07-15T14:00:00")).toMatch(/2026/);
  });
});
```

- [ ] **Step 2: Run to verify failure**

Run: `cd frontend && npx vitest run tests/lib/format-date.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the formatter**

```ts
// frontend/lib/format-date.ts
// Formats a wall-clock event datetime (e.g. "2026-07-15T14:00") for display.
export function formatEventDate(value?: string): string {
  if (!value) return "No date";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "No date";
  return d.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}
```

- [ ] **Step 4: Run to verify pass**

Run: `cd frontend && npx vitest run tests/lib/format-date.test.ts`
Expected: PASS.

- [ ] **Step 5: Use it in the card.** In `frontend/components/events/event-card.tsx`:

Change the icon import line to add `Boxes`:
```tsx
import { Calendar, Users, ArrowRight, Boxes } from "lucide-react";
```
Add the import:
```tsx
import { formatEventDate } from "@/lib/format-date";
```
Replace the `CardContent` meta block so Calendar shows the date and teams gets its own icon:
```tsx
      <CardContent className="pb-2">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {formatEventDate(event.event_at)}
          </span>
          <span className="flex items-center gap-1">
            <Boxes className="h-3.5 w-3.5" />
            {event.team_count} teams
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3.5 w-3.5" />
            {event.participant_limit ? `Max ${event.participant_limit}` : "No limit"}
          </span>
        </div>
      </CardContent>
```

- [ ] **Step 6: Typecheck + lint + tests**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: clean; all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/lib/format-date.ts frontend/tests/lib/format-date.test.ts frontend/components/events/event-card.tsx
git commit -m "feat(ui): show event date on card; fix mislabeled icons"
```

---

## Phase 7 — Event detail: date + Archive/Delete actions

**Files:**
- Modify: `frontend/app/dashboard/events/[eventId]/page.tsx`

- [ ] **Step 1: Add date display + lifecycle actions with a confirm dialog.** Edit `frontend/app/dashboard/events/[eventId]/page.tsx`:

Update imports:
```tsx
import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import { toast } from "sonner";
import { useEvent, updateEvent, archiveEvent, deleteEvent } from "@/hooks/use-events";
import { formatEventDate } from "@/lib/format-date";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from "@/components/ui/dialog";
import { Users, Settings, Zap, ArrowRight, Archive, Trash2, Calendar } from "lucide-react";
```

Inside the component, add state + handlers (after the existing `activating` state):
```tsx
  const router = useRouter();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleArchive = async () => {
    if (!session?.accessToken) return;
    setBusy(true);
    try {
      await archiveEvent(session.accessToken, eventId);
      toast.success("Event archived");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to archive");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async () => {
    if (!session?.accessToken) return;
    setBusy(true);
    try {
      await deleteEvent(session.accessToken, eventId);
      toast.success("Event permanently deleted");
      router.push("/dashboard");
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setBusy(false);
      setConfirmDelete(false);
    }
  };
```

Under the title (replace the title `<div>` block) show the date:
```tsx
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{event.title}</h1>
          {event.description && <p className="text-muted-foreground text-sm mt-1">{event.description}</p>}
          <p className="text-muted-foreground text-sm mt-1 flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" /> {formatEventDate(event.event_at)}
          </p>
        </div>
```

In the header actions cluster (the `<div className="flex items-center gap-3">` holding the Badge + Open Registration button), add after the existing button:
```tsx
          <Button size="sm" variant="outline" onClick={handleArchive} disabled={busy}>
            <Archive className="mr-1 h-4 w-4" /> Archive
          </Button>
          <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700" onClick={() => setConfirmDelete(true)} disabled={busy}>
            <Trash2 className="mr-1 h-4 w-4" /> Delete
          </Button>
```

At the end of the returned JSX (before the final closing `</div>`), add the confirm dialog:
```tsx
      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Delete this event permanently?</DialogTitle>
            <DialogDescription>
              This removes <strong>{event.title}</strong> and all of its participants and
              results. This cannot be undone. To keep the record instead, use Archive.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setConfirmDelete(false)} disabled={busy}>Cancel</Button>
            <Button className="bg-red-600 hover:bg-red-700 text-white" onClick={handleDelete} disabled={busy}>
              {busy ? "Deleting…" : "Delete permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
```

(If `DialogFooter` is not exported by `@/components/ui/dialog`, read that file and use the exported parts — render the buttons in a `<div className="flex justify-end gap-2">` instead.)

- [ ] **Step 2: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/dashboard/events/[eventId]/page.tsx
git commit -m "feat(ui): event date + Archive/Delete actions on detail page"
```

---

## Phase 8 — Archived view toggle

**Files:**
- Modify: `frontend/components/events/events-view.tsx`

- [ ] **Step 1: Add a toggle.** In `frontend/components/events/events-view.tsx`:

Make it a client component that tracks an `archived` flag and passes it to `useEvents`. Update the top:
```tsx
"use client";

import { useState } from "react";
import { useEvents } from "@/hooks/use-events";
import { EventCard } from "@/components/events/event-card";
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { QuickGuideButton } from "@/components/onboarding/quick-guide-button";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function EventsView({ title, subtitle }: { title: string; subtitle: string }) {
  const [archived, setArchived] = useState(false);
  const { events, isLoading, error } = useEvents(archived);
```

Add the toggle button into the header actions cluster (the `<div className="flex items-center gap-2">` with QuickGuide + CreateEventDialog). Put a toggle before them:
```tsx
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setArchived(a => !a)}>
            {archived ? "Active events" : "Show archived"}
          </Button>
          {!archived && <QuickGuideButton />}
          {!archived && <CreateEventDialog />}
        </div>
```

Update the empty-state copy to reflect the mode:
```tsx
      ) : events.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <p className="text-lg font-medium">{archived ? "No archived events" : "No events yet"}</p>
          <p className="text-sm mt-1">{archived ? "Archived events will appear here." : "Create your first event to get started"}</p>
        </div>
```

- [ ] **Step 2: Typecheck + lint + tests**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: clean; all pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/components/events/events-view.tsx
git commit -m "feat(ui): Show archived toggle on the events list"
```

---

## Phase 9 — Full verification

- [ ] **Step 1: Backend suite + migration**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Run: `cd backend && DATABASE_URL="sqlite:///./e2e.db" python -m alembic upgrade head && rm -f e2e.db`
Expected: all pass; migration ends at `0004_event_at`.

- [ ] **Step 2: Frontend gates + build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: tsc clean; lint no new errors; all tests pass; build succeeds.

- [ ] **Step 3: Commit any fixes** (only if needed)

```bash
git add -A && git commit -m "chore(event-lifecycle): verification fixes"
```

---

## Self-Review (completed by author)

- **Spec coverage:** `event_at` model/migration (P1), schemas (P2), hard delete + archived filter (P3), hooks (P4), create dialog date (P5), card date + icon fix (P6), detail date + archive/delete + confirm (P7), archived toggle (P8), testing (P3/P6 + P9). ✅
- **Type consistency:** `event_at` is `DateTime`(model)/`datetime`(schema)/`string`(TS) consistently; `list_events(..., archived)` matches the route `Query(False)` and `useEvents(archived)`/`?archived=true`; `archiveEvent`/`deleteEvent` names match detail-page imports; `formatEventDate` used by card + detail. ✅
- **Placeholders:** none — full code per step; the one conditional (`DialogFooter` export) has an explicit fallback instruction. ✅
- **YAGNI:** wall-clock datetime (no tz), toggle (no new route), no un-archive/restore UI. ✅
