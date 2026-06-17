# Nostr-Send Infra + Feedback Box (B2a) Design

**Date:** 2026-06-17
**Status:** Approved design (pending spec review)
**Branch:** `feat/nostr-feedback` (off `main`)
**Scope note:** **B2a** of two. **B2b** (next): optional `npub` at registration + DM each attendee
their team on publish — built on this same `nostr_service`. B2a builds the send infra and proves
it end-to-end with the smallest consumer (the Settings feedback box).

## Overview

Add the server-side ability to send an encrypted Nostr DM (NIP-04) from a dedicated **bot key**
to a recipient **npub**, and use it for a Settings **feedback box**: organizers submit feedback,
which is **stored in the DB** (source of truth) and best-effort **DM'd to the owner's npub**.

## Goals
- A reusable, provider-agnostic Nostr-send service that never blocks or breaks the caller.
- A working feedback channel that doesn't lose data if relays drop the message.
- Run fine when Nostr is unconfigured (no key → no-op).

## Non-Goals (B2a)
- npub at registration, team-notify on publish (B2b).
- Reading/inbox of DMs, NIP-17, multi-recipient fan-out, retries/queues.
- A feedback admin UI (rows are queryable; DM is the notification).

## Decisions (locked)
- Protocol **NIP-04** (kind 4). Sender = **bot `nsec`** (env); recipient = **npub** (env).
- Inputs are **bech32** (`nsec1…` / `npub1…`), decoded in-repo (no new dep).
- Sends are **fire-and-forget** via FastAPI `BackgroundTasks` (best-effort, logged, never fail the request).
- Feedback is **persisted in the DB** and DM'd; DB is source of truth.
- Default relays: `wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band` (env-overridable).

## Components

### 1. `backend/app/services/nostr_service.py` (new)
- `_bech32_decode(s) -> bytes`: minimal bech32 decode for `npub`/`nsec` → 32-byte key. (Self-contained; ~40 lines.)
- `send_dm(recipient_npub: str, message: str) -> bool`: best-effort, returns whether ≥1 relay accepted; **never raises**.
  - If `settings.SQUADSYNC_NSEC` is falsy → log + return `False` (unconfigured no-op).
  - Decode bot privkey (from nsec) and recipient x-only pubkey (from npub).
  - **NIP-04 encrypt**:
    - ECDH shared secret = secp256k1 ECDH of bot priv with recipient pubkey (compressed `02||x`),
      taking the **raw 32-byte X** (coincurve `ecdh(pub, hashfn=lambda x, y: x)`).
    - AES-256-CBC (cryptography) with a random 16-byte IV; PKCS7 pad.
    - `content = base64(ciphertext) + "?iv=" + base64(iv)`.
  - Build event `{ pubkey: bot_xonly_hex, created_at, kind: 4, tags: [["p", recipient_hex]], content }`,
    compute `id = sha256(serialized)` (NIP-01 serialization), `sig = schnorr_sign(id)` (coincurve).
  - Publish: for each relay in `settings.nostr_relays`, open a websocket (short timeout), send
    `["EVENT", event]`, read one frame for an OK; swallow per-relay errors. Return `True` if any accepted.
- A pure helper `encrypt_nip04(bot_privkey_bytes, recipient_xonly_bytes, message) -> str` so the
  crypto is unit-testable without network, plus a `decrypt_nip04(...)` used only by the round-trip test.

### 2. `backend/app/core/config.py`
Add: `SQUADSYNC_NSEC: str | None = None`, `FEEDBACK_NPUB: str | None = None`,
`NOSTR_RELAYS: str = "wss://relay.damus.io,wss://nos.lol,wss://relay.nostr.band"`, and a
`nostr_relays` property splitting on comma. Document in `render.yaml` + `DEPLOYMENT.md` (all optional).

### 3. Feedback model + migration `0005`
`backend/app/models/feedback.py`: `Feedback { id (uuid pk), user_id (FK users.id), message (Text), created_at }`.
Alembic `0005_feedback` creates the table.

### 4. Feedback API — `backend/app/api/v1/feedback.py` (new), mounted at `/api/v1/feedback`
`POST /api/v1/feedback` (auth required), body `{ message: str (1..2000) }`:
- Persist a `Feedback` row for `current_user`.
- If `FEEDBACK_NPUB` set, `background_tasks.add_task(send_dm, FEEDBACK_NPUB, f"SquadSync feedback from {current_user.pubkey}:\n\n{message}")`.
  (The submitter is identified by their raw hex pubkey — we only need a bech32 *decoder* for the
  bot/recipient keys, not an *encoder*, so no npub-encoding is required.)
- Return `201 { "detail": "received" }`. Sending never blocks or fails this response.

Register the router in `app/main.py` at prefix `/api/v1/feedback`.

### 5. Frontend — feedback card on Settings (`app/dashboard/settings/page.tsx`)
A "Send feedback" `Card`: a `textarea` + "Send" `Button`. On submit → `POST /api/v1/feedback`
(authenticated via the session token, like other dashboard calls) → toast "Thanks for the feedback!"
and clear the box. Disable while sending; show an error toast on failure.

## Error Handling
- `send_dm` and all relay I/O are wrapped so failures log and return `False` — they never propagate
  to the feedback request (which has already persisted the row and returned).
- Unconfigured (`SQUADSYNC_NSEC`/`FEEDBACK_NPUB` unset): feedback still persists; the DM is skipped.

## Testing
- **`nostr_service`** (no network): `encrypt_nip04` → `decrypt_nip04` round-trip recovers the message;
  bech32 decode of a known `npub`/`nsec` test vector yields the expected 32-byte hex; `send_dm`
  returns `False` and does not raise when `SQUADSYNC_NSEC` is unset (monkeypatched).
- **Feedback API**: `POST` with auth persists a row and returns 201 (relay/`send_dm` mocked so no
  network); without auth → 401/403; over-long message → 422.
- **Frontend**: feedback card renders; submit calls the API (fetch/`fetchAPI` mocked).
- Gates: `pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Migration
Single Alembic `0005_feedback` (additive table). No data backfill.

## Out of Scope (→ B2b / later)
- npub at registration, team-notify on publish.
- DM retries/queue, delivery receipts, NIP-17, reading DMs.
- Feedback moderation/admin views.
