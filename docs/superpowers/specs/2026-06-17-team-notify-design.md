# npub at Registration + Team-Notify on Publish (B2b) Design

**Date:** 2026-06-17
**Status:** Approved (with 4 adjustments incorporated)
**Branch:** `feat/team-notify` (off `main`)
**Builds on:** B2a `nostr_service` (`send_dm`, `bech32_decode`) — shipped in PR #18.

## Overview

Attendees may optionally provide their Nostr `npub` at registration. When an organizer
**publishes** an allocation, each attendee who provided an npub receives a best-effort
NIP-04 DM telling them their team and a link to the public results. Attendees without an
npub continue to use **find-my-team** (B1). This closes the participant round-trip.

## Goals
- Capture an optional, validated `npub` at registration.
- On publish, DM each npub-having attendee their team — best-effort, non-blocking.
- Never spam: a successful notification is sent at most once per (allocation, participant).
- Never permanently suppress delivery because of a transient relay outage.

## Non-Goals (B2b)
- Retries/queues, delivery receipts, NIP-17.
- Editing/removing an npub after registration.
- DMs on any trigger other than publish.
- Deep-linking to a specific team on the results page (noted as a future enhancement;
  the link stays `/results/{allocation_id}`).

## Decisions (locked)
- **DM trigger:** once per **published allocation** — dedup keyed on `(allocation_id, participant_id)`.
  Re-publishing the same allocation never re-sends a *successful* notification; a regenerated
  (new) allocation notifies again with the updated teams.
- **npub validation:** optional; if provided it must be a well-formed `npub1…` (bech32, hrp `npub`,
  decodes to 32 bytes), else **422**. Empty/omitted → stored as `NULL`.
- **Only record success:** the dedup row is written **only when `send_dm` returns `True`**
  (≥1 relay responded). On failure we log a warning and write nothing, so a later re-publish
  retries that participant. (Adjustment 1.)
- **npub is organizer-only data:** exposed solely in the organizer-authenticated `ParticipantOut`;
  never in `PublicTeamMember`, public results, public join, or find-my-team.
- **No new config:** the results link base reuses `FRONTEND_URL` (`settings.cors_origins[0]`).

## Components

### 1. Data model — migration `0006_npub_and_team_notifications`
- `participants.npub` — new nullable `String` column.
- New table **`team_notifications`**:
  - `id` (Uuid pk), `allocation_id` (FK `allocations.id`, indexed), `participant_id` (FK `participants.id`),
    `sent_at` (the DM success time, set explicitly), `created_at` (server default `now()`, indexed). (Adjustment 2.)
  - **Unique constraint** `uq_team_notification` on `(allocation_id, participant_id)`.
- Register `TeamNotification` in `app/models/__init__.py`.

### 2. Registration — `app/schemas/participant.py`
- `ParticipantRegister` gains `npub: Optional[str] = None`.
- A `field_validator("npub", mode="before")`: treat `None`/blank → `None`; otherwise
  `npub.strip().lower()` (Adjustment 3), then validate via a new
  `nostr_service.validate_npub(npub) -> str` that raises `ValueError` unless `bech32_decode`
  yields hrp `npub` and a 32-byte key. A `ValueError` surfaces to the client as **422**.
- Store the normalized `npub` on the participant (in `participant_service.register_participant`).
- `ParticipantOut` gains `npub: Optional[str]` (organizer dashboard only). No public schema changes.

### 3. `nostr_service.validate_npub`
- `validate_npub(npub: str) -> str`: `hrp, key = bech32_decode(npub)`; raise `ValueError("invalid npub")`
  if `hrp != "npub"` or `len(key) != 32`; return the (already-normalized) npub. Pure, unit-testable.

### 4. Notify fan-out — `app/services/team_notifications.py` (new)
- `notify_teams_task(allocation_id: UUID) -> None` — designed to run inside FastAPI `BackgroundTasks`.
  - Opens its **own session**: `with SessionLocal() as db:` (request session is gone post-response).
  - **No-op guard:** if `not settings.SQUADSYNC_NSEC`, return immediately (write nothing) so enabling
    the key later + re-publish still works.
  - Load the allocation; if missing or `status != "published"`, return.
  - Compute the results link: `f"{settings.cors_origins[0]}/results/{allocation_id}"` (fall back to
    `settings.FRONTEND_URL` if the origins list is empty).
  - Load the event (for its title) and the teams + members of this allocation.
  - For each team, for each member **with a non-null `npub`**, in an **isolated `try/except` per
    participant** (one failure must not abort the loop):
    - Skip if a `team_notifications` row already exists for `(allocation_id, participant_id)`.
    - `ok = send_dm(member.npub, message)` where `message =`
      `f"You're on {team.name} for {event.title}!\n\nSee your team and teammates: {link}"`.
    - **If `ok`:** insert a `team_notifications` row (`sent_at = now`) and `commit`; on `IntegrityError`
      (race/dupe) roll back and continue. **If not `ok`:** log a warning, write nothing.

### 5. Publish endpoint — `app/api/v1/allocation.py`
- `publish_allocation` gains a `background_tasks: BackgroundTasks` parameter.
- After the existing `db.commit()`, schedule `background_tasks.add_task(notify_teams_task, allocation.id)`.
- The endpoint's behavior and response (`{"detail": "published"}`) are otherwise unchanged; the DM
  fan-out never blocks or fails the publish.

### 6. Frontend — registration form (`components/registration/registration-form.tsx`)
- Add an optional `npub` text input with helper text: *"Optional — paste your Nostr npub to be DM'd
  your team. Otherwise you can look it up after results are posted."*
- Include `npub` in the register POST body when non-empty. The server is the source of truth for
  validation; a 422 surfaces inline as a field/error message (reuse the form's existing error handling).

## Error Handling
- `notify_teams_task` never propagates: the session context manager, the no-op guard, and the
  per-participant `try/except` ensure a single bad send/insert is logged and skipped.
- `send_dm` is already best-effort (never raises, no-op when unconfigured).
- A failed send writes **no** dedup row, so re-publish is a manual retry.

## Testing
- **Schema** (`tests/test_registration.py` or new): valid npub stored normalized; mixed-case/whitespace
  npub normalized to canonical; malformed npub → 422; empty/omitted → `None`.
- **`validate_npub`**: accepts the NIP-19 npub vector; rejects an nsec / garbage with `ValueError`.
- **`notify_teams_task`** (`tests/test_team_notify.py`, `send_dm` monkeypatched, no network):
  - npub member is DM'd once and a `team_notifications` row is written; non-npub member is skipped.
  - **Dedup:** running the task twice for the same allocation calls `send_dm` once per participant.
  - **Failure path:** when `send_dm` returns `False`, **no** row is written (re-run sends again).
  - **No-op:** when `SQUADSYNC_NSEC` is unset, `send_dm` is never called and no rows are written.
  - Regenerated/new allocation → new rows, sends again.
- **Publish endpoint**: publishing schedules `notify_teams_task` (monkeypatch `add_task` / the task).
- **Frontend** (`tests/components/registration-form.test.tsx`): npub field renders; a provided npub is
  included in the submit body; omitted npub is absent/empty.
- Gates: `pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Migration
Single Alembic `0006_npub_and_team_notifications` (additive column + table). No backfill.

## Out of Scope (→ later)
- Retries/queue, delivery receipts, NIP-17.
- Editing npub post-registration; per-team deep links on the results page.
- Notifying on re-allocation without an explicit publish.
