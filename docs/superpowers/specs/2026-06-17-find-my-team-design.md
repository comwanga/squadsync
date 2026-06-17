# Find My Team (B1) Design

**Date:** 2026-06-17
**Status:** Approved design (pending spec review)
**Branch:** `feat/find-my-team` (off `main`)
**Scope note:** This is **B1** of the participant round-trip. **B2** (next cycle) adds optional
npub at registration, Nostr DM team-notify on publish, and a Settings **feedback box** — all
sharing the same Nostr-send infra (a dedicated **bot `nsec`** sender + recipient **npub**,
NIP-04, relays; feedback stored in DB + best-effort DM). B2 decisions are recorded here for
continuity but are **not** implemented in B1.

## Overview

After teams are published the organizer shares a public results link, but the attendees who
scanned the QR have no easy way to learn *their* team. B1 adds a **"Find my team"** lookup on
the public results page: an attendee enters the email they registered with and sees their team
and teammates. No new infrastructure — a public lookup against the published allocation.

## Goals
- Close the attendee-facing loop with zero new infra.
- Don't leak draft allocations or participant emails.

## Non-Goals (B1)
- npub collection, Nostr DMs, the feedback box (all B2).
- Notifying attendees automatically (B2).
- Rate limiting (revisit with broader hardening).

## Decisions (locked)
- Lookup key = **email** (unique per event; unambiguous).
- Lookup is **POST** (email in body, not URL/logs).
- **Published-only**: lookups against non-published allocations return 404.
- Response reuses the existing `PublicTeam` shape (names only, no emails).

## Components

### Backend — `app/api/v1/public.py`
New endpoint `POST /api/v1/public/allocations/{allocation_id}/find-team`, body `{ "email": str }`:
1. Load the allocation; if missing or `status != "published"` → `404 "Results not found"`
   (same opaque message the existing public read uses — never reveal drafts).
2. Find the participant by **case-insensitive** email within the allocation's event
   (`Participant.event_id == allocation.event_id`).
3. Resolve their team in this allocation (via `TeamMember` → `Team` where
   `Team.allocation_id == allocation.id`).
4. If no matching participant, or they're not on a team in this allocation → `404 "Not found on this event"`.
5. Return the matched team as **`PublicTeam`** (id, name, fairness_score, members =
   `PublicTeamMember[]` — name/normalized_strength/experience_level, no email), exactly like the
   teams in the existing `PublicAllocationOut`.

Request schema `FindTeamRequest { email: EmailStr }` added to `app/schemas/allocation.py`.

### Frontend — `components/results/find-my-team.tsx` (new) + results page
- `find-my-team.tsx` (client component): an email `Input` + "Find my team" `Button`. On submit,
  `POST`s to the endpoint via `fetchAPI` (no token — public).
  - Success → a highlighted card: *"You're on **{team.name}** — with {teammate names}."*
  - 404 → *"We couldn't find that email on this event. Check the address you registered with."*
  - Other error → a generic error line.
- `app/results/[allocationId]/page.tsx` (server component): render `<FindMyTeam allocationId={allocationId} />`
  near the top, above the full team grid (which is unchanged).

## Error Handling
- All not-found cases (bad allocation, unpublished, unknown email) return 404 with a non-revealing
  message so the endpoint can't be used to distinguish "draft exists" from "email not registered"
  beyond what the public page already shows.
- Frontend treats any non-200 as "not found / try again"; no stack traces surfaced.

## Testing
- Backend (`tests/test_find_my_team.py`): published allocation + registered email → returns that
  participant's team (name + members); unknown email → 404; **unpublished** allocation → 404;
  email match is **case-insensitive**.
- Frontend (`tests/components/find-my-team.test.tsx`): renders the input+button; mocked success
  shows the team name + a teammate; mocked 404 shows the not-found message.
- Gates: `pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Deferred to B2 (recorded, not built here)
- Registration gains an optional `npub`; only npub-havers get DMs, everyone else uses find-my-team.
- On publish, best-effort NIP-04 DM to each participant's npub with their team + the results link,
  sent from a dedicated bot key (`SQUADSYNC_NSEC`), to relays from a configurable list.
- Settings **feedback box**: stores a feedback row in the DB and fires a best-effort NIP-04 DM
  from the bot key to the owner's `FEEDBACK_NPUB`. The owner's personal nsec is never stored.

## Out of Scope
- Authenticated/per-attendee identity for the lookup (email is the key).
- Editing/looking up across multiple allocations of one event (uses the given allocation).
