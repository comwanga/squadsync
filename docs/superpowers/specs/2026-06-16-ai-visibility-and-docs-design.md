# Surface AI Categorization + Docs/Cleanup

**Date:** 2026-06-16
**Status:** Approved design (pending spec review)
**Branch:** `feat/ai-visibility-and-docs` (off `main`)

## Overview

The AI normalization of free-text "Other" strengths runs invisibly (background,
at allocation time), so users who set `ANTHROPIC_API_KEY` can't tell it's working
and the guide never mentions it. This change makes it visible and documents it:

1. **Counts in the API** — the allocation response reports how many participants
   were AI-categorized vs deterministically (fallback) categorized.
2. **UI surfacing** — a post-generation line on the results page, source **badges**
   in the Attendees table (AI / Auto / Manual), and an explanatory line + stale-copy
   fix on the engine page.
3. **Guide step** — a new walkthrough step explaining "Other → auto-categorized",
   with a fresh screenshot.
4. **README rewrite** + **redundant-file cleanup**.

## Goals
- Make the AI's effect observable (counts + per-row badges) without changing the
  background, zero-friction design.
- Distinguish real AI (`ai`) from the no-key fallback (`fallback`) honestly.
- Bring README and the guide in line with the current product.

## Non-Goals
- No change to *when*/*how* normalization runs (still background, at allocation).
- No new AI calls or models.
- No per-step AI progress streaming.

## Components

### Backend
- `app/services/categorization_service.py`: `normalize_pending(db, event_id)`
  returns `dict` `{"ai": int, "fallback": int}` (count of entries it set this run).
  Existing behavior otherwise unchanged; still never raises.
- `app/schemas/allocation.py`: `AllocationOut` gains `ai_normalized: int = 0` and
  `auto_normalized: int = 0` (defaults so list/get/public builders stay valid).
- `app/api/v1/allocation.py`: `_build_allocation_out` sets those two fields by
  counting the event's participants:
  - `ai_normalized` = participants with `strength_source == "ai"`
  - `auto_normalized` = participants with `strength_source == "fallback"`
  (Counts reflect the event's current state, so they're accurate on every read.)
  The `allocate` endpoint already calls `normalize_pending` before `run_allocation`;
  its return value is not required by the endpoint (counts come from the DB), but
  the function returns counts for unit-testability.

### Frontend
- `hooks/use-allocation.ts`: `Allocation` type gains `ai_normalized?: number` and
  `auto_normalized?: number`.
- `components/engine/results-grid.tsx`: when an allocation is shown, render a small
  note:
  - `ai_normalized > 0` → "🧠 AI categorized {n} free-text “Other” response(s)."
  - else if `auto_normalized > 0` → "{n} “Other” response(s) categorized automatically — set ANTHROPIC_API_KEY for AI."
  - else nothing.
- `components/attendees/attendees-table.tsx`: the Source cell renders a badge:
  - `ai` → "AI" (violet), `fallback` → "Auto" (gray), `manual` → "Manual" (blue),
    `preset` → plain muted text "preset".
- `components/engine/run-panel.tsx`: fix stale copy — `PASSES[0]` "Advanced /
  Professional" → "Advanced"; `PASSES[2]` "Role constraint enforcement" →
  "Strength constraint enforcement"; add a muted line under the participant count:
  "Free-text 'Other' strengths are categorized by AI before allocation."

### Guide
- `lib/guide-steps.ts`: **append** a final step (id `ai-categorize`,
  title "9. Behind the scenes: SquadSync sorts free-text answers",
  image `/guide/09-ai-category.png`). Appending avoids renumbering steps 1–8 and
  keeps the image filename aligned with its position.
- `scripts/capture-guide.mjs`: after publish, navigate to the Attendees page and
  capture `09-ai-category.png` (shows the "Agronomist" Other entry with its Source
  badge). Captured without a key locally → shows "Auto"; production shows "AI".
- `frontend/public/guide/09-ai-category.png`: the captured artifact.

### README (root)
Rewrite `README.md` to reflect: what SquadSync is; universal Primary Strengths +
free-text Other; AI-assisted-but-deterministic team formation; the in-app guide;
local dev (backend venv + alembic + uvicorn, frontend npm); single-branch `main`
deploy → Render (backend) + Vercel (frontend); `ANTHROPIC_API_KEY` optional.

### Cleanup (redundant tracked files)
- Delete root `screenshots/` (14 stale pre-redesign PNGs, superseded by
  `frontend/public/guide/`).
- Delete root `golden-path.mjs` (superseded by `scripts/capture-guide.mjs`).
- Verify nothing references them before deleting (grep repo).

## Testing
- Backend: `normalize_pending` returns `{"ai": n}` with key + mocked classify, and
  `{"fallback": n}` without key; an allocate integration check asserts
  `AllocationOut.ai_normalized` / `auto_normalized` reflect participant sources.
- Frontend: attendees badge shows correct label per `strength_source`; results note
  appears when `ai_normalized > 0` and shows the fallback variant otherwise.
- Gates: `pytest -q`, `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Out of Scope
- Streaming/progress UI for the AI call.
- Surfacing AI on the public results page.
- Changing the deterministic engine.
