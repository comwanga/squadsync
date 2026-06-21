# SquadSync 🧠 Team Rationale Design

**Date:** 2026-06-20
**Status:** Approved
**Branch:** `feat/team-rationale` (off the self-custody payout work)
**Builds on:** `categorization_service` (the batched, abstention-tolerant Claude pattern,
cacheable system block) and the deterministic allocation engine.
**Context:** Audit aim — capitalize on AI in depth. Today AI only normalizes "Other"
strengths. This adds an **explainability layer**: a short, human-readable "why this team
works" per team, so organizers and participants trust the (otherwise opaque) deterministic
allocation. It is the foundation for later AI features (pairing, NL queries).

## Overview

A descriptive, **post-hoc** explanation of an allocation. It never reads into or changes the
deterministic engine — it narrates the result that already happened. The organizer clicks
**"Explain teams"**; SquadSync generates a structured rationale per team in one batched Claude
call, caches it on each team, and shows it in the engine view and on the public results page.

## Goals

- One short, structured rationale per team: a title, a one-sentence summary, strengths, and gaps.
- Generated **on demand** (not on every draft run), cached, and shown publicly.
- Built only from composition data the app already has; **never** sends or shows participant PII.
- Zero effect on allocation — determinism and reproducibility are untouched.

## Non-Goals

- Influencing allocation, scoring, or ranking teams (that is later "complementary pairing").
- Per-participant explanations ("why am I on this team") — team-level only for now.
- A deterministic non-AI fallback: when no API key is configured the feature is simply absent.
- Collecting `tech_stack`/`interests` (the form does not capture them yet; see Data reality).

## Decisions (locked)

- **Trigger:** on-demand `POST /allocations/{id}/rationale` from an "Explain teams" button. A fresh
  allocate/regenerate produces new team rows (no rationale); a manual `move_member` edit **clears**
  that allocation's rationales so a stale explanation never shows.
- **Storage:** a nullable `rationale` **JSON** column on `Team` holding
  `{title, summary, strengths: [...], gaps: [...]}`. Structured (not a rendered string) so the UI
  controls presentation and future features can read fields.
- **No-key behavior:** if `ANTHROPIC_API_KEY` is unset, the endpoint returns `400` "AI rationale
  requires ANTHROPIC_API_KEY"; the button surfaces "AI not configured". No template fallback.
- **Privacy:** the AI input contains **no names or emails** — only role/normalized strength,
  experience level, and `tech_stack`/`interests` when present. The prompt forbids naming
  individuals, so the output is PII-free by construction and safe on public results.
- **Model:** reuse the Haiku model id via a `RATIONALE_MODEL` setting (default
  `claude-haiku-4-5-20251001`).

## Data reality (tech_stack / interests)

The `participants.tech_stack` / `interests` columns exist and the API accepts them, but the
registration form never sets them, so they are empty for real participants. The rationale is
designed to lean on **roles, experience, and normalized strengths** (rich enough on their own)
and to fold in tech_stack/interests **only when non-empty**. Adding those form fields is a clean
follow-up (the "complementary pairing" track), out of scope here.

## Data model

- `teams.rationale` — new nullable `JSON` column (Alembic migration). `null` = not yet generated.

## Backend components

- **`app/services/rationale_service.py`**
  - `_build_request(event, teams_with_members) -> dict` (pure): one batched Messages API request.
    Static instructions + output contract in a **cacheable system block**; per-team composition
    (PII-free) in the user message; a tool schema returning
    `{rationales: [{team_id, title, summary, strengths[], gaps[]}]}`.
  - `_parse_rationales(content_blocks) -> dict[team_id, dict]` (pure): extract + validate.
  - `generate(db, allocation) -> dict[team_id, dict]`: gather each team's members (roles,
    experience, normalized strength, optional tech_stack/interests), call Claude, persist
    `Team.rationale`, return the map. Raises a typed `RationaleUnavailable` when no key is set.
- **`allocation_engine.move_participant`** — clear `rationale` on the allocation's teams after an
  edit (it no longer describes the current composition).

## API (organizer-authenticated, under `/api/v1`)

- `POST /allocations/{allocation_id}/rationale` — generate + store + return
  `{team_id: {title, summary, strengths, gaps}}`. `400` when AI is not configured; `404`/`403`
  via the existing organizer guard.
- Public `GET /public/allocations/{allocation_id}` — extend `PublicTeam` with an optional
  `rationale` object (PII-free) so published results show the blurb.

## Frontend components

- **Engine view (`run-panel` / `results-grid` / `team-card`)** — an "Explain teams" button that
  calls the endpoint, then renders per team: title, one-sentence summary, and small
  strengths / gaps lists. A toast surfaces "AI not configured" on `400`.
- **Public results page** — render the same per-team blurb when a rationale exists.

## Data flow

1. Organizer runs/edits an allocation, then clicks "Explain teams".
2. Backend gathers PII-free composition per team → one batched Claude call → structured rationales.
3. Each `Team.rationale` is persisted; the response updates the engine view live.
4. On publish, the public results page renders the stored rationales (no extra AI call).
5. Re-running allocation yields fresh teams (no rationale); editing a team clears stale rationales.

## Error handling

- **No API key** → `400` "AI rationale requires ANTHROPIC_API_KEY"; button shows "AI not configured".
- **Claude/tool failure or a team omitted from the response** → that team simply has no rationale
  (the others still get one); never blocks the allocation or the page.
- **Malformed/oversized output** → batched + bounded `max_tokens`, mirroring categorization, so a
  large allocation cannot truncate the whole response.

## Testing

Backend (SQLite, matching existing suite):
- `_build_request` — system block is cacheable; the payload contains **no name/email**; tool enum
  shape; each team id present.
- `_parse_rationales` — keeps well-formed entries; drops malformed; tolerates an omitted team.
- `generate` — persists `Team.rationale`; raises `RationaleUnavailable` with no key.
- endpoint — organizer-only; `400` without a key; stores on teams; public surface includes it.
- `move_participant` clears the allocation's rationales.

Frontend: unit-test the rationale API call + the card rendering of title/summary/strengths/gaps;
the "AI not configured" toast path.

## Scope guardrails (YAGNI)

Team-level, descriptive, on-demand, cached, PII-free. No allocation influence, no per-person
explanations, no new data collection, no non-AI fallback.
