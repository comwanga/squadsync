# SquadSync — Universal Group Allocation Engine
## Design Specification
**Date:** 2026-06-11
**Status:** Approved
**Phase:** Phase 1 (MVP)

---

## 1. Product Overview

SquadSync is a web-based Universal Group Allocation Engine that intelligently distributes people into balanced teams based on skills, experience, roles, and configurable criteria. It serves hackathons, bootcamps, universities, workshops, corporate training, NGOs, and community events.

**Core user flow:**
> Create Event → Configure Rules → Generate QR → Collect Registrations → Run Allocation → View Teams → Export & Share

**Three-layer product model:**
1. **Participant Experience** — mobile-optimized public registration via QR code
2. **Organizer Workspace** — event setup, participant management, allocation controls
3. **Allocation Intelligence Layer** — fairness scoring, constraint enforcement, explainability (Phase 2)

---

## 2. Scope

### Phase 1 (this spec)
- Organizer auth (email/password + Google OAuth)
- Event CRUD + co-organizer invites
- QR-based public participant registration
- Allocation engine (4-pass deterministic algorithm)
- Team results view with fairness scores
- Export: CSV, PDF, public share link

### Phase 2 (future — no schema changes required)
- Allocation simulation (dry-run before commit)
- Fairness explainability panel ("Why these teams were formed")
- Drag-and-drop team override studio
- Live registration tracker (SSE or polling)
- WhatsApp / Telegram / Discord share integrations

---

## 3. Architecture

### Approach
Clean monorepo, REST API. Frontend and backend are independently deployed services communicating over HTTP.

### Repository Structure

```
squadsync/
├── frontend/                        # Next.js 14 App Router → Vercel
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx           # sidebar + topbar shell
│   │   │   ├── page.tsx             # overview / multi-event hub
│   │   │   └── events/
│   │   │       └── [eventId]/
│   │   │           ├── page.tsx     # event dashboard
│   │   │           ├── attendees/   # participant list + QR display
│   │   │           ├── configure/   # allocation rules setup
│   │   │           └── engine/      # run allocation + results
│   │   └── join/
│   │       └── [eventId]/page.tsx   # public mobile registration form
│   ├── components/
│   ├── lib/                         # API client, auth helpers
│   └── hooks/
│
├── backend/                         # FastAPI → Render (Docker)
│   ├── app/
│   │   ├── api/                     # route handlers
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   ├── services/                # business logic + allocation engine
│   │   └── core/                    # config, auth, database session
│   └── alembic/                     # DB migrations
│
└── docker-compose.yml               # local dev: postgres + backend + frontend
```

### Deployment

| Service    | Platform                         |
|------------|----------------------------------|
| Frontend   | Vercel                           |
| Backend    | Render (Dockerized FastAPI)      |
| Database   | Supabase PostgreSQL or Render PG |

### Request Flow

```
Browser / Mobile
      │
      ▼
Next.js (Vercel)
  ├── (auth) pages   →  NextAuth.js  →  FastAPI /auth/...
  ├── (dashboard)    →  fetchAPI()   →  FastAPI /api/v1/...
  └── join/[eventId] →  fetchAPI()   →  FastAPI /api/v1/events/{slug}/register
                                                │
                                           PostgreSQL
```

- NextAuth.js issues a session JWT on login
- JWT forwarded as `Authorization: Bearer <token>` on every FastAPI call
- FastAPI validates JWT via `get_current_user` dependency on protected routes
- Public registration route requires only a valid event slug — no auth

---

## 4. Data Model

```sql
users
  id               UUID PRIMARY KEY
  name             TEXT NOT NULL
  email            TEXT UNIQUE NOT NULL
  hashed_password  TEXT                    -- null for OAuth users
  provider         ENUM(local, google)
  provider_id      TEXT                    -- Google sub claim
  created_at       TIMESTAMPTZ

events
  id                  UUID PRIMARY KEY
  owner_id            UUID REFERENCES users
  title               TEXT NOT NULL
  description         TEXT
  participant_limit   INTEGER
  team_count          INTEGER NOT NULL
  status              ENUM(draft, active, allocated, archived)
  registration_slug   TEXT UNIQUE NOT NULL  -- used in QR URL
  created_at          TIMESTAMPTZ

event_co_organizers
  event_id    UUID REFERENCES events
  user_id     UUID REFERENCES users
  invited_at  TIMESTAMPTZ
  PRIMARY KEY (event_id, user_id)

participants
  id                UUID PRIMARY KEY
  event_id          UUID REFERENCES events
  name              TEXT NOT NULL
  email             TEXT NOT NULL
  phone             TEXT
  skill_level       ENUM(beginner, intermediate, advanced, professional)
  role              ENUM(frontend, backend, fullstack, ai_ml, ux, devops,
                         blockchain, mobile, product, marketing)
  years_experience  INTEGER NOT NULL
  tech_stack        TEXT[]
  interests         TEXT[]
  composite_score   FLOAT                   -- computed on registration, stored
  registered_at     TIMESTAMPTZ

allocation_configs
  id                  UUID PRIMARY KEY
  event_id            UUID REFERENCES events UNIQUE
  weight_experience   FLOAT DEFAULT 0.5     -- W_exp + W_skill = 1.0
  weight_skill        FLOAT DEFAULT 0.5
  role_constraints    JSONB DEFAULT '{}'    -- e.g. {"frontend": 1, "backend": 1}
  updated_at          TIMESTAMPTZ

allocations
  id                   UUID PRIMARY KEY
  event_id             UUID REFERENCES events
  snapshot_hash        TEXT NOT NULL        -- SHA-256 of input participant set
  status               ENUM(draft, published)
  constraint_warnings  JSONB DEFAULT '{}'   -- e.g. {"team_03": ["missing: frontend"]}
  created_at           TIMESTAMPTZ

teams
  id                  UUID PRIMARY KEY
  allocation_id       UUID REFERENCES allocations
  name                TEXT NOT NULL
  fairness_score      FLOAT
  skill_score         FLOAT
  role_balance_score  FLOAT

team_members
  team_id         UUID REFERENCES teams
  participant_id  UUID REFERENCES participants
  PRIMARY KEY (team_id, participant_id)
```

### Key Design Decisions

- `composite_score` is computed at registration time and stored. Recomputed only when `allocation_config` weights change.
- `snapshot_hash` is SHA-256 of the sorted participant ID set — guarantees reproducibility and detects stale allocations.
- `constraint_warnings` is JSONB — shape: `{"team_03": ["missing: frontend"]}`. Evolves without schema migrations.
- `role_constraints` is JSONB — organizer sets minimum counts per role. Empty object means no constraints.
- Participants belong to an event, not a user account — no login required to register.
- Phase 2 features require no additional schema changes.

---

## 5. API Design

### Auth

```
POST /auth/register          # email + password signup
POST /auth/login             # returns JWT
POST /auth/google            # OAuth token exchange → JWT
POST /auth/refresh           # refresh JWT
```

### Events (organizer-protected)

```
GET    /api/v1/events
POST   /api/v1/events
GET    /api/v1/events/{id}
PATCH  /api/v1/events/{id}
DELETE /api/v1/events/{id}                     # soft delete → status: archived

POST   /api/v1/events/{id}/co-organizers       # invite by email
DELETE /api/v1/events/{id}/co-organizers/{uid}
```

### Registration (public)

```
GET  /api/v1/events/{slug}/info        # title, status, limit — no auth required
POST /api/v1/events/{slug}/register    # participant submission — no auth required
```

### Participants (organizer-protected)

```
GET    /api/v1/events/{id}/participants         # paginated; filter by role/skill
DELETE /api/v1/events/{id}/participants/{pid}
```

### Allocation (organizer-protected)

```
GET  /api/v1/events/{id}/config
PUT  /api/v1/events/{id}/config
POST /api/v1/events/{id}/allocate
GET  /api/v1/events/{id}/allocations/{aid}
POST /api/v1/events/{id}/allocations/{aid}/publish
```

### Teams (organizer-protected)

```
GET  /api/v1/allocations/{aid}/teams
GET  /api/v1/allocations/{aid}/teams/{tid}
```

### Export (organizer-protected)

```
GET  /api/v1/allocations/{aid}/export/csv
GET  /api/v1/allocations/{aid}/export/pdf
GET  /api/v1/allocations/{aid}/export/link
```

---

## 6. Allocation Engine

### Composite Score (computed at registration)

```
Sc = (W_exp × E) + (W_skill × K)

E = years_experience → scalar [1–4]
    0–1y → 1 | 2–3y → 2 | 4–6y → 3 | 7+y → 4

K = skill_level → scalar [1–4]
    beginner → 1 | intermediate → 2 | advanced → 3 | professional → 4

W_exp + W_skill = 1.0  (organizer-configured, default 0.5 / 0.5)
```

### Four-Pass Algorithm

**Pass 1 — Anchor Allocation**
Filter `Sc >= 3.0`. Distribute round-robin across T1..Tn. If no anchors exist, skip to Pass 2.

**Pass 2 — Core Balance Pipeline**
Pool: `1.5 <= Sc < 3.0`, sorted descending. Assign each to the team with lowest current `ΣSc`.

**Pass 3 — Role Constraint Enforcement**
For each team, check `role_constraints`. If violated, attempt look-ahead swap with next unassigned participant matching the missing role. If no candidate: log to `constraint_warnings`, continue.

**Pass 4 — Beginner Fill**
Pool: `Sc < 1.5`. Assign to teams with fewest current members to minimise size variance.

### Post-Allocation Scoring

```
skill_score        = 100 × (1 − std_dev(ΣSc per team) / mean(ΣSc per team))
role_balance_score = 100 × (fulfilled_constraints / total_constraints)
                     100 if no constraints defined
fairness_score     = (skill_score × 0.6) + (role_balance_score × 0.4)
```

All three scores stored per team. All pass decisions logged on the allocation record for Phase 2 explainability.

### Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| No anchors (all beginners) | Pass 1 skipped |
| Role constraint unsatisfiable | Best-effort + warning logged per team |
| Odd participant count | Final team(s) get one fewer member; flagged in warnings |
| Single participant | Assigned to Team 1; no balancing |
| Zero participants | Engine error: `"No participants to allocate"` |
| Team count > participant count | Engine error: `"Fewer participants than teams"` |

---

## 7. Frontend

### Auth Flow

```
Email/Password:
  /register → POST /auth/register → auto-login → /dashboard
  /login    → POST /auth/login    → JWT in NextAuth session → /dashboard

Google OAuth:
  /login → NextAuth signIn("google") → Google consent → POST /auth/google → /dashboard

Route protection:
  (dashboard)/layout.tsx → getServerSession() → redirect /login if null
  All FastAPI calls → Authorization: Bearer <jwt> via fetchAPI() wrapper
```

### App Shell

```
(dashboard)/layout.tsx
├── <Sidebar>    nav links, collapse toggle, active event indicator
│                desktop: collapsible | mobile: bottom nav bar
├── <Topbar>     search, notifications, profile dropdown
└── <main>       {children}
```

### Screen Inventory

| Route | Screen | Key Interactions |
|-------|--------|-----------------|
| `/login` | Login | Email/pass form, Google OAuth button |
| `/register` | Register | Email/pass form, Google OAuth button |
| `/dashboard` | Overview hub | Event cards, stat totals, create event CTA |
| `/dashboard/events/[id]` | Event dashboard | Stat cards, quick-action buttons |
| `/dashboard/events/[id]/attendees` | Attendees | Paginated table, search/filter, QR display + PNG download |
| `/dashboard/events/[id]/configure` | Configure | Weight sliders (locked to sum 1.0), role constraint builder |
| `/dashboard/events/[id]/engine` | Engine | Run button, pass progress, results grid, publish + export |
| `/join/[eventId]` | Registration | Mobile-first form, in-place confirmation card |

### Registration Form Fields

```
name              text, required
email             email, required
phone             tel, optional
skill_level       radio: beginner / intermediate / advanced / professional
role              select: frontend / backend / fullstack / ai_ml / ux /
                          devops / blockchain / mobile / product / marketing
years_experience  number, min 0
tech_stack        tag input, optional
interests         tag input, optional
```

On successful submission: show confirmation card in-place (no redirect) to prevent duplicate submissions.

### Engine Page Flow

```
Pre-run:
  participant readiness summary → active config display → [Run Allocation]

Running:
  step indicator: Pass 1 → Pass 2 → Pass 3 → Pass 4

Results:
  constraint warnings banner (if any)
  team grid: name, member count, fairness score, role badges
  expandable per-team panel: member list, role breakdown, all scores
  [Publish Teams] → locks allocation
  export: [CSV] [PDF] [Copy Share Link]
```

---

## 8. Error Handling

| Layer | Strategy |
|-------|----------|
| FastAPI | RFC 7807 `application/problem+json` — `{type, title, status, detail}` |
| NextAuth | Auth errors redirect to `/login?error=<code>` |
| Frontend API client | Central `fetchAPI()` wrapper — typed errors → shadcn `<Sonner>` toasts |
| Registration form | Pydantic errors mapped to field-level inline messages |
| Allocation engine | Never throws — returns result with `constraint_warnings`; UI shows warning banner |

---

## 9. Technology Stack

| Technology   | Version     |
|--------------|-------------|
| Next.js      | 14 (App Router) |
| React        | 18          |
| Tailwind CSS | 3           |
| shadcn/ui    | latest      |
| NextAuth.js  | v5          |
| FastAPI      | 0.111+      |
| Python       | 3.12        |
| SQLAlchemy   | 2.0         |
| Pydantic     | v2          |
| Alembic      | latest      |
| PostgreSQL   | 16          |

---

## 10. Out of Scope (Phase 1)

- Allocation simulation / dry-run
- Fairness explainability panel
- Drag-and-drop team override studio
- Live registration tracker (SSE / WebSocket)
- WhatsApp / Telegram / Discord share
- AI-powered matching
- Decentralized features (Lightning, Nostr, reputation)
- Mobile native apps
- Third-party integrations (Eventbrite, Slack, GitHub)
- Platform super-admin role
