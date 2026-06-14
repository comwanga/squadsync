# AI-Assisted, Deterministic Team Categorization

**Date:** 2026-06-14
**Status:** Approved design (pending spec review)

## Overview

SquadSync forms balanced teams for any event, but the registration flow and
allocation engine are currently **developer-centric**: participants must pick a
"Preferred Role" from a hard-coded list of 10 software roles
(`frontend`, `backend`, `ai_ml`, …), and the engine balances on that enum.

This change makes SquadSync usable by **any team for any event** while keeping
team formation **deterministic, explainable, and reproducible**:

- Registrants pick a **Primary Strength** from a universal, event-agnostic list,
  or choose **Other** and type their own in natural language.
- Claude (Haiku 4.5) **normalizes only the free-text "Other" entries** in the
  background — mapping them to the nearest universal category, using the event
  description for context. The common path never calls AI.
- The existing **deterministic allocation engine** balances teams on the
  resulting category + experience. Claude never builds teams.
- The organizer can **override any participant's category inline** in the
  attendees table if they disagree.

This matches the launch-readiness audit's position that the allocation engine is
a strategic asset and must remain predictable.

## Goals

- Remove the developer-only framing; work for hackathons, sports days, study
  groups, corporate workshops, etc.
- Zero-friction onboarding: the vast majority of registrants tap one option.
- "Intelligent" handling of unusual professions without sacrificing
  determinism, reproducibility, or offline operability.
- Human-reviewable: organizer can correct any AI/preset categorization.

## Non-Goals

- Claude does **not** create teams or decide team composition.
- No emergent/per-event AI-generated category taxonomy (the universal set is
  fixed; AI only maps Other → that set).
- No notifications system (the dead topbar bell is removed, not implemented).
- No multi-select strengths (single Primary Strength per participant).

## User Flows

### Registrant (scan QR → join)
1. Enters Name, Email, Phone (optional).
2. Picks **Primary Strength** from the universal list, or **Other** → a text
   box appears to type their profession/skill.
3. Picks **Experience**: Beginner / Intermediate / Advanced.
4. Submits.

### Organizer
1. Creates an event with **Title** + **Description** (description is prominent
   and strongly encouraged — it is the AI's context for Other normalization).
2. Watches registrations arrive in the attendees table; each row shows the
   participant's **category** (preset value, or AI/fallback-normalized Other).
3. Optionally **edits any participant's category inline** if they disagree.
4. Generates teams. Before allocation runs, the backend **auto-normalizes** any
   not-yet-normalized, non-overridden Other entries in the background.

## Universal "Primary Strength" Set

Single-choice, event-agnostic (labels editable later; these are the defaults):

- `technical` — Technical / Hands-on
- `design` — Design / Creative
- `planning` — Planning / Strategy
- `coordination` — Coordination / Operations
- `communication` — Communication / Outreach
- `research` — Research / Analysis
- `domain_expert` — Domain Expert
- `other` — Other (type your own)

The canonical list lives in **one shared place** the backend owns (a Python
enum/constant exposed via an API or mirrored constant) so the form, validation,
AI prompt, and engine never drift.

## Data Model

### `Event`
- No schema change. `description` already exists; the create form makes it
  prominent and encourages it.

### `Participant` (migration required)
Replace developer-centric fields:

| Old | New | Notes |
|---|---|---|
| `role` (enum, 10 dev roles) | `primary_strength` (String) | one of the universal values, or `other` |
| — | `strength_other` (Text, nullable) | the free text when `primary_strength = other` |
| — | `normalized_strength` (String, nullable) | category used by the engine; for presets = `primary_strength`; for Other = AI/fallback result |
| — | `strength_source` (String) | `preset` \| `ai` \| `fallback` \| `manual` — `manual` is never overwritten by re-normalization |
| `skill_level` (enum: beginner/intermediate/advanced/professional) | `experience_level` (enum: beginner/intermediate/advanced) | 4 → 3 levels |
| `years_experience` (int) | removed | experience level subsumes it |

`tech_stack` / `interests` (JSON, unused by the form) are left untouched to
limit migration scope.

## AI Normalization Service (Other only)

New `app/services/categorization_service.py`:

- **Input:** event title + description, the universal category set, and the list
  of participants whose `primary_strength = other` and `strength_source` is not
  `manual` and `normalized_strength` is unset.
- **Call:** Claude **Haiku 4.5** (`claude-haiku-4-5`) via the Anthropic SDK,
  using **tool-use / structured output** to return a strict
  `{participant_id → universal_category}` mapping (model must choose from the
  fixed set). Exact model id, params, and pricing confirmed via the `claude-api`
  skill at build time.
- **Persist:** sets `normalized_strength` and `strength_source = ai`.
- **Idempotent & deterministic downstream:** results are stored, so allocation
  reads fixed values and re-runs identically.

### Fallback / error handling
If `ANTHROPIC_API_KEY` is unset, or the API errors/times out:
- Each Other entry's `normalized_strength` = a slugified version of its
  `strength_other` text (its own bucket), `strength_source = fallback`.
- Allocation proceeds normally (just less semantic grouping).
- The failure is logged; no user-facing hard error.

## Allocation Engine Changes

`app/services/allocation_engine.py` (stays fully deterministic):

- Replace the `role` dimension with `normalized_strength` everywhere (anchors,
  role-constraint enforcement → "strength-constraint", buckets `roles` list).
- Update `_SKILL_MAP` to the 3-level scale; recompute `compute_composite_score`
  without `years_experience` (experience level is the sole experience input).
- Diversity balancing spreads each `normalized_strength` evenly across teams,
  as the role logic does today.

## API Endpoints

- **Registration** (`registration_service` / events register): accept
  `primary_strength`, optional `strength_other`, `experience_level`. On submit,
  if preset → `normalized_strength = primary_strength`, `strength_source = preset`.
- **Auto-normalize before allocation:** allocation entry point first calls the
  categorization service for pending Other entries, then runs the engine.
- **Inline override:** `PATCH /api/v1/events/{event_id}/participants/{participant_id}`
  sets `normalized_strength` and `strength_source = manual`.
- **Attendees list:** include `primary_strength`, `strength_other`,
  `normalized_strength` so the table can show + edit category.

## Frontend Changes

- **Registration form** (`registration-form.tsx`): replace role/skill-level
  dropdowns. Primary Strength = clearly-styled control + conditional Other text
  box; Experience = 3-option segmented control. Fixes the dark-mode visibility
  complaint.
- **Create-event dialog**: make Description prominent + encouraged (helper text
  explaining it improves team accuracy).
- **Attendees table** (`attendees/page.tsx`): show category column; allow inline
  edit (calls the override endpoint). Update "All roles" filter → strengths.
- **Topbar**: remove the non-functional bell button; leave the account menu.

## Configuration

- Backend env: `ANTHROPIC_API_KEY` (optional — absence triggers fallback).
- Document in `DEPLOYMENT.md` / `render.yaml` (`sync: false`).

## Testing

- **Engine** (deterministic, no AI): existing allocation tests updated for
  `normalized_strength` + 3-level experience; new cases for strength diversity
  balancing and the 3-level composite score.
- **Categorization service**: unit-tested with the Anthropic client mocked
  (valid mapping, malformed response, API error → fallback, no-key → fallback).
- **Override**: PATCH sets `manual` and survives re-normalization.
- **Frontend**: registration form renders new fields, Other reveals text box,
  validation; attendees inline edit.

## Migration

Single Alembic migration: rename/replace `role`→strength fields, `skill_level`→
`experience_level` (4→3). Pre-launch, so existing participant data may be reset
rather than back-filled.

## Out of Scope

- Notifications (bell removed).
- Multi-select strengths.
- Organizer-defined per-event taxonomies (universal set only).
- AI involvement in actual team assignment.
