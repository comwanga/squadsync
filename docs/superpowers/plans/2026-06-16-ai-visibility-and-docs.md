# Surface AI Categorization + Docs/Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the AI categorization of free-text "Other" strengths visible (counts + badges + a guide step), fix stale post-PR#11 UI, rewrite the README, and remove redundant files.

**Architecture:** Backend reports per-event `ai_normalized`/`auto_normalized` counts on the allocation response; the frontend surfaces them as a results-page note and Attendees source badges, and the guide gains an explainer step with a fresh screenshot. Small contained bugfix for the stale `TeamMember` type. Docs + cleanup round it out.

**Tech Stack:** FastAPI + SQLAlchemy + pytest (backend); Next.js 16 + React + Vitest (frontend); Playwright (screenshot capture).

**Spec:** `docs/superpowers/specs/2026-06-16-ai-visibility-and-docs-design.md`
**Branch:** `feat/ai-visibility-and-docs` (off `main`).

---

## Phase 1 — Backend: normalization counts

**Files:**
- Modify: `backend/app/services/categorization_service.py`
- Modify: `backend/app/schemas/allocation.py`
- Modify: `backend/app/api/v1/allocation.py`
- Test: `backend/tests/test_categorization.py` (extend), `backend/tests/test_allocation_counts.py` (new)

- [ ] **Step 1: Update `normalize_pending` to return counts.** In `categorization_service.py`, change the function so it returns `{"ai": int, "fallback": int}`. Replace the final loop + `return`:

```python
def normalize_pending(db: Session, event_id: UUID) -> dict[str, int]:
    """Fill normalized_strength for un-normalized Other entries. Never raises.

    Returns counts of how many entries were set via AI vs deterministic fallback
    in this call.
    """
    counts = {"ai": 0, "fallback": 0}
    pending = _pending(db, event_id)
    if not pending:
        return counts
    event = db.query(Event).filter(Event.id == event_id).first()

    mapping: dict[str, str] = {}
    if settings.ANTHROPIC_API_KEY:
        try:
            mapping = _classify(event, pending)
        except Exception as exc:  # noqa: BLE001 — AI is best-effort
            logger.warning("Categorization AI failed, using fallback: %s", exc)
            mapping = {}

    for p in pending:
        ai_cat = mapping.get(str(p.id))
        if ai_cat:
            p.normalized_strength = ai_cat
            p.strength_source = "ai"
            counts["ai"] += 1
        else:
            p.normalized_strength = _slug(p.strength_other or "other")
            p.strength_source = "fallback"
            counts["fallback"] += 1
    db.commit()
    return counts
```

- [ ] **Step 2: Add count fields to `AllocationOut`.** In `backend/app/schemas/allocation.py`, add two fields to `AllocationOut` (after `constraint_warnings`):

```python
class AllocationOut(BaseModel):
    id: UUID
    event_id: UUID
    snapshot_hash: str
    status: str
    constraint_warnings: dict
    ai_normalized: int = 0
    auto_normalized: int = 0
    teams: list[TeamOut] = []

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Populate counts in `_build_allocation_out`.** In `backend/app/api/v1/allocation.py`, inside `_build_allocation_out`, before the final `return`, count the event's participant sources and include them in the validated dict:

```python
    ai_n = db.query(Participant).filter(
        Participant.event_id == allocation.event_id,
        Participant.strength_source == "ai",
    ).count()
    auto_n = db.query(Participant).filter(
        Participant.event_id == allocation.event_id,
        Participant.strength_source == "fallback",
    ).count()
    return AllocationOut.model_validate({
        "id": allocation.id,
        "event_id": allocation.event_id,
        "snapshot_hash": allocation.snapshot_hash,
        "status": allocation.status,
        "constraint_warnings": allocation.constraint_warnings or {},
        "ai_normalized": ai_n,
        "auto_normalized": auto_n,
        "teams": teams_out,
    })
```

(`Participant` is already imported in this module.)

- [ ] **Step 4: Extend the categorization test.** In `backend/tests/test_categorization.py`, update the two existing assertions to also check the return value. Add to `test_ai_maps_other_to_category` after the `normalize_pending` call:

```python
    with patch.object(cat, "_classify", return_value={str(p.id): "domain_expert"}):
        counts = cat.normalize_pending(db, e.id)
    assert counts == {"ai": 1, "fallback": 0}
```

And add to `test_fallback_when_no_key` after the call:

```python
    counts = cat.normalize_pending(db, e.id)
    assert counts == {"ai": 0, "fallback": 1}
```

(Replace the existing bare `cat.normalize_pending(db, e.id)` lines in those two tests with the count-capturing versions above.)

- [ ] **Step 5: New integration test for the response counts.** Create `backend/tests/test_allocation_counts.py` (uses the shared `client`/`auth_headers` fixtures from `conftest.py`; no Anthropic key in the test env → fallback path):

```python
def _make_active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Counts", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def test_allocation_reports_auto_normalized_count(client, auth_headers):
    e = _make_active_event(client, auth_headers)
    slug = e["registration_slug"]
    # one free-text "Other" + three presets so allocation has >= 2 per team
    client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Carol", "email": "carol@t.com",
        "primary_strength": "other", "strength_other": "Agronomist", "experience_level": "advanced"})
    for i, s in enumerate(["technical", "design", "planning"]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    res = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    # No ANTHROPIC_API_KEY in tests -> the Other entry is categorized via fallback.
    assert body["auto_normalized"] == 1
    assert body["ai_normalized"] == 0
```

- [ ] **Step 6: Run backend tests**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest tests/test_categorization.py tests/test_allocation_counts.py -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/categorization_service.py backend/app/schemas/allocation.py backend/app/api/v1/allocation.py backend/tests/test_categorization.py backend/tests/test_allocation_counts.py
git commit -m "feat(api): report ai_normalized / auto_normalized counts on allocation"
```

---

## Phase 2 — Frontend types + team-card bugfix

**Files:**
- Modify: `frontend/hooks/use-allocation.ts`
- Modify: `frontend/components/engine/team-card.tsx`

> Bug: after PR #11 the backend returns `normalized_strength`/`experience_level` per member, but the `TeamMember` type and `team-card` still read `role`/`skill_level` (now undefined). Fix while adding the count fields.

- [ ] **Step 1: Update `use-allocation.ts` types.** Replace the `TeamMember` interface and add count fields to `Allocation`:

```ts
export interface TeamMember {
  id: string;
  name: string;
  email: string;
  normalized_strength?: string;
  experience_level: string;
  composite_score?: number;
}
```
```ts
export interface Allocation {
  id: string;
  event_id: string;
  snapshot_hash: string;
  status: string;
  constraint_warnings: Record<string, string[]>;
  ai_normalized?: number;
  auto_normalized?: number;
  teams: Team[];
}
```

- [ ] **Step 2: Fix `team-card.tsx`** to use the new fields. Replace the `roleColor` map, the `roleCounts` reducer, the chips block, and the member line:

```tsx
const strengthColor: Record<string, string> = {
  technical: "bg-blue-100 text-blue-800",
  design: "bg-pink-100 text-pink-800",
  planning: "bg-indigo-100 text-indigo-800",
  coordination: "bg-green-100 text-green-800",
  communication: "bg-orange-100 text-orange-800",
  research: "bg-purple-100 text-purple-800",
  domain_expert: "bg-teal-100 text-teal-800",
};
```

Reducer:
```tsx
  const strengthCounts = team.members.reduce<Record<string, number>>((acc, m) => {
    const key = m.normalized_strength ?? "other";
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
```

Chips block:
```tsx
        <div className="flex flex-wrap gap-1">
          {Object.entries(strengthCounts).map(([strength, count]) => (
            <span
              key={strength}
              className={`px-1.5 py-0.5 rounded text-xs font-medium capitalize ${strengthColor[strength] ?? "bg-slate-100 text-slate-800"}`}
            >
              {strength.replace("_", " ")} ×{count}
            </span>
          ))}
        </div>
```

Member line (inside the `details` list):
```tsx
                <span className="text-muted-foreground capitalize">
                  {(m.normalized_strength ?? "—").replace("_", " ")} · {m.experience_level}
                </span>
```

- [ ] **Step 3: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: tsc clean; 0 lint errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/hooks/use-allocation.ts frontend/components/engine/team-card.tsx
git commit -m "fix(ui): team cards use normalized_strength/experience_level; add count types"
```

---

## Phase 3 — Attendees source badge

**Files:**
- Create: `frontend/components/attendees/source-badge.tsx`
- Test: `frontend/tests/components/source-badge.test.tsx`
- Modify: `frontend/components/attendees/attendees-table.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// frontend/tests/components/source-badge.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { SourceBadge } from "@/components/attendees/source-badge";

describe("SourceBadge", () => {
  it("labels each source", () => {
    const cases: [string, string][] = [
      ["ai", "AI"], ["fallback", "Auto"], ["manual", "Manual"], ["preset", "preset"],
    ];
    for (const [source, label] of cases) {
      const { unmount } = render(<SourceBadge source={source} />);
      expect(screen.getByText(label)).toBeInTheDocument();
      unmount();
    }
  });
});
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd frontend && npx vitest run tests/components/source-badge.test.tsx`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the badge**

```tsx
// frontend/components/attendees/source-badge.tsx
const STYLES: Record<string, { label: string; cls: string }> = {
  ai: { label: "AI", cls: "bg-violet-100 text-violet-800" },
  fallback: { label: "Auto", cls: "bg-slate-100 text-slate-700" },
  manual: { label: "Manual", cls: "bg-blue-100 text-blue-800" },
};

export function SourceBadge({ source }: { source: string }) {
  const s = STYLES[source];
  if (!s) return <span className="text-xs text-muted-foreground">{source}</span>;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>;
}
```

- [ ] **Step 4: Run it, expect PASS**

Run: `cd frontend && npx vitest run tests/components/source-badge.test.tsx`
Expected: PASS.

- [ ] **Step 5: Use it in the attendees table.** In `frontend/components/attendees/attendees-table.tsx`, add the import:

```tsx
import { SourceBadge } from "@/components/attendees/source-badge";
```

and replace the Source cell (currently `<td ...>{p.strength_source}</td>`) with:

```tsx
                    <td className="px-4 py-3 whitespace-nowrap"><SourceBadge source={p.strength_source} /></td>
```

- [ ] **Step 6: Typecheck + lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/attendees/source-badge.tsx frontend/tests/components/source-badge.test.tsx frontend/components/attendees/attendees-table.tsx
git commit -m "feat(ui): AI/Auto/Manual source badges in attendees table"
```

---

## Phase 4 — Engine surfacing (results note + run-panel copy)

**Files:**
- Create: `frontend/lib/allocation-notes.ts`
- Test: `frontend/tests/lib/allocation-notes.test.ts`
- Modify: `frontend/components/engine/results-grid.tsx`
- Modify: `frontend/components/engine/run-panel.tsx`

- [ ] **Step 1: Write the failing test**

```ts
// frontend/tests/lib/allocation-notes.test.ts
import { describe, it, expect } from "vitest";
import { normalizationNote } from "@/lib/allocation-notes";

describe("normalizationNote", () => {
  it("reports AI count when present", () => {
    expect(normalizationNote(2, 0)).toMatch(/AI categorized 2/i);
  });
  it("reports fallback when no AI", () => {
    expect(normalizationNote(0, 3)).toMatch(/categorized automatically/i);
  });
  it("returns null when nothing was normalized", () => {
    expect(normalizationNote(0, 0)).toBeNull();
  });
});
```

- [ ] **Step 2: Run it, expect FAIL**

Run: `cd frontend && npx vitest run tests/lib/allocation-notes.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement the helper**

```ts
// frontend/lib/allocation-notes.ts
// Human-readable note about how free-text "Other" strengths were categorized.
export function normalizationNote(aiNormalized = 0, autoNormalized = 0): string | null {
  if (aiNormalized > 0) {
    const s = aiNormalized === 1 ? "" : "s";
    return `🧠 AI categorized ${aiNormalized} free-text “Other” response${s}.`;
  }
  if (autoNormalized > 0) {
    const s = autoNormalized === 1 ? "" : "s";
    return `${autoNormalized} “Other” response${s} categorized automatically — set ANTHROPIC_API_KEY for AI.`;
  }
  return null;
}
```

- [ ] **Step 4: Run it, expect PASS**

Run: `cd frontend && npx vitest run tests/lib/allocation-notes.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Render the note in `results-grid.tsx`.** Add the import:

```tsx
import { normalizationNote } from "@/lib/allocation-notes";
```

Just inside the returned top-level `<div className="space-y-4">` (before the warnings block), add:

```tsx
      {normalizationNote(allocation.ai_normalized, allocation.auto_normalized) && (
        <div className="text-sm text-muted-foreground bg-violet-50 border border-violet-100 rounded-lg px-4 py-2">
          {normalizationNote(allocation.ai_normalized, allocation.auto_normalized)}
        </div>
      )}
```

- [ ] **Step 6: Fix stale copy + add AI line in `run-panel.tsx`.** Replace the `PASSES` array:

```tsx
const PASSES = [
  "Pass 1 — Distributing anchors (Advanced)",
  "Pass 2 — Core balance pipeline (Intermediate)",
  "Pass 3 — Strength constraint enforcement",
  "Pass 4 — Beginner fill",
];
```

And replace the participant-count `<p>` with two lines:

```tsx
        <p className="text-sm text-muted-foreground">
          {participantCount} participants ready for allocation.
          The engine will run 4 passes to distribute teams fairly.
        </p>
        <p className="text-xs text-muted-foreground">
          Free-text “Other” strengths are categorized by AI before allocation.
        </p>
```

- [ ] **Step 7: Typecheck + lint + tests**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test`
Expected: clean; all tests pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/lib/allocation-notes.ts frontend/tests/lib/allocation-notes.test.ts frontend/components/engine/results-grid.tsx frontend/components/engine/run-panel.tsx
git commit -m "feat(ui): results-page normalization note + engine copy fixes"
```

---

## Phase 5 — Guide step + screenshot

**Files:**
- Modify: `frontend/lib/guide-steps.ts`
- Modify: `frontend/tests/lib/guide-steps.test.ts`
- Modify: `scripts/capture-guide.mjs`
- Create: `frontend/public/guide/09-ai-category.png`

- [ ] **Step 1: Append the guide step.** In `frontend/lib/guide-steps.ts`, add as the LAST element of `GUIDE_STEPS`:

```ts
  {
    id: "ai-categorize",
    title: "9. Behind the scenes: SquadSync sorts free-text answers",
    caption: "When someone picks “Other” and types their own strength, SquadSync categorizes it automatically before forming teams — by AI when an API key is set, deterministically otherwise. The Attendees table shows each person’s category and its source (AI / Auto / Manual), and you can override any of them.",
    image: "/guide/09-ai-category.png",
  },
```

- [ ] **Step 2: Update the count assertion.** In `frontend/tests/lib/guide-steps.test.ts`, change `expect(GUIDE_STEPS.length).toBe(8);` to `expect(GUIDE_STEPS.length).toBe(9);`.

- [ ] **Step 3: Run guide-steps test**

Run: `cd frontend && npx vitest run tests/lib/guide-steps.test.ts`
Expected: PASS (the image file need not exist yet for this test).

- [ ] **Step 4: Extend the capture script.** In `scripts/capture-guide.mjs`, after the `08-published` shot and before `await browser.close();`, add:

```js
  // 09 attendees after allocation — shows categorized "Other" + Source badge
  await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Registration QR Code", { timeout: 45000 });
  await shot(page, "09-ai-category");
```

- [ ] **Step 5: Capture the screenshot.** (Controller runs this — needs the live stack.) Start the migrated backend on :8000 and `npm run dev` on :3000, then:

Run: `node scripts/capture-guide.mjs`
Expected: all `📸` lines including `09-ai-category.png`; confirm `frontend/public/guide/09-ai-category.png` exists. (Locally it shows the "Auto" badge since no key is set — that's expected.)

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/guide-steps.ts frontend/tests/lib/guide-steps.test.ts scripts/capture-guide.mjs frontend/public/guide/09-ai-category.png
git commit -m "feat(guide): add AI-categorization step + screenshot"
```

---

## Phase 6 — README rewrite

**Files:**
- Modify: `README.md` (root)

- [ ] **Step 1: Rewrite `README.md`** to cover, in this order: one-line description; key features (universal Primary Strengths + free-text Other, AI-assisted **deterministic** team formation, registration QR, in-app guide, CSV/PDF export, Nostr login); architecture (Next.js frontend on Vercel, FastAPI + Postgres backend on Render, single `main` branch deploys both); local development (backend: venv, `pip install -r backend/requirements.txt`, `alembic upgrade head`, `uvicorn app.main:app`; frontend: `npm install`, `npm run dev`); environment variables (link to `DEPLOYMENT.md`, note `ANTHROPIC_API_KEY` optional → enables AI categorization, deterministic fallback otherwise); testing (`pytest`, `npm test`); and a pointer to `docs/superpowers/` for specs/plans. Keep it concise (under ~120 lines) and accurate to the current code.

- [ ] **Step 2: Sanity check links/commands** — verify referenced paths exist (`backend/requirements.txt`, `DEPLOYMENT.md`, `frontend/`), and that commands match what the project actually uses (cross-check against `DEPLOYMENT.md`).

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for current product + deploy model"
```

---

## Phase 7 — Cleanup redundant files

**Files:**
- Delete: `screenshots/` (root, 14 PNGs)
- Delete: `golden-path.mjs` (root)

- [ ] **Step 1: Confirm nothing references them**

Run: `cd "C:/Users/mwang/squadsync" && grep -rn "golden-path\|/screenshots/\|\"screenshots\b" --include=*.ts --include=*.tsx --include=*.mjs --include=*.json --include=*.yml --include=*.md . | grep -v node_modules | grep -v "docs/superpowers"`
Expected: no functional references (matches only inside the deleted files themselves or historical docs are acceptable — if a workflow/package script references `golden-path.mjs`, stop and report).

- [ ] **Step 2: Delete and commit**

```bash
git rm -r screenshots golden-path.mjs
git commit -m "chore: remove redundant root screenshots/ and golden-path.mjs (superseded by scripts/capture-guide.mjs + frontend/public/guide)"
```

---

## Phase 8 — Full verification

- [ ] **Step 1: Backend suite**

Run: `cd backend && rm -f *.db; DATABASE_URL="sqlite:///./test_squadsync.db" SECRET_KEY=test python -m pytest -q; rm -f *.db`
Expected: all pass.

- [ ] **Step 2: Frontend gates + build**

Run: `cd frontend && npx tsc --noEmit && npm run lint && npm test && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=build-check npm run build`
Expected: tsc clean; lint no new errors; all tests pass; build succeeds.

- [ ] **Step 3: Commit any fixes** (only if needed)

```bash
git add -A && git commit -m "chore(ai-visibility): verification fixes"
```

---

## Self-Review (completed by author)

- **Spec coverage:** counts API (P1), use-allocation types (P2), results note (P4), attendees badges (P3), engine copy fix (P4), guide step + screenshot (P5), README (P6), cleanup (P7), testing (each phase + P8). Plus the discovered `TeamMember` bugfix (P2). ✅
- **Type consistency:** `ai_normalized`/`auto_normalized` used identically across `AllocationOut`, `_build_allocation_out`, `Allocation` type, `normalizationNote`, and `results-grid`; `normalize_pending` returns `{"ai","fallback"}` matching the test; `SourceBadge` labels (AI/Auto/Manual/preset) match `strength_source` values (`ai`/`fallback`/`manual`/`preset`). ✅
- **Placeholders:** none — complete code per step; the one runtime step (P5 capture) is controller-run with exact commands. ✅
- **YAGNI:** counts derived from existing data; pure-function/presentational units chosen specifically for reliable tests (no SWR/session wrestling). ✅
