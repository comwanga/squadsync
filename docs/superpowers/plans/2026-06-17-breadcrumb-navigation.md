# Breadcrumb Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add breadcrumb navigation to every nested dashboard page so users can see where they are and climb back to the parent event / section.

**Architecture:** A generic presentational `Breadcrumb` component (semantic `<nav><ol>`, responsive wrap), plus a thin client `EventBreadcrumb` wrapper that reads the event title from the existing `useEvent` SWR hook (with a load skeleton to avoid layout shift). Both are dropped onto the four event pages and the guide page.

**Tech Stack:** Next.js 16 (App Router), React 19, Tailwind v4, lucide-react, Vitest + Testing Library.

**Spec:** `docs/superpowers/specs/2026-06-17-breadcrumb-navigation-design.md`
**Branch:** `feat/breadcrumb-nav` (already cut from `main`). Commit messages must NOT include any Co-Authored-By line.

**Verified facts (do not re-derive):**
- `hooks/use-events.ts` exports `useEvent(eventId: string | null)` returning `{ event, error, isLoading }`. `Event` has `{ id: string; title: string; ... }`.
- Existing pages and their current top-level structure:
  - `app/dashboard/events/[eventId]/page.tsx` (client) — has `eventId` (via `use(params)`), renders `<div className="space-y-6">` then a `<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">` header. Early-returns on loading/not-found before the main return.
  - `app/dashboard/events/[eventId]/attendees/page.tsx` (client) — has `eventId` and already calls `useEvent(eventId)`; renders `<div className="space-y-6"><div><h1 className="text-xl font-bold">Attendees</h1>…`.
  - `app/dashboard/events/[eventId]/engine/page.tsx` (client) — has `eventId`; renders `<div className="space-y-6"><div><h1 className="text-xl font-bold">Allocation Engine</h1>…`.
  - `app/dashboard/events/[eventId]/configure/page.tsx` (**server**, `async`) — has `eventId` (via `await params`); renders `<div className="space-y-6"><div><h1 className="text-xl font-bold">Configure Allocation</h1>…`. A client component (`EventBreadcrumb`) can be rendered inside it.
  - `app/dashboard/settings/guide/page.tsx` (server) — currently has a `← Back to Settings` `<Link>` (imports `Link`, `ArrowLeft`); `Link`/`ArrowLeft` are used ONLY for that back link. `Image` and `GUIDE_STEPS` are used elsewhere.
- Frontend tests run from `frontend/`: `npm test` (Vitest). Component tests live in `frontend/tests/components/`. Existing tests mock hooks via `vi.mock`. Heed `frontend/AGENTS.md` (modified Next.js 16) — this task uses only client components + existing hooks, no new Next routing APIs.

---

## File Structure

**Create:**
- `frontend/components/layout/breadcrumb.tsx` — generic presentational breadcrumb.
- `frontend/components/layout/event-breadcrumb.tsx` — client wrapper resolving the event title.
- `frontend/tests/components/breadcrumb.test.tsx`
- `frontend/tests/components/event-breadcrumb.test.tsx`

**Modify (one-line integrations):**
- `frontend/app/dashboard/events/[eventId]/page.tsx`
- `frontend/app/dashboard/events/[eventId]/attendees/page.tsx`
- `frontend/app/dashboard/events/[eventId]/configure/page.tsx`
- `frontend/app/dashboard/events/[eventId]/engine/page.tsx`
- `frontend/app/dashboard/settings/guide/page.tsx` (replaces the ad-hoc back link)

---

## Task 1: Generic `Breadcrumb` component

**Files:**
- Create: `frontend/components/layout/breadcrumb.tsx`
- Test: `frontend/tests/components/breadcrumb.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/tests/components/breadcrumb.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Breadcrumb } from "@/components/layout/breadcrumb";

describe("Breadcrumb", () => {
  it("renders all segment labels", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "My Event", href: "/dashboard/events/1" },
      { label: "Attendees" },
    ]} />);
    expect(screen.getByText("Events")).toBeInTheDocument();
    expect(screen.getByText("My Event")).toBeInTheDocument();
    expect(screen.getByText("Attendees")).toBeInTheDocument();
  });

  it("renders parent items (with href, not last) as links", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "Attendees" },
    ]} />);
    expect(screen.getByRole("link", { name: "Events" })).toHaveAttribute("href", "/dashboard/events");
  });

  it("renders the last item as the current page, not a link", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "Attendees" },
    ]} />);
    expect(screen.queryByRole("link", { name: "Attendees" })).toBeNull();
    expect(screen.getByText("Attendees")).toHaveAttribute("aria-current", "page");
  });

  it("never links the last item even if it has an href", () => {
    render(<Breadcrumb items={[
      { label: "Events", href: "/dashboard/events" },
      { label: "My Event", href: "/dashboard/events/1" },
    ]} />);
    expect(screen.queryByRole("link", { name: "My Event" })).toBeNull();
    expect(screen.getByText("My Event")).toHaveAttribute("aria-current", "page");
  });

  it("exposes a labelled breadcrumb nav", () => {
    render(<Breadcrumb items={[{ label: "Events", href: "/dashboard/events" }, { label: "X" }]} />);
    expect(screen.getByRole("navigation", { name: /breadcrumb/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- breadcrumb.test`
Expected: FAIL — cannot resolve `@/components/layout/breadcrumb`.

- [ ] **Step 3: Implement the component**

Create `frontend/components/layout/breadcrumb.tsx`:

```tsx
import { Fragment } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

export interface BreadcrumbItem {
  label: React.ReactNode;
  href?: string;
}

export function Breadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav aria-label="Breadcrumb">
      <ol className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
        {items.map((item, i) => {
          const isLast = i === items.length - 1;
          return (
            <Fragment key={i}>
              <li className="flex items-center">
                {item.href && !isLast ? (
                  <Link
                    href={item.href}
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span
                    className={isLast ? "font-medium text-foreground" : "text-muted-foreground"}
                    aria-current={isLast ? "page" : undefined}
                  >
                    {item.label}
                  </span>
                )}
              </li>
              {!isLast && (
                <li aria-hidden className="flex items-center text-muted-foreground/50">
                  <ChevronRight className="h-3.5 w-3.5" />
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- breadcrumb.test`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/breadcrumb.tsx frontend/tests/components/breadcrumb.test.tsx
git commit -m "feat(ui): add generic Breadcrumb component"
```

---

## Task 2: Event breadcrumb variants (`EventBreadcrumb` pure + `EventBreadcrumbAuto` self-resolving)

**Files:**
- Create: `frontend/components/layout/event-breadcrumb.tsx`
- Test: `frontend/tests/components/event-breadcrumb.test.tsx`

Two variants share a private item-builder + skeleton: a **pure** `EventBreadcrumb` (the page
passes the already-loaded `title`) and a **self-resolving** `EventBreadcrumbAuto` (reads the
title via `useEvent`, for pages that don't otherwise load the event).

- [ ] **Step 1: Write the failing tests**

Create `frontend/tests/components/event-breadcrumb.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EventBreadcrumb, EventBreadcrumbAuto } from "@/components/layout/event-breadcrumb";
import { useEvent } from "@/hooks/use-events";

vi.mock("@/hooks/use-events", () => ({ useEvent: vi.fn() }));
const mockUseEvent = useEvent as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => vi.clearAllMocks());

describe("EventBreadcrumb (pure)", () => {
  it("links the title and marks the current leaf", () => {
    render(<EventBreadcrumb eventId="e1" title="Hackathon 2026" current="Attendees" />);
    expect(screen.getByRole("link", { name: "Hackathon 2026" })).toHaveAttribute("href", "/dashboard/events/e1");
    expect(screen.getByText("Attendees")).toHaveAttribute("aria-current", "page");
  });

  it("uses the title as the leaf when no current is given", () => {
    render(<EventBreadcrumb eventId="e1" title="Hackathon 2026" />);
    expect(screen.queryByRole("link", { name: "Hackathon 2026" })).toBeNull();
    expect(screen.getByText("Hackathon 2026")).toHaveAttribute("aria-current", "page");
  });

  it("shows a skeleton when title is undefined", () => {
    render(<EventBreadcrumb eventId="e1" current="Attendees" />);
    expect(screen.getByTestId("breadcrumb-title-skeleton")).toBeInTheDocument();
    expect(screen.getByText("Attendees")).toBeInTheDocument();
  });
});

describe("EventBreadcrumbAuto (self-resolving)", () => {
  it("resolves the title and marks the current leaf", () => {
    mockUseEvent.mockReturnValue({ event: { id: "e1", title: "Hackathon 2026" }, isLoading: false });
    render(<EventBreadcrumbAuto eventId="e1" current="Configure" />);
    expect(screen.getByRole("link", { name: "Hackathon 2026" })).toHaveAttribute("href", "/dashboard/events/e1");
    expect(screen.getByText("Configure")).toHaveAttribute("aria-current", "page");
  });

  it("shows a skeleton while loading", () => {
    mockUseEvent.mockReturnValue({ event: undefined, isLoading: true });
    render(<EventBreadcrumbAuto eventId="e1" current="Allocation" />);
    expect(screen.getByTestId("breadcrumb-title-skeleton")).toBeInTheDocument();
    expect(screen.getByText("Allocation")).toBeInTheDocument();
  });

  it("falls back to 'Event' when loaded with no event", () => {
    mockUseEvent.mockReturnValue({ event: undefined, isLoading: false });
    render(<EventBreadcrumbAuto eventId="e1" current="Configure" />);
    expect(screen.getByText("Event")).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- event-breadcrumb.test`
Expected: FAIL — cannot resolve `@/components/layout/event-breadcrumb`.

- [ ] **Step 3: Implement both variants**

Create `frontend/components/layout/event-breadcrumb.tsx`:

```tsx
"use client";

import { useEvent } from "@/hooks/use-events";
import { Breadcrumb, type BreadcrumbItem } from "@/components/layout/breadcrumb";

// Fixed-size placeholder so swapping in the real title never shifts the layout.
const titleSkeleton = (
  <span
    data-testid="breadcrumb-title-skeleton"
    aria-hidden
    className="inline-block h-4 w-24 align-middle rounded bg-muted animate-pulse"
  />
);

function buildItems(
  eventId: string,
  titleLabel: BreadcrumbItem["label"],
  current?: string,
): BreadcrumbItem[] {
  const items: BreadcrumbItem[] = [
    { label: "Events", href: "/dashboard/events" },
    current
      ? { label: titleLabel, href: `/dashboard/events/${eventId}` }
      : { label: titleLabel },
  ];
  if (current) items.push({ label: current });
  return items;
}

// Pure presentation: the page supplies the title it already loaded. Renders a
// skeleton until `title` is defined (e.g. a client page's first paint).
export function EventBreadcrumb({
  eventId,
  title,
  current,
}: {
  eventId: string;
  title?: string;
  current?: string;
}) {
  return <Breadcrumb items={buildItems(eventId, title ?? titleSkeleton, current)} />;
}

// Self-resolving: for pages that don't otherwise load the event (the engine
// page and the server-rendered configure page). Skeleton while loading; "Event"
// only as a rare loaded-but-missing fallback (the page itself 404s then).
export function EventBreadcrumbAuto({
  eventId,
  current,
}: {
  eventId: string;
  current?: string;
}) {
  const { event, isLoading } = useEvent(eventId);
  const titleLabel: BreadcrumbItem["label"] =
    isLoading && !event ? titleSkeleton : (event?.title ?? "Event");
  return <Breadcrumb items={buildItems(eventId, titleLabel, current)} />;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- event-breadcrumb.test`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add frontend/components/layout/event-breadcrumb.tsx frontend/tests/components/event-breadcrumb.test.tsx
git commit -m "feat(ui): add EventBreadcrumb (pure) + EventBreadcrumbAuto (self-resolving)"
```

---

## Task 3: Integrate breadcrumbs into the pages

**Files (modify):**
- `frontend/app/dashboard/events/[eventId]/page.tsx`
- `frontend/app/dashboard/events/[eventId]/attendees/page.tsx`
- `frontend/app/dashboard/events/[eventId]/configure/page.tsx`
- `frontend/app/dashboard/events/[eventId]/engine/page.tsx`
- `frontend/app/dashboard/settings/guide/page.tsx`

> No new unit tests here — these are one-line wirings of already-tested components. Coverage is the `tsc` + `lint` + `build` gates in Step 6.

- [ ] **Step 1: Event detail page** (has `event` post-guard → pure variant with `title`)

In `frontend/app/dashboard/events/[eventId]/page.tsx`, add the import after the existing lucide import line (line 16, `import { Users, Settings, ... } from "lucide-react";`):

```tsx
import { EventBreadcrumb } from "@/components/layout/event-breadcrumb";
```

Then add the breadcrumb as the first child of the main return's outer `<div className="space-y-6">`, immediately before the header `<div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">`. `event` is guaranteed defined here (the page early-returns while loading / not-found):

```tsx
      <EventBreadcrumb eventId={eventId} title={event.title} />
```

- [ ] **Step 2: Attendees page** (already has `useEvent` → pure variant; `event?.title` may be undefined on first paint → skeleton)

In `frontend/app/dashboard/events/[eventId]/attendees/page.tsx`, add the import after the existing imports (e.g. after the `Skeleton` import):

```tsx
import { EventBreadcrumb } from "@/components/layout/event-breadcrumb";
```

Then make it the first child of the outer `<div className="space-y-6">` (before the `<div>` that holds `<h1>Attendees</h1>`):

```tsx
      <EventBreadcrumb eventId={eventId} title={event?.title} current="Attendees" />
```

- [ ] **Step 3: Configure page** (server component, loads no event → self-resolving `Auto` variant)

In `frontend/app/dashboard/events/[eventId]/configure/page.tsx`, add the import after the existing `ConfigForm` import:

```tsx
import { EventBreadcrumbAuto } from "@/components/layout/event-breadcrumb";
```

Then make it the first child of the outer `<div className="space-y-6">` (before the `<div>` that holds `<h1>Configure Allocation</h1>`):

```tsx
      <EventBreadcrumbAuto eventId={eventId} current="Configure" />
```

(`EventBreadcrumbAuto` is a client component; rendering it inside this server component is fine.)

- [ ] **Step 4: Engine page** (does not load the event → self-resolving `Auto` variant; leaf noun "Allocation")

In `frontend/app/dashboard/events/[eventId]/engine/page.tsx`, add the import after the existing imports (e.g. after the `ResultsGrid` import):

```tsx
import { EventBreadcrumbAuto } from "@/components/layout/event-breadcrumb";
```

Then make it the first child of the outer `<div className="space-y-6">` (before the `<div>` that holds `<h1>Allocation Engine</h1>`):

```tsx
      <EventBreadcrumbAuto eventId={eventId} current="Allocation" />
```

- [ ] **Step 5: Guide page — replace the ad-hoc back link with the shared Breadcrumb**

In `frontend/app/dashboard/settings/guide/page.tsx`:

Replace the first three import lines:
```tsx
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { GUIDE_STEPS } from "@/lib/guide-steps";
```
with:
```tsx
import Image from "next/image";
import { GUIDE_STEPS } from "@/lib/guide-steps";
import { Breadcrumb } from "@/components/layout/breadcrumb";
```

Replace the back-link block:
```tsx
        <Link href="/dashboard/settings" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to Settings
        </Link>
```
with:
```tsx
        <Breadcrumb items={[{ label: "Settings", href: "/dashboard/settings" }, { label: "Guide" }]} />
```

- [ ] **Step 6: Verify gates**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean (no output).

Run: `cd frontend && npm run lint`
Expected: 0 errors. (A pre-existing `react-hooks/incompatible-library` warning in `registration-form.tsx` is unrelated and may remain.)

Run: `cd frontend && npm test`
Expected: all tests pass (the new breadcrumb tests + existing suite).

Run: `cd frontend && npm run build`
Expected: build succeeds (all dashboard routes compile).

- [ ] **Step 7: Commit**

```bash
git add "frontend/app/dashboard/events/[eventId]/page.tsx" \
        "frontend/app/dashboard/events/[eventId]/attendees/page.tsx" \
        "frontend/app/dashboard/events/[eventId]/configure/page.tsx" \
        "frontend/app/dashboard/events/[eventId]/engine/page.tsx" \
        frontend/app/dashboard/settings/guide/page.tsx
git commit -m "feat(ui): breadcrumbs on event pages + guide"
```

---

## Final verification (after all tasks)

- [ ] `cd frontend && npx tsc --noEmit && npm run lint && npm test && npm run build` → all green.
- [ ] Manual sanity (optional): on a nested page (e.g. `…/engine`), the breadcrumb reads `Events / {title} / Allocation`; clicking `{title}` returns to the event, clicking `Events` returns to the list; at 360px width the trail wraps without overflow or vertical collision.
- [ ] Then use **superpowers:finishing-a-development-branch** to open the PR to `main`.

---

## Self-Review notes (plan author)

- **Spec coverage:** generic `Breadcrumb` with semantic `<nav><ol>`, `flex-wrap` + `gap-y-1`, last-item `aria-current` (Task 1); **pure** `EventBreadcrumb({ eventId, title?, current? })` (skeleton when title undefined) + **self-resolving** `EventBreadcrumbAuto({ eventId, current? })` (load skeleton + `"Event"` fallback) (Task 2); integration — detail/attendees use the pure variant fed by their own event data, engine/configure use `Auto` (Task 3); guide uses the generic `Breadcrumb`.
- **Review-driven adjustments folded in:** breadcrumbs are pure presentation where the page already has the title (detail, attendees) — no breadcrumb-initiated fetch; `Auto` self-resolves only where there's no other source (engine has no event load, configure is a server component). Skeleton (not a "Event"→title text swap) prevents flicker. Leaf noun is **"Allocation"** (not "Run Allocation"). No `icon` field — `label: ReactNode` already supports icon+text (YAGNI). Page `<h1>`s are preserved as primary headings.
- **Type consistency:** `BreadcrumbItem { label: React.ReactNode; href?: string }` defined in Task 1, imported in Task 2; `EventBreadcrumb` takes `title?` (string), `EventBreadcrumbAuto` takes no title — call sites in Task 3 match (detail/attendees pass `title=`, engine/configure pass none); skeleton `data-testid="breadcrumb-title-skeleton"` matches both the pure and Auto tests.
- **Placeholder scan:** none — every code step is complete.
- **Privacy/scope:** no public pages or global nav touched; no backend changes.
