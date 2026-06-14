# In-App User Guide + One-Time Onboarding Nudge

**Date:** 2026-06-14
**Status:** Approved design (pending spec review)
**Branch:** `feat/user-guide-onboarding` (off `feat/ai-team-categorization`)

## Overview

New users land on the Overview page after Nostr login with no guidance on how
SquadSync works. This feature adds:

1. A **Guide** page under Settings — a scrollable, screenshot-driven walkthrough
   of the full golden path. Always available.
2. A one-time **"Quick guide"** pill beside the **New Event** button on the
   Overview page, with a highlight dot that appears only until first interaction
   (remembered in `localStorage`). After that the dot is gone for good; the quiet
   pill remains as a shortcut, and the guide is always reachable from Settings.

## Goals
- Zero-friction onboarding for first-time users.
- A durable, always-available how-to under Settings.
- The nudge grabs attention exactly once, then gets out of the way.

## Non-Goals
- No backend/per-account persistence (localStorage only).
- No video, no interactive product tour — static screenshots + captions.
- No new sidebar entry (the guide lives under Settings).

## Dependency
Screenshots must reflect the **new** registration UI (Primary Strength /
Experience) and logo, which exist on `feat/ai-team-categorization` (PR #11).
This branch is cut from that branch and should merge **after / together with**
PR #11 so the guide matches the shipped UI.

## Components

### 1. Guide content (single source of truth)
`frontend/lib/guide-steps.ts` exports an ordered array:
```ts
export interface GuideStep { id: string; title: string; caption: string; image: string; }
export const GUIDE_STEPS: GuideStep[] = [ ... ];
```
`image` paths point at `frontend/public/guide/NN-*.png`.

Golden-path steps (each = one screenshot + caption):
1. Sign in with Nostr
2. Create an event (title + description — description improves team grouping)
3. Activate the event
4. Share the registration QR code
5. Attendees register (Primary Strength + Experience; "Other" for anything)
6. (Optional) Configure balancing weights / strength constraints
7. Generate teams
8. Publish & share results

### 2. Guide page + Settings entry
- Route: `frontend/app/dashboard/settings/guide/page.tsx` — renders `GUIDE_STEPS`
  as numbered sections (each: `next/image` screenshot + title + caption), with a
  "← Back to Settings" link. Server component (static content).
- Settings page (`settings/page.tsx`): add a **Guide card** ("Learn how SquadSync
  works — step by step") linking to `/dashboard/settings/guide`.

### 3. One-time "Quick guide" knob
- `frontend/components/onboarding/quick-guide-button.tsx` (client component):
  - Renders a small secondary pill `Quick guide` linking to
    `/dashboard/settings/guide`.
  - Shows a highlight dot/pulse only when `localStorage["squadsync.guideSeen"]`
    is absent. Reads the flag in `useEffect` (SSR-safe; dot defaults hidden on
    first paint to avoid hydration mismatch, then appears after mount if unseen).
  - On click, sets `localStorage["squadsync.guideSeen"] = "1"` so the dot never
    shows again. The pill itself persists (quiet) regardless.
- Rendered beside the New Event button in `frontend/components/events/events-view.tsx`.

### 4. Screenshot capture (reproducible)
A Playwright script (new `scripts/capture-guide.mjs`, adapting the existing
`golden-path.mjs` / `e2e` harness) that:
- boots the migrated SQLite backend + Next dev server (reusing the
  `playwright.config.ts` webServer pattern),
- logs in with a generated Nostr key,
- walks the golden path, calling `page.screenshot()` at each step,
- writes PNGs to `frontend/public/guide/`.

Run manually (documented in the script header); the committed PNGs are the
artifacts the guide ships. Not part of CI.

## Testing
- Vitest:
  - `quick-guide-button.test.tsx`: dot shown when flag absent; after click the
    flag is set and dot hidden (localStorage mocked).
  - `guide-page` (or guide-steps): renders one section per `GUIDE_STEPS` entry.
- `tsc --noEmit` clean, `lint` clean, production `build` succeeds.

## Out of Scope
- Backend persistence of "seen" state.
- Localization of guide copy.
- Auto-refreshing screenshots in CI.
