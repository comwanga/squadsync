# Breadcrumb Navigation for Nested Dashboard Pages Design

**Date:** 2026-06-17
**Status:** Approved design (pending spec review)
**Branch:** `feat/breadcrumb-nav` (off `main`)

## Problem

The dashboard has only top-level global navigation (sidebar / mobile bottom-tabs →
Overview, Events, Settings). Once an organizer drills into an event's nested pages
(`/dashboard/events/[eventId]` and its `attendees` / `configure` / `engine` children),
there is **no upward or contextual navigation**: no breadcrumb trail and no "back to this
event" link. The only ways back to the specific event are the browser back button or the
sidebar (which lands on the top-level Events list, losing context). The Settings → Guide
page is the lone exception, with an ad-hoc `← Back to Settings` link.

## Goals

- Every nested dashboard page shows where it is and lets the user climb back to its parent(s).
- One reusable, accessible, responsive breadcrumb pattern across the app.
- Minimal, low-risk change: a presentational component dropped onto each nested page.

## Non-Goals

- Wizard-style Previous/Next stepping through the setup flow (explicitly deferred).
- Any change to the global sidebar / mobile tab bar.
- Navigation on the public attendee pages (`/join/[slug]`, `/results/[allocationId]`) — these
  are standalone landing pages and stay as-is.

## Components

### 1. `components/layout/breadcrumb.tsx` (new) — generic, presentational
- Props: `items: { label: React.ReactNode; href?: string }[]`. `label` is `ReactNode` so a
  caller can pass a skeleton element **or an icon + text** (e.g. `<><Settings/> Settings</>`) —
  no separate `icon` field is needed (would be redundant API surface; YAGNI).
- Renders semantic breadcrumb markup: `<nav aria-label="Breadcrumb"><ol>…</ol></nav>` with one
  `<li>` per segment. Items with an `href` render as Next `<Link>`s
  (`text-muted-foreground hover:text-foreground`); the **last** item renders as plain text with
  `aria-current="page"` (muted, not a link) regardless of whether it has an `href`.
- Segments separated by a `ChevronRight` icon (lucide), `aria-hidden`, inside the `<ol>` between
  items. The `<ol>` is `flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm` — `flex-wrap` so it
  never overflows on narrow screens, and an explicit **`gap-y-1`** so wrapped lines don't collide
  vertically.
- Pure/presentational — no data fetching. Independently testable.

### 2. `components/layout/event-breadcrumb.tsx` (new) — two event variants

Breadcrumbs are presentation-first: pages that already hold the event title feed it in
directly (no breadcrumb-initiated fetch). Only the two pages that have no other source for
the title self-resolve it. Both variants share private `items(...)` and skeleton helpers and
render the generic `<Breadcrumb>`.

Shared item-building rule:
- Always starts with `{ label: "Events", href: "/dashboard/events" }`.
- Then the event segment. If `current` is provided, the event segment is a link
  (`href: "/dashboard/events/{eventId}"`) and `{ label: current }` is appended as the leaf.
  If `current` is omitted, the event segment is the leaf (used on the event-detail page) —
  no `href`, so the generic component marks it `aria-current`.
- The event-title label is a **skeleton element**
  (`<span data-testid="breadcrumb-title-skeleton" aria-hidden class="inline-block h-4 w-24 align-middle rounded bg-muted animate-pulse" />`)
  whenever the title is unavailable, so swapping in the real title never does a text-swap
  flicker / layout jump.

- **`EventBreadcrumb({ eventId, title?, current? })` — pure (no data fetching).**
  Used by pages that already loaded the event (**event detail**, **attendees**). Renders the
  skeleton when `title` is `undefined` (e.g. attendees' first paint before its `useEvent`
  resolves), the real `title` otherwise. This is the component that satisfies "breadcrumbs are
  pure presentation" for the pages where the data is already in hand.

- **`EventBreadcrumbAuto({ eventId, current? })` — self-resolving (`"use client"`).**
  Used only by the two pages that don't otherwise load the event: the **engine** page (loads
  participants/allocations, not the event) and the **configure** page (a server component that
  loads nothing). Calls `useEvent(eventId)`; shows the skeleton while `isLoading`, falls back to
  the literal `"Event"` only if loading finished with no event (rare — the page itself 404s),
  else `event.title`. Self-resolving here is the pragmatic choice: forcing purity would mean a
  server-side fetch in Configure (extra round-trip + auth coupling) or a title-only fetch in
  Engine — both strictly worse than this small encapsulated reader.

### 3. Page integrations (one line each, at the top of the page content)
- `app/dashboard/events/[eventId]/page.tsx` (has `event` post-guard) →
  `<EventBreadcrumb eventId={eventId} title={event.title} />` (leaf = event title).
- `app/dashboard/events/[eventId]/attendees/page.tsx` (has `useEvent`) →
  `<EventBreadcrumb eventId={eventId} title={event?.title} current="Attendees" />`.
- `app/dashboard/events/[eventId]/engine/page.tsx` (no event load) →
  `<EventBreadcrumbAuto eventId={eventId} current="Allocation" />`.
- `app/dashboard/events/[eventId]/configure/page.tsx` (server component) →
  `<EventBreadcrumbAuto eventId={eventId} current="Configure" />` (a client island inside the
  server page).
- `app/dashboard/settings/guide/page.tsx` → replace the existing `← Back to Settings` link with
  the **generic** `<Breadcrumb items={[{ label: "Settings", href: "/dashboard/settings" }, { label: "Guide" }]} />`
  (no event fetch needed).

The breadcrumb renders **above** each page's existing `<h1>` title block; **the page `<h1>`
remains the primary heading — it is not shrunk or removed because the breadcrumb shows the title.**
The leaf segment uses the noun **"Allocation"** (not "Run Allocation") for consistency with
`Attendees` / `Configure` / `Guide`.

## Data Flow

`useEvent(eventId)` (existing `hooks/use-events` SWR hook returning `{ event, isLoading }`) is the
only data dependency, and only for `EventBreadcrumb`. The generic `Breadcrumb` is pure.

## Error / Edge Handling

- Event still loading or not found → title falls back to `"Event"`; the breadcrumb still renders
  and remains navigable. The page's own loading/not-found UI is unchanged.
- Long event titles: the breadcrumb wraps (flex-wrap); no truncation logic needed for v1.

## Testing (Vitest, `tests/components/`)

- `breadcrumb.test.tsx`:
  - renders every segment's label;
  - parent items (with `href`) are links pointing to the right path;
  - the last item is **not** a link and carries `aria-current="page"`.
- `event-breadcrumb.test.tsx`:
  - **`EventBreadcrumb` (pure, no mock needed):** with `title` set + `current`, the title is a
    link and `current` is the `aria-current` leaf; with `title` set and no `current`, the title
    is the leaf; with `title` undefined, the skeleton (`data-testid="breadcrumb-title-skeleton"`)
    renders.
  - **`EventBreadcrumbAuto` (mock `@/hooks/use-events` `useEvent`):** shows the resolved title +
    `current` leaf when loaded; shows the skeleton while `isLoading`; falls back to `"Event"` when
    loaded with no event.
- Gates: `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Out of Scope

- Wizard Previous/Next navigation through Attendees → Configure → Run Allocation.
- Truncation/ellipsis of very long titles (revisit only if it becomes a problem).
- Public attendee pages and the global nav.
