# SquadSync

Balanced team formation for hackathons, workshops, sports days, and study groups.
Organizers create an event and share a registration link or QR code; attendees
self-register; a deterministic engine builds balanced teams — no spreadsheets required.
Authentication is Nostr (NIP-98). No passwords, no email sign-up.

---

## Features

- **Nostr auth** — sign in with a browser extension (NIP-07), a generated keypair, or an existing `nsec`. No account required.
- **Event management** — create events, set them active for registration, manage and monitor participants from a dashboard.
- **Registration QR code** — share a QR or link; attendees fill out a public form with no login needed.
- **Participant taxonomy** — attendees choose a Primary Strength (Technical, Design, Planning, Coordination, Communication, Research, Domain Expert, or Other + free text) and an Experience level (Beginner / Intermediate / Advanced).
- **AI-assisted categorization** — "Other" free-text entries are normalized to a standard strength by Claude (Haiku) at allocation time when `ANTHROPIC_API_KEY` is set. Without the key a deterministic slug fallback is used. The team-allocation engine itself is fully deterministic — Claude never builds teams.
- **Balanced team allocation** — the engine distributes role diversity and experience scores evenly across teams.
- **CSV / PDF export** — download team rosters in either format.
- **Public results link** — share a `/results/<id>` URL so attendees can view their team without logging in.
- **Dark mode** — default theme; toggle in Settings. In-app Guide available at Settings → Guide.

---

## How it works

1. **Organizer creates an event** — sets a name, description, and target team size, then activates registration.
2. **Attendees self-register** — by scanning the event QR code or visiting the share link. No Nostr identity needed to register.
3. **Each attendee picks a strength and experience level** — from the universal taxonomy above, plus an optional "Other" free-text field.
4. **Organizer runs the allocation engine** — one button distributes participants into balanced teams, normalizing any "Other" entries via AI (or the deterministic fallback) first.
5. **Results are published** — a public share link (`/results/<id>`) is generated; teams can also be exported as CSV or PDF.

---

## Tech stack and architecture

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind CSS v4, NextAuth v5 |
| Backend | FastAPI 0.111, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL (production / Render); SQLite (tests only) |
| Auth | Nostr NIP-98 HTTP Auth, BIP340 Schnorr signatures (`coincurve`) |
| AI | Anthropic Claude Haiku (optional — strength normalization only) |
| Export | ReportLab (PDF), CSV via FastAPI |

**Deployment:** a single `main` branch drives both services. The backend (Docker) and a managed Postgres database are provisioned on Render via `render.yaml`. The Next.js frontend is deployed on Vercel with root directory set to `frontend/`. See `DEPLOYMENT.md` for the full step-by-step guide.

---

## Local development

### Backend

Run all commands from the `backend/` directory.

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — minimum required values:
#   DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/squadsync
#   SECRET_KEY=<any long random string>

# 4. Run database migrations
python -m alembic upgrade head

# 5. Start the server
python -m uvicorn app.main:app --port 8000
```

The API is available at `http://localhost:8000`. Confirm with `http://localhost:8000/health` → `{"status":"ok"}`.

### Frontend

Run all commands from the `frontend/` directory.

```bash
cd frontend

npm install

cp .env.local.example .env.local
# Edit .env.local — minimum required values:
#   NEXT_PUBLIC_API_URL=http://localhost:8000
#   AUTH_SECRET=<any long random string>

npm run dev
```

The app is available at `http://localhost:3000`.

---

## Environment variables

See `DEPLOYMENT.md` for the full environment reference for both Render and Vercel.

Key variables at a glance:

| Variable | Where | Notes |
|---|---|---|
| `DATABASE_URL` | backend | Postgres connection string. Auto-wired on Render; set in `.env` locally. |
| `SECRET_KEY` | backend | JWT signing key. Auto-generated on Render. |
| `FRONTEND_URL` | backend | CORS allowed origin (your Vercel URL). No trailing slash. |
| `PUBLIC_API_URL` | backend | This API's own public URL. Must match `NEXT_PUBLIC_API_URL` exactly (NIP-98 binding). |
| `ANTHROPIC_API_KEY` | backend | **Optional.** Enables AI normalization of free-text "Other" strengths. Omit to use the deterministic fallback. |
| `NEXT_PUBLIC_API_URL` | frontend | API URL. Must equal `PUBLIC_API_URL`. Build-time inlined — redeploy after changing. |
| `AUTH_SECRET` | frontend | NextAuth session secret. |
| `AUTH_URL` | frontend | The frontend's own URL (production only). |

---

## Testing

```bash
# Backend — runs against an in-memory SQLite database, no Postgres needed
cd backend
python -m pytest

# Frontend — unit tests (Vitest)
cd frontend
npm test

# Frontend — end-to-end tests (Playwright)
cd frontend
npm run test:e2e
```

---

## Project docs

Specs and implementation plans live under `docs/superpowers/`:

- `docs/superpowers/specs/` — design specs for each feature
- `docs/superpowers/plans/` — implementation plans
- `docs/audits/` — launch-readiness audits

---

## License

MIT — see [LICENSE](LICENSE)
