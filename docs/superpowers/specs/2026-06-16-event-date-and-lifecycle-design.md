# Event Date + Lifecycle (Archive / Delete) Design

**Date:** 2026-06-16
**Status:** Approved design (pending spec review)
**Branch:** `feat/event-date-and-lifecycle` (off `main`)

## Overview

Two additions to event management:
1. **Event date & time** — an optional `datetime` captured at event setup, shown on the
   event card and detail page.
2. **End-of-life choices** — the organizer can **Archive** an event (keep it and its
   results as history, hidden from the active list) or **Permanently delete** it (hard
   removal of the event and everything under it). Archived events are viewable via an
   **Archived view**.

Today `DELETE /events/{id}` silently sets `status="archived"`, archived events are
hidden everywhere with no way to view them, and there is no event date.

## Goals
- Capture when an event happens (optional, non-disruptive).
- Give organizers an explicit, understandable choice between keeping history and
  permanently removing an event.
- Make "keep history" useful by letting organizers see archived events.

## Non-Goals
- No timezone conversion — the datetime is treated as wall-clock local time.
- No recurring events, reminders, or calendar integration.
- No multi-day ranges (single start datetime only).
- No undo/restore for permanent delete (it is irreversible by design).

## Decisions (locked)
- Date field: single **optional `event_at` datetime** (`<input type="datetime-local">`).
- Archive = `PATCH status:"archived"`; Permanent delete = hard cascade `DELETE`.
- Archived view = a "Show archived" toggle on the Overview page.
- Permanent delete cascades all child rows and requires a confirmation dialog.

## Data Model

### `Event` (migration `0004`)
- Add `event_at = Column(DateTime(timezone=False), nullable=True)`.

### Schemas (`backend/app/schemas/event.py`)
- `EventCreate`: add `event_at: Optional[datetime] = None`.
- `EventUpdate`: add `event_at: Optional[datetime] = None`.
- `EventOut`: add `event_at: Optional[datetime]`.

## Backend Behavior

### Archive (existing path, no new endpoint)
`update_event` already applies `status` from `EventUpdate`; `EventStatus` already
includes `"archived"`. Archiving is `PATCH /events/{id}` `{ "status": "archived" }`.
`list_events` already excludes archived from the active list. No change needed beyond
the archived-list filter below.

### Permanent delete (repurpose `delete_event`)
Change `delete_event` from soft-archive to a **hard cascade delete**, in FK-safe order:
`team_members` → `teams` → `allocations` → `allocation_configs` → `participants` →
`event_co_organizers` → the `event`. Resolve teams/allocations via the event's
allocations. Keep `_assert_organizer` authorization. `DELETE /events/{id}` returns the
deleted event's `EventOut` (built before deletion).

### Archived list filter
`list_events(db, user_id, archived: bool = False)`:
- `archived=False` (default): owned + co-organized events with `status != "archived"` (current behavior).
- `archived=True`: owned + co-organized events with `status == "archived"`.
The `GET /events` route gains an `archived: bool = Query(False)` param passed through.

## Frontend

### Hooks (`frontend/hooks/use-events.ts`)
- `Event` interface: add `event_at?: string`.
- `CreateEventPayload`: add `event_at?: string`.
- `useEvents(archived = false)`: include `?archived=true` in the key/URL when archived.
- Add `archiveEvent(token, eventId)` → `updateEvent(..., { status: "archived" })`.
- Add `deleteEvent(token, eventId)` → `DELETE /api/v1/events/{eventId}`, then revalidate the events list.

### Create-event dialog (`components/events/create-event-dialog.tsx`)
- Add an optional "Event date & time" field: `<input type="datetime-local">` bound via
  the existing `react-hook-form`. Submit `event_at` only when set (omit/`undefined` if blank).

### Event card (`components/events/event-card.tsx`)
- Show `event_at` (formatted, e.g. "Jul 15, 2026, 2:00 PM") next to the Calendar icon when set;
  show "No date" otherwise. Give the team-count its own icon (e.g. `Boxes`) so Calendar
  is no longer mislabeled on teams.

### Event detail page (`app/dashboard/events/[eventId]/page.tsx`)
- Show the formatted `event_at` under the title when set.
- Header actions: **Archive** (calls `archiveEvent`, toast, navigate to Overview) and
  **Delete permanently** (opens a confirmation dialog; on confirm calls `deleteEvent`,
  toast, navigate to Overview).
- Confirmation dialog: a Radix `Dialog` warning that this permanently removes the event
  and all participants/results; Cancel + "Delete permanently" buttons.

### Archived view (`components/events/events-view.tsx`)
- Add a "Show archived" toggle (button) that switches the list between active and archived
  via `useEvents(archived)`. Archived cards still link to the detail page (to view results /
  export). The "New Event" + Quick-guide actions remain on the active view.

## Testing

### Backend (`backend/tests/`)
- `event_at` round-trips through create and appears in `EventOut`; a `PATCH` can set it.
  (Clearing to null is out of scope — `update_event` uses `exclude_none=True`, so omitted
  fields are left unchanged.)
- `DELETE /events/{id}` hard-deletes: the event is gone (404 afterward) and its participants
  and allocations are removed from the DB.
- `PATCH status:"archived"` keeps the event row; it disappears from `GET /events` (active) and
  appears in `GET /events?archived=true`.
- Authorization preserved: a non-organizer gets 403 on delete.

### Frontend
- Create dialog renders the date/time input.
- `event-card` formats and shows a date when `event_at` is set, "No date" when not.
- Delete confirmation dialog requires an explicit confirm before `deleteEvent` is called.

### Gates
`pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Out of Scope
- Restoring permanently-deleted events.
- Un-archiving from the UI (can be added later via `PATCH status`).
- Timezone-aware scheduling and reminders.
