# In-App User Guide + One-Time Onboarding Nudge — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a screenshot-driven Guide page under Settings plus a one-time "Quick guide" pill beside New Event so first-time users learn the SquadSync flow.

**Architecture:** A single `guide-steps.ts` data module drives a Settings sub-route guide page. A client `QuickGuideButton` shows a one-time highlight dot tracked in `localStorage`. Fresh screenshots are produced by a Playwright capture script (adapted from `golden-path.mjs`) into `frontend/public/guide/`.

**Tech Stack:** Next.js 16 (App Router, `next/image`, `next/link`), React, Vitest + Testing Library, Playwright (capture only).

**Spec:** `docs/superpowers/specs/2026-06-14-user-guide-onboarding-design.md`
**Branch:** `feat/user-guide-onboarding` (off `feat/ai-team-categorization`; merge after/with PR #11).

---

## File structure
- `frontend/lib/guide-steps.ts` — ordered step data (title, caption, image). One responsibility: content.
- `frontend/app/dashboard/settings/guide/page.tsx` — renders the steps.
- `frontend/app/dashboard/settings/page.tsx` — add a "Guide" card (modify).
- `frontend/components/onboarding/quick-guide-button.tsx` — the one-time pill.
- `frontend/components/events/events-view.tsx` — render the pill beside New Event (modify).
- `scripts/capture-guide.mjs` — Playwright capture (adapted from `golden-path.mjs`).
- `frontend/public/guide/*.png` — captured screenshots (artifacts).
- Tests: `frontend/tests/lib/guide-steps.test.ts`, `frontend/tests/components/quick-guide-button.test.tsx`.

---

## Phase 1 — Guide content data module

**Files:**
- Create: `frontend/lib/guide-steps.ts`
- Test: `frontend/tests/lib/guide-steps.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/tests/lib/guide-steps.test.ts
import { describe, it, expect } from "vitest";
import { GUIDE_STEPS } from "@/lib/guide-steps";

describe("GUIDE_STEPS", () => {
  it("has steps, each with the required fields", () => {
    expect(GUIDE_STEPS.length).toBeGreaterThanOrEqual(6);
    for (const s of GUIDE_STEPS) {
      expect(s.id).toBeTruthy();
      expect(s.title).toBeTruthy();
      expect(s.caption).toBeTruthy();
      expect(s.image).toMatch(/^\/guide\/.+\.png$/);
    }
  });

  it("has unique ids", () => {
    const ids = GUIDE_STEPS.map(s => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd frontend && npx vitest run tests/lib/guide-steps.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Create the data module**

```ts
// frontend/lib/guide-steps.ts
export interface GuideStep {
  id: string;
  title: string;
  caption: string;
  image: string; // path under /public
}

// Screenshots are 1280x800 (capture viewport); see scripts/capture-guide.mjs.
export const GUIDE_STEPS: GuideStep[] = [
  {
    id: "sign-in",
    title: "1. Sign in with Nostr",
    caption: "No account needed — connect with your Nostr identity to reach your dashboard.",
    image: "/guide/01-login.png",
  },
  {
    id: "create-event",
    title: "2. Create an event",
    caption: "Click New Event, give it a name, and add a description — the description helps SquadSync group attendees more accurately.",
    image: "/guide/02-create-event.png",
  },
  {
    id: "activate",
    title: "3. Open your event",
    caption: "Your new event opens to its dashboard, where you can activate it and manage everything.",
    image: "/guide/03-event-dashboard.png",
  },
  {
    id: "share-qr",
    title: "4. Share the registration QR code",
    caption: "Open Attendees to get a QR code and link. Share it so people can register themselves.",
    image: "/guide/04-attendees-qr.png",
  },
  {
    id: "register",
    title: "5. Attendees register",
    caption: "Each person picks a Primary Strength (or 'Other' to type their own) and an Experience level — works for any team, any event.",
    image: "/guide/05-join-form.png",
  },
  {
    id: "configure",
    title: "6. (Optional) Tune the balance",
    caption: "Configure balancing weights and per-team strength requirements if you want finer control.",
    image: "/guide/06-configure.png",
  },
  {
    id: "generate",
    title: "7. Generate teams",
    caption: "Run the engine to form balanced teams. Free-text 'Other' strengths are normalized automatically before allocation.",
    image: "/guide/07-engine-results.png",
  },
  {
    id: "publish",
    title: "8. Publish & share results",
    caption: "Publish to announce teams, then export CSV/PDF or share the public results link.",
    image: "/guide/08-published.png",
  },
];
```

- [ ] **Step 4: Run it, expect PASS**

Run: `cd frontend && npx vitest run tests/lib/guide-steps.test.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/guide-steps.ts frontend/tests/lib/guide-steps.test.ts
git commit -m "feat(guide): golden-path step content module"
```

---

## Phase 2 — Guide page + Settings entry

**Files:**
- Create: `frontend/app/dashboard/settings/guide/page.tsx`
- Modify: `frontend/app/dashboard/settings/page.tsx`

- [ ] **Step 1: Create the guide page**

```tsx
// frontend/app/dashboard/settings/guide/page.tsx
import Image from "next/image";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { GUIDE_STEPS } from "@/lib/guide-steps";

export default function GuidePage() {
  return (
    <div className="space-y-8 max-w-3xl">
      <div>
        <Link href="/dashboard/settings" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to Settings
        </Link>
        <h1 className="text-2xl font-bold tracking-tight mt-2">How SquadSync works</h1>
        <p className="text-sm text-muted-foreground mt-1">A quick walkthrough from sign-in to published teams.</p>
      </div>

      <ol className="space-y-10">
        {GUIDE_STEPS.map(step => (
          <li key={step.id} className="space-y-3">
            <h2 className="text-lg font-semibold">{step.title}</h2>
            <p className="text-sm text-muted-foreground">{step.caption}</p>
            <Image
              src={step.image}
              alt={step.title}
              width={1280}
              height={800}
              className="w-full h-auto rounded-lg border dark:border-slate-700"
            />
          </li>
        ))}
      </ol>
    </div>
  );
}
```

- [ ] **Step 2: Add a Guide card to the Settings page** — in `frontend/app/dashboard/settings/page.tsx`, add the imports and a new card after the Appearance card (before the closing `</div>`).

Add imports at the top (alongside existing imports):
```tsx
import Link from "next/link";
import { BookOpen, ChevronRight } from "lucide-react";
```

Insert this card immediately after the closing `</Card>` of the Appearance card:
```tsx
      <Link href="/dashboard/settings/guide" className="block">
        <Card className="transition-colors hover:border-primary/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <BookOpen className="h-5 w-5 text-primary" />
                <div>
                  <CardTitle className="text-base">Guide</CardTitle>
                  <CardDescription>Learn how SquadSync works — step by step</CardDescription>
                </div>
              </div>
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardHeader>
        </Card>
      </Link>
```

- [ ] **Step 3: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean (the pre-existing `react-hooks/incompatible-library` warning in unrelated files is acceptable; no new errors).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/dashboard/settings/guide/page.tsx frontend/app/dashboard/settings/page.tsx
git commit -m "feat(guide): Settings guide page + entry card"
```

---

## Phase 3 — One-time "Quick guide" knob

**Files:**
- Create: `frontend/components/onboarding/quick-guide-button.tsx`
- Modify: `frontend/components/events/events-view.tsx`
- Test: `frontend/tests/components/quick-guide-button.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/tests/components/quick-guide-button.test.tsx
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, beforeEach } from "vitest";
import { QuickGuideButton } from "@/components/onboarding/quick-guide-button";

beforeEach(() => localStorage.clear());

describe("QuickGuideButton", () => {
  it("renders a link to the guide", () => {
    render(<QuickGuideButton />);
    const link = screen.getByRole("link", { name: /quick guide/i });
    expect(link).toHaveAttribute("href", "/dashboard/settings/guide");
  });

  it("shows the highlight dot when not seen, hides it after click", async () => {
    render(<QuickGuideButton />);
    // Dot appears after mount (effect reads localStorage).
    await waitFor(() => expect(screen.getByTestId("guide-dot")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("link", { name: /quick guide/i }));
    expect(localStorage.getItem("squadsync.guideSeen")).toBe("1");
    await waitFor(() => expect(screen.queryByTestId("guide-dot")).not.toBeInTheDocument());
  });

  it("does not show the dot when already seen", async () => {
    localStorage.setItem("squadsync.guideSeen", "1");
    render(<QuickGuideButton />);
    await waitFor(() => {}, { timeout: 50 });
    expect(screen.queryByTestId("guide-dot")).not.toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd frontend && npx vitest run tests/components/quick-guide-button.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the component**

```tsx
// frontend/components/onboarding/quick-guide-button.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const SEEN_KEY = "squadsync.guideSeen";

export function QuickGuideButton() {
  // Default hidden so server and first client paint match (no hydration mismatch).
  const [showDot, setShowDot] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(SEEN_KEY) !== "1") setShowDot(true);
  }, []);

  const markSeen = () => {
    localStorage.setItem(SEEN_KEY, "1");
    setShowDot(false);
  };

  return (
    <Link
      href="/dashboard/settings/guide"
      onClick={markSeen}
      className={cn(
        "relative inline-flex items-center gap-1.5 rounded-md border border-input bg-background",
        "px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
      )}
    >
      <HelpCircle className="h-4 w-4" />
      Quick guide
      {showDot && (
        <span
          data-testid="guide-dot"
          aria-label="New"
          className="absolute -right-1 -top-1 flex h-2.5 w-2.5"
        >
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
        </span>
      )}
    </Link>
  );
}
```

- [ ] **Step 4: Run it, expect PASS**

Run: `cd frontend && npx vitest run tests/components/quick-guide-button.test.tsx`
Expected: PASS (3 tests).

- [ ] **Step 5: Render the pill beside New Event** — in `frontend/components/events/events-view.tsx`, add the import and wrap the actions. Replace:

```tsx
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { Skeleton } from "@/components/ui/skeleton";
```
with:
```tsx
import { CreateEventDialog } from "@/components/events/create-event-dialog";
import { QuickGuideButton } from "@/components/onboarding/quick-guide-button";
import { Skeleton } from "@/components/ui/skeleton";
```

And replace:
```tsx
        <CreateEventDialog />
```
with:
```tsx
        <div className="flex items-center gap-2">
          <QuickGuideButton />
          <CreateEventDialog />
        </div>
```

- [ ] **Step 6: Typecheck + lint + run full frontend tests**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: clean; all tests pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/onboarding/quick-guide-button.tsx frontend/components/events/events-view.tsx frontend/tests/components/quick-guide-button.test.tsx
git commit -m "feat(guide): one-time Quick guide pill beside New Event"
```

---

## Phase 4 — Capture fresh screenshots

**Files:**
- Create: `scripts/capture-guide.mjs`
- Create: `frontend/public/guide/*.png` (output)

> This produces the 8 PNGs the guide ships. It needs the stack running. Run from repo root.

- [ ] **Step 1: Create the capture script**

```js
// scripts/capture-guide.mjs
// Captures the 8 guide screenshots into frontend/public/guide/.
// Prereqs (run in separate terminals from repo root):
//   1) backend:  cd backend && DATABASE_URL="sqlite:///./guide.db" SECRET_KEY=guide \
//                python -m alembic upgrade head && \
//                DATABASE_URL="sqlite:///./guide.db" SECRET_KEY=guide PUBLIC_API_URL=http://localhost:8000 \
//                python -m uvicorn app.main:app --port 8000
//   2) frontend: cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=guide-secret \
//                AUTH_URL=http://localhost:3000 npm run dev   (serves on :3000)
//   3) capture:  node scripts/capture-guide.mjs
import { chromium } from "playwright";
import { generateSecretKey, getPublicKey, finalizeEvent } from "nostr-tools";
import { nsecEncode } from "nostr-tools/nip19";
import { mkdirSync } from "fs";

const BASE = process.env.GUIDE_BASE ?? "http://localhost:3000";
const API = process.env.GUIDE_API ?? "http://localhost:8000";
const OUT = "frontend/public/guide";

const SK = generateSecretKey();
const PK = getPublicKey(SK);
const NSEC = nsecEncode(SK);

const shot = async (page, name) => {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name}.png`);
};

async function token() {
  const event = finalizeEvent(
    { kind: 27235, created_at: Math.floor(Date.now() / 1000), tags: [["u", `${API}/auth/nostr`], ["method", "POST"]], content: "" },
    SK
  );
  const res = await fetch(`${API}/auth/nostr`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pubkey: PK, event }),
  });
  if (!res.ok) throw new Error(`/auth/nostr ${res.status}: ${await res.text()}`);
  return (await res.json()).access_token;
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  // 01 login
  await page.goto(`${BASE}/login`);
  await page.waitForLoadState("domcontentloaded");
  await shot(page, "01-login");

  await page.fill('input[id="nsec"]', NSEC);
  await page.click('button:has-text("Connect with nsec key")');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 15000 });
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('h1:has-text("Overview")', { timeout: 10000 });

  // 02 create-event dialog
  await page.click('button:has-text("New Event")');
  await page.waitForSelector('[role="dialog"]', { timeout: 3000 });
  await page.fill('input[id="title"]', "AI for Agriculture Hackathon");
  await page.fill('#description', "Build AI + satellite tools to improve crop yields.");
  await page.fill('input[id="team_count"]', "3");
  await shot(page, "02-create-event");
  await page.click('button:has-text("Create Event")');
  await page.waitForURL(/\/dashboard\/events\/[^/]+$/, { timeout: 15000 });
  const eventId = page.url().split("/events/")[1];

  // 03 event dashboard
  await page.waitForLoadState("domcontentloaded");
  await shot(page, "03-event-dashboard");

  // activate via API
  const t = await token();
  await fetch(`${API}/api/v1/events/${eventId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
    body: JSON.stringify({ status: "active" }),
  });
  const slug = (await (await fetch(`${API}/api/v1/events/${eventId}`, { headers: { Authorization: `Bearer ${t}` } })).json()).registration_slug;

  // register participants via API (NEW fields)
  const people = [
    { name: "Alice", email: "alice@t.com", primary_strength: "technical", experience_level: "advanced" },
    { name: "Bob", email: "bob@t.com", primary_strength: "design", experience_level: "intermediate" },
    { name: "Carol", email: "carol@t.com", primary_strength: "other", strength_other: "Agronomist", experience_level: "advanced" },
    { name: "Dave", email: "dave@t.com", primary_strength: "planning", experience_level: "beginner" },
    { name: "Eve", email: "eve@t.com", primary_strength: "research", experience_level: "advanced" },
    { name: "Frank", email: "frank@t.com", primary_strength: "coordination", experience_level: "intermediate" },
  ];
  for (const p of people) {
    await fetch(`${API}/api/v1/events/${slug}/register`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p),
    });
  }

  // 04 attendees + QR
  await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Registration QR Code", { timeout: 8000 });
  await shot(page, "04-attendees-qr");

  // 05 public join form (NEW form)
  const join = await ctx.newPage();
  await join.goto(`${BASE}/join/${slug}`, { waitUntil: "domcontentloaded" });
  await join.waitForSelector("text=Primary Strength", { timeout: 8000 });
  await shot(join, "05-join-form");
  await join.close();

  // 06 configure
  await page.goto(`${BASE}/dashboard/events/${eventId}/configure`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Balancing Weights", { timeout: 8000 });
  await shot(page, "06-configure");

  // 07 engine results
  await page.goto(`${BASE}/dashboard/events/${eventId}/engine`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("text=Allocation Engine", { timeout: 15000 });
  await page.click('button:has-text("Generate Teams")');
  await page.waitForSelector("text=Team 01", { timeout: 20000 });
  await shot(page, "07-engine-results");

  // 08 published
  await page.click('button:has-text("Publish Teams")');
  await page.waitForSelector('button:has-text("Export CSV")', { timeout: 8000 });
  await shot(page, "08-published");

  await browser.close();
  console.log("\n✅ Guide screenshots captured to frontend/public/guide/\n");
}

main().catch(e => { console.error("❌ capture failed:", e.message); process.exit(1); });
```

> Selectors mirror the live UI on this branch. If any `waitForSelector` text changed (e.g., button labels on the engine page), read the relevant page component and adjust the selector — do not guess.

- [ ] **Step 2: Run the stack and capture** — follow the prereq comments in the script header (start backend on :8000 with a fresh migrated `guide.db`, start frontend dev on :3000), then:

Run: `node scripts/capture-guide.mjs`
Expected: 8 lines `📸 NN-*.png` and `✅ Guide screenshots captured`. Confirm 8 files exist:
Run: `ls frontend/public/guide/`
Expected: `01-login.png 02-create-event.png 03-event-dashboard.png 04-attendees-qr.png 05-join-form.png 06-configure.png 07-engine-results.png 08-published.png`

- [ ] **Step 3: Verify each filename matches `GUIDE_STEPS[].image`** — the 8 files must exactly match the `image` paths in `frontend/lib/guide-steps.ts`. Fix any mismatch in `guide-steps.ts` (the data file is the source of truth for naming).

- [ ] **Step 4: Clean up the scratch DB**

Run: `rm -f backend/guide.db`

- [ ] **Step 5: Commit**

```bash
git add scripts/capture-guide.mjs frontend/public/guide/
git commit -m "feat(guide): capture script + fresh golden-path screenshots"
```

---

## Phase 5 — Full verification

- [ ] **Step 1: Frontend gates**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: tsc clean; lint no new errors; all vitest tests pass.

- [ ] **Step 2: Production build**

Run: `cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: build succeeds; route list includes `/dashboard/settings/guide`.

- [ ] **Step 3: Commit any fixes** (only if Steps 1–2 required changes)

```bash
git add -A && git commit -m "chore(guide): verification fixes"
```

---

## Self-Review (completed by author)

- **Spec coverage:** Guide content (P1), guide page + Settings entry (P2), one-time knob with localStorage + events-view placement (P3), fresh screenshots via capture script (P4), testing + build (every phase + P5). ✅
- **Type consistency:** `GuideStep`/`GUIDE_STEPS`, `image` paths `^/guide/NN-*.png` match the capture script's output filenames and the page's `next/image src`; `SEEN_KEY="squadsync.guideSeen"` used identically in component + tests; `data-testid="guide-dot"` consistent. ✅
- **Placeholders:** none — full code for every new file; the one judgment point (capture selectors drifting) has an explicit "read the component, don't guess" instruction. ✅
- **YAGNI:** localStorage (no backend), static screenshots (no tour), capture not in CI. ✅
