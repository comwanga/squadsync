# SquadSync ⚡ Lightning Prize Splitting (NWC) Design

**Date:** 2026-06-17
**Status:** Approved
**Branch:** `feat/lightning-payout` (off `main`)
**Builds on:** `nostr_service` (NIP-04 `encrypt_nip04`/`decrypt_nip04`, `bech32_decode`, Schnorr
signing, `websockets.sync.client` relay helper) — already shipped for feedback/team-notify.
**Context:** bitcoin++ Open Source Edition hackathon (Nairobi). Adds real Bitcoin (Lightning)
to an otherwise Nostr-only app. Targets the main competition and the Nostr/Soapbox angle.

## Overview

After teams are formed, an organizer marks one team as the **winner**, enters a prize amount in
**sats**, connects a Lightning wallet via a **Nostr Wallet Connect (NWC / NIP-47)** string, and
SquadSync splits the pot evenly and pays each winner's Lightning address **live**. The
deterministic allocation engine is untouched — this is a bolt-on at the results stage.

## Goals

- One-click even split of a sats prize across a winning team's members.
- Pay each member's Lightning address programmatically over NWC (NIP-47 `pay_invoice`).
- Resolve each member's Lightning address from their Nostr `kind:0` profile (`lud16`), with an
  editable fallback field captured at registration.
- Show live per-member payment status (paid + preimage / failed + reason); retry failed items.
- Persist a payout receipt for verifiability; surface it on the public results page.

## Non-Goals

- Multi-currency, fee configuration, scheduled/recurring payouts.
- Per-member custom amounts (even split only; deterministic remainder).
- Multiple simultaneous winning teams (one team per payout).
- On-chain payments, swaps, or fiat off-ramp.
- Persisting the NWC credential (it is a spend credential — used transiently, never stored).

## Decisions (locked)

- **Payment rail:** NWC (NIP-47). Organizer pastes a `nostr+walletconnect://…` string per payout
  request. Backend performs `pay_invoice`, reusing existing NIP-04 + relay plumbing.
- **Recipient address:** auto-resolve `lud16` from the member's Nostr `kind:0` profile; if absent,
  use the optional `lightning_address` captured at registration (prefilled in the form from the
  logged-in user's own profile, editable). Stored as a plain string; validated as `name@domain`.
- **Split:** integer even split of `total_sats` over N members. Remainder sats assigned
  deterministically to the first members (ordered by participant id) so the full pot is paid and
  the result is reproducible. Each per-member amount must satisfy the recipient LNURL's
  `minSendable`/`maxSendable` (msat) or that item fails pre-flight.
- **Winner selection:** organizer marks a team within a published allocation as winner; stored as
  a `team_label` snapshot on the `Payout` (not a hard FK to a regenerable team row).
- **Security:** payout endpoints are organizer-authenticated (NIP-98, existing dependency). The
  NWC string is accepted in the request body, used in-memory, and never logged or persisted.

## Data model

- `participants.lightning_address` — new nullable `String` column (Alembic migration).
- `Payout` (`app/models/payout.py`): `id`, `event_id` (FK), `allocation_id` (FK), `team_label`,
  `total_sats`, `status` (`pending`/`partial`/`complete`/`failed`), `created_at`.
- `PayoutItem`: `id`, `payout_id` (FK), `participant_id` (FK), `lightning_address`, `amount_sats`,
  `status` (`pending`/`paid`/`failed`), `bolt11` (nullable), `preimage` (nullable),
  `error` (nullable), `created_at`.

Persisting the payout gives a verifiable receipt (the "does it work" judging axis) and a public
proof rendered on `/results/{allocation_id}`.

## Backend components

- **`app/services/lnurl_service.py`** — `resolve_lnurl(address) -> LnurlParams` (build
  `https://{domain}/.well-known/lnurlp/{name}`, GET, parse `callback`/`minSendable`/`maxSendable`);
  `request_invoice(params, amount_msat) -> bolt11` (GET `callback?amount=…`, parse `pr`). Uses
  `httpx`. Each function raises a typed error captured per item; never aborts the batch.
- **`app/services/nwc_service.py`** — parse the NWC URI (`wallet_pubkey`, `relay`, `secret`);
  build + Schnorr-sign a kind `23194` request event whose content is `encrypt_nip04`-encrypted
  `{"method":"pay_invoice","params":{"invoice":bolt11}}` to the wallet pubkey; open one
  `websockets.sync.client` connection, publish the EVENT, `REQ` for the kind `23195` response
  authored by the wallet, `decrypt_nip04` it, return `{preimage}` or `{error}`. Bounded timeout;
  reuses the existing relay-connection pattern.
- **`app/services/payout_service.py`** — `compute_split(participants, total_sats)`; orchestrate:
  resolve address → LNURL → invoice → NWC pay, writing `PayoutItem` status transitions; roll the
  `Payout.status` up to `complete`/`partial`/`failed`.

## API (organizer-authenticated, under `/api/v1`)

- `POST /allocations/{id}/payouts` — body `{ team_id, total_sats, nwc, addresses?: {participant_id:
  lightning_address} }`. The optional `addresses` map lets the organizer fill/correct a member's
  Lightning address in the modal (overrides the registration value). Pre-flight: compute split,
  resolve addresses; if any address is still missing, return `422` listing those members **before**
  spending. On success, executes payments and returns the `Payout` with per-item results.
- `POST /payouts/{id}/retry` — body `{ nwc }`; retries only `failed` items.
- Public `GET /public/results/{allocation_id}` — extended to include a redacted payout summary
  (amounts, masked addresses, paid/failed counts); no NWC, no preimages-as-secrets beyond display.

## Frontend components

- **Registration form** — add an optional "Lightning address" field; on mount, resolve the logged-in
  user's own `kind:0` `lud16` (via existing Nostr client / extension) and prefill it, editable.
- **Results page (organizer view)** — per team: "Mark winner & pay out" → modal:
  total sats input, NWC string paste, computed split + resolved/missing addresses (inline edit),
  "Send payout" → live per-member status list (✅ paid + short preimage / ❌ failed + reason),
  "Retry failed" button.
- **Public results** — small "⚡ Prize paid" badge + redacted payout summary when a payout exists.

## Data flow

1. Organizer (NIP-98) opens results → "Mark winner & pay out" on a team → enters total sats →
   pastes NWC string.
2. App resolves each member's address (profile-prefilled, editable) → shows split + any gaps.
3. "Send payout" → per member: LNURL resolve → request invoice → NWC `pay_invoice` → status.
4. `Payout`/`PayoutItem` persisted; failed items retryable; public results shows the receipt.

## Error handling

- **Missing address** → flagged in `422` pre-flight (before any spend); organizer fills it inline
  via the `addresses` override and re-submits. (Skip-and-re-split is out of scope.)
- **LNURL failure / amount below `minSendable` / above `maxSendable`** → that item `failed`,
  others continue.
- **NWC timeout / wallet error response** → item `failed` with the wallet's error; "Retry failed".
- **NWC string accepted per-request**, used transiently, never logged or persisted.

## Testing

Backend (SQLite, matching existing suite):
- `compute_split` — even split + deterministic remainder; re-split after a skip; N=1 edge.
- `lnurl_service` — URL construction from `lud16`; parse `callback`/min/max; invoice extraction;
  amount-out-of-bounds error (mocked `httpx`).
- `nwc_service` — URI parse; request event built/signed/encrypted correctly; response decrypt to
  `{preimage}` and to `{error}` (mocked relay socket).
- `payout_service` / endpoint — pre-flight `422` on missing address; status roll-up
  `complete`/`partial`/`failed`; retry touches only `failed` items; NWC never persisted.

Manual stage demo on **mainnet with tiny amounts** (e.g. 21 sats/member) for maximum swag.

## Scope guardrails (YAGNI)

Even split only, one winning team, one click, no fee/currency config, no scheduling, NWC never
stored. Everything else is out of scope for the hackathon build.
