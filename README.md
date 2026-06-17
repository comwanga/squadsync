# SquadSync

Balanced team formation for hackathons, workshops, and study groups. Organizers create an event and share a QR/link; attendees self-register; a **deterministic engine** builds balanced teams. **AI reads each attendee's free-text "Other" strength and maps it to a standard category** so everyone is comparable before allocation — while the team-building itself stays fully deterministic and reproducible. Auth is **Nostr (NIP-98)** — no passwords, no email.

## What it does

- **Nostr login** — NIP-07 extension, generated keypair, or existing `nsec`.
- **Events + registration** — create an event, share a QR/link, attendees register with no login.
- **Taxonomy** — each attendee picks a Primary Strength (Technical, Design, Planning, Coordination, Communication, Research, Domain Expert, or Other free-text) and Experience level (Beginner/Intermediate/Advanced).
- **Allocation** — one click distributes role diversity and experience evenly across teams. The engine is fully deterministic; Claude (Haiku) only normalizes free-text "Other" strengths when `ANTHROPIC_API_KEY` is set (deterministic fallback otherwise).
- **Results** — public `/results/<id>` link, "find my team" lookup, CSV/PDF export.
- **Feedback** — Settings feedback box; stored in the DB and optionally DM'd to the owner over Nostr (NIP-04) when a bot key is configured.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind v4, NextAuth v5 |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Database | PostgreSQL (prod), SQLite (tests) |
| Auth / Nostr | NIP-98 auth, NIP-04 DMs, Schnorr (`coincurve`) |
| AI | Anthropic Claude Haiku (optional, strength normalization only) |

**Deploy:** single `main` branch → backend + Postgres on Render (`render.yaml`), frontend on Vercel (`frontend/`). Full guide in `DEPLOYMENT.md`.

## Local development

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

## Testing

```bash
cd backend && python -m pytest          # backend (SQLite, no Postgres needed)
cd frontend && npm test                 # unit (Vitest)
cd frontend && npm run test:e2e         # e2e (Playwright)
```

## Docs

Environment reference and deploy steps: `DEPLOYMENT.md`. Design specs and plans: `docs/superpowers/`.

## License

MIT — see [LICENSE](LICENSE)
