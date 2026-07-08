# SquadSync

Balanced team formation for hackathons, workshops, study groups, and community events.

The default journey is intentionally simple: an organizer creates an event, shares a QR code or link, participants join from their phones without accounts, and SquadSync generates deterministic fair teams with public results.

AI and Lightning payouts are optional add-ons. The app works without an Anthropic API key and without any wallet setup.

## What it does

- **Organizer access** — organizers can sign in to create and manage events.
- **Events + registration** — create an event, share a QR/link, attendees register with no login. Each attendee may add an optional Lightning address.
- **Taxonomy** — each attendee picks a Primary Strength (Technical, Design, Planning, Coordination, Communication, Research, Domain Expert, or Other free-text) and Experience level (Beginner/Intermediate/Advanced).
- **Allocation** — one click distributes role diversity and experience evenly across teams. The engine is fully deterministic; Claude (Haiku) only normalizes free-text "Other" strengths when `ANTHROPIC_API_KEY` is set (deterministic fallback otherwise).
- **Results** — public `/results/<id>` link, "find my team" lookup, CSV/PDF export.
- **Advanced Rewards** — optional prize payouts can split a sats pot across a winning team. Wallet credentials are used per request and are not stored.
- **Feedback** — Settings feedback box; stored in the DB and optionally forwarded to the owner when configured.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind v4, NextAuth v5 |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL (prod), SQLite (tests) |
| Auth / messaging | Nostr-based organizer sign-in and optional feedback forwarding |
| Bitcoin / Lightning | Optional prize payouts |
| AI | Anthropic Claude Haiku (optional, strength normalization only) |

**Deploy:** single `main` branch → backend + Postgres on Render (`render.yaml`), frontend on Vercel (`frontend/`). Full guide in `DEPLOYMENT.md`.

## Local development

### Option A: Docker Compose

Runs the full app locally: Postgres, FastAPI, and Next.js.

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:3000
- Backend health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

### Option B: Run services manually

```bash
# Backend (http://localhost:8000)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # set DATABASE_URL + SECRET_KEY
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8000

# Frontend (http://localhost:3000)
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL + AUTH_SECRET
npm run dev
```

For local development, no Anthropic key or Lightning configuration is required.

## Testing

```bash
# Root helpers
npm test                             # backend pytest + frontend Vitest
npm run lint                         # frontend ESLint
npm run build                        # frontend production build
npm run e2e                          # Playwright route smoke tests

# Direct commands
cd backend && python3 -m pytest         # backend (SQLite, no Postgres needed)
cd frontend && npm test                 # unit (Vitest)
cd frontend && npm run test:e2e         # e2e (Playwright)
```

## Docs

Environment reference and deploy steps: `DEPLOYMENT.md`. Design specs and plans: `docs/superpowers/`.

Project maintenance docs:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `docs/RELEASE_CHECKLIST.md`

## License

MIT — see [LICENSE](LICENSE)
