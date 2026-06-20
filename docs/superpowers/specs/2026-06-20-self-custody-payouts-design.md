# SquadSync ⚡ Self-Custody Payouts (client-side NWC) Design

**Date:** 2026-06-20
**Status:** Approved
**Branch:** `fix/payout-correctness` (off `main`)
**Builds on:** the shipped Lightning payout (`payout_service`, `lnurl_service`, `nwc_service`,
`bolt11` preimage verification, idempotent per-team `Payout`).
**Context:** Audit finding — the NWC spend credential currently transits the backend, so a
compromised server could drain any connected wallet (bounded only by the wallet's NWC budget).
This is not self-custodial-grade. It also makes the payout a long, blocking HTTP request that
can time out mid-send.

## Overview

Move the Lightning send **into the organizer's browser**. The server computes the deterministic
split and records a payout, but the browser holds the NWC credential, resolves each recipient's
invoice, performs the NIP-47 `pay_invoice`, and reports each result back. The server **verifies**
every reported preimage against the invoice's payment hash before recording `paid`. The NWC
secret never leaves the client.

This simultaneously resolves two audit findings: **self-custody** (server never sees the spend
key) and **blocking/timeout** (no server-side relay round-trips, so the HTTP request no longer
blocks on the network for the whole team).

## Goals

- The NWC spend credential is used only in the browser; the backend never receives it.
- The server remains the source of truth for the deterministic split and the payout receipt.
- Every `paid` item is backed by a server-verified preimage (`sha256(preimage) == payment_hash`).
- Per-member live status; failed/unverified items retryable from the browser.
- Backwards-compatible receipt: the public results summary is unchanged.

## Non-Goals

- Changing the split math, idempotency model, or the public summary shape.
- Removing `nwc_service` (kept as a reusable NIP-47 client; the browser reimplements the subset
  it needs). Server-side execution is retired from the live path.
- BOLT12 / zaps / on-chain (separate, build on this contract).

## Decisions (locked)

- **Where the secret lives:** only in the browser, in component state, for the duration of the
  payout. Never sent to the backend, never persisted, never logged.
- **Split authority:** the server computes `compute_split` and creates the `Payout` + `PayoutItem`
  rows in `pending`. The browser may not invent amounts; it pays the items the server created.
- **Invoice resolution:** done in the browser (LUD-16 → LNURL-pay callback → bolt11). No secret
  needed, and it keeps the server off the network during the send.
- **Proof:** the browser POSTs `{bolt11, preimage}` per item; the server recomputes the payment
  hash from the bolt11 and checks the preimage (`bolt11.preimage_matches`) before marking `paid`.
  A mismatch is recorded `unverified` (terminal), exactly as today.
- **Auth:** all payout endpoints stay organizer-authenticated (NIP-98).

## API (organizer-authenticated, under `/api/v1`)

- `POST /allocations/{id}/payouts` — body `{ team_id, total_sats, addresses? }` (**no `nwc`**).
  Pre-flight (split + every member has an address, spend ceiling, idempotency) unchanged; creates
  the `Payout` and `pending` `PayoutItem`s and returns them. **Does not send anything.**
- `POST /payouts/{payout_id}/items/{item_id}/result` — body `{ bolt11, preimage }`. Organizer-auth.
  Verifies the preimage; sets the item `paid` or `unverified`; rolls up `Payout.status`. Idempotent
  on an already-`paid` item (returns current state, never re-counts).
- `POST /payouts/{payout_id}/items/{item_id}/failed` — body `{ error }`. Marks an item `failed`
  so the browser can record a send that never produced a preimage (LNURL/relay/wallet error).
- `POST /payouts/{id}/retry` — retained for re-driving `failed` items (browser re-pays, re-reports).

The old server-side `nwc` body field and server execution are removed from `create_payout`.

## Backend components

- **`payout_service.create_pending(db, payout, splits)`** — write `pending` items, no network.
- **`payout_service.record_item_result(db, payout, item, bolt11, preimage)`** — verify + set
  `paid`/`unverified`, roll up status. Pure of network.
- **`payout_service.record_item_failed(db, payout, item, error)`** — set `failed`, roll up.
- `execute_payout` / `retry_failed` (server-side NWC) are removed from the API path.

## Frontend components

- **`lib/lightning.ts`** (new) — `resolveInvoice(address, sats)`: LUD-16 fetch + callback fetch
  → bolt11 (browser `fetch`). `payWithNwc(nwcUri, bolt11)`: parse URI, build + sign the kind-23194
  request (nostr-tools `finalizeEvent` + `nip04`), open a `WebSocket` to the relay, publish, await
  the kind-23195 response, decrypt, return the preimage. Bounded timeout.
- **`payout-modal.tsx`** — on "Send payout": `createPayout` (no nwc) → for each returned item,
  `resolveInvoice` → `payWithNwc` → POST `result` (or `failed`); update live status from the
  server's verified responses. Retry re-drives `failed` items.

## Data flow

1. Organizer opens the modal, enters sats, pastes NWC (stays in the browser).
2. `POST /payouts` → server returns the payout with `pending` items (id, address, amount).
3. Browser loops items: resolve invoice → NWC pay → POST `{bolt11, preimage}` (or `{error}`).
4. Server verifies each preimage, records `paid`/`unverified`/`failed`, rolls up status.
5. Public results show the same redacted receipt.

## Testing

Backend (SQLite, matching existing suite):
- `create_payout` returns `pending` items and sends nothing (no nwc accepted).
- `result` endpoint: valid preimage → `paid` + rollup `complete`; bad preimage → `unverified`;
  already-`paid` item is idempotent (no double count).
- `failed` endpoint marks the item and rolls up `partial`/`failed`.
- Auth: non-organizer is rejected on every new endpoint.

Frontend: unit-test `resolveInvoice` URL/amount construction and the NWC request-event build
(mocked `fetch`/`WebSocket`). The relay round-trip itself is covered by manual mainnet verification.

## Scope guardrails (YAGNI)

Same split, same receipt, same idempotency. Only the *location* of the send and the secret moves
to the client; the server's new job is to verify proofs and keep the receipt.
