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
- Props: `items: { label: React.ReactNode; href?: string }[]` (label is `ReactNode` so a
  caller can pass a skeleton element, not just a string).
- Renders semantic breadcrumb markup: `<nav aria-label="Breadcrumb"><ol>…</ol></nav>` with one
  `<li>` per segment. Items with an `href` render as Next `<Link>`s
  (`text-muted-foreground hover:text-foreground`); the **last** item renders as plain text with
  `aria-current="page"` (muted, not a link) regardless of whether it has an `href`.
- Segments separated by a `ChevronRight` icon (lucide), `aria-hidden`, inside the `<ol>` between
  items. The `<ol>` is `flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm` — `flex-wrap` so it
  never overflows on narrow screens, and an explicit **`gap-y-1`** so wrapped lines don't collide
  vertically.
- Pure/presentational — no data fetching. Independently testable.

### 2. `components/layout/event-breadcrumb.tsx` (new) — client wrapper
- `"use client"`. Props: `{ eventId: string; current?: string }`.
- Calls the existing `useEvent(eventId)` SWR hook to read the event title (already cached on
  these pages — no additional network request in practice).
- Builds the items array and renders `<Breadcrumb>`:
  - Always starts with `{ label: "Events", href: "/dashboard/events" }`.
  - Then the event: `{ label: title, href: "/dashboard/events/{eventId}" }`.
  - If `current` is provided, appends `{ label: current }` as the leaf (the event segment stays
    a link). If `current` is omitted, the event segment is the leaf (used on the event-detail
    page itself) — rendered without an `href` so it becomes the `aria-current` leaf.
- **Event-title rendering (avoid the SWR flash / layout shift):**
  - While `useEvent` is loading (`isLoading` true and no cached event), the event segment's
    `label` is a **skeleton element** — `<span class="inline-block animate-pulse bg-muted rounded h-4 w-24 align-middle" />`
    — not text, so swapping in the real title doesn't jump the layout.
  - If loading finished but no event was found, fall back to the literal string `"Event"`.
  - Otherwise use `event.title`.

### 3. Page integrations (one line each, at the top of the page content)
- `app/dashboard/events/[eventId]/page.tsx` → `<EventBreadcrumb eventId={eventId} />`
  (leaf = event title).
- `app/dashboard/events/[eventId]/attendees/page.tsx` → `<EventBreadcrumb eventId={eventId} current="Attendees" />`.
- `app/dashboard/events/[eventId]/configure/page.tsx` → `<EventBreadcrumb eventId={eventId} current="Configure" />`.
  (This page is a server component; `EventBreadcrumb` is a client island rendered inside it.)
- `app/dashboard/events/[eventId]/engine/page.tsx` → `<EventBreadcrumb eventId={eventId} current="Run Allocation" />`.
- `app/dashboard/settings/guide/page.tsx` → replace the existing `← Back to Settings` link with
  the **generic** `<Breadcrumb items={[{ label: "Settings", href: "/dashboard/settings" }, { label: "Guide" }]} />`
  (no event fetch needed).

The breadcrumb renders **above** each page's existing `<h1>` title block; the page titles stay.

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
- `event-breadcrumb.test.tsx` (mock `@/hooks/use-events` `useEvent`):
  - shows the event title and the `current` leaf when `current` is set;
  - when `current` is omitted, the event title is the leaf (no trailing segment);
  - shows the `"Event"` fallback when `useEvent` returns no event.
- Gates: `tsc --noEmit`, `npm run lint`, `npm test`, production `build`.

## Out of Scope

- Wizard Previous/Next navigation through Attendees → Configure → Run Allocation.
- Truncation/ellipsis of very long titles (revisit only if it becomes a problem).
- Public attendee pages and the global nav.
