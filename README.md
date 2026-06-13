# SquadSync

Intelligent team formation for hackathons, workshops, and events. No account required — connect with a [Nostr](https://nostr.com) identity.

## Features

- **Nostr auth** — sign in with a browser extension (NIP-07), generate a new keypair, or paste an existing `nsec` key
- **Event management** — create events, share a QR code for registration, manage participants
- **Allocation engine** — balance teams by skill level, role diversity, and experience
- **No KYC** — self-sovereign identity, no email or password required
- **Dark mode** by default, light mode available in Settings

## Stack

| Layer | Tech |
|---|---|
| Frontend | Next.js 16, React 19, Tailwind v4, NextAuth v5 |
| Backend | FastAPI, SQLAlchemy, SQLite / PostgreSQL |
| Auth | Nostr NIP-98 HTTP Auth, BIP340 Schnorr signatures |

## Local setup

### Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL and SECRET_KEY
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL and AUTH_SECRET
npm run dev
```

The app runs at `http://localhost:3000` (or `3001` if 3000 is taken).

## Tests

```bash
# Backend
cd backend && pytest tests/ -v

# Frontend (type check)
cd frontend && npx tsc --noEmit
```

## How auth works

1. The organizer signs in by creating a signed Nostr event (kind 27235, NIP-98)
2. The backend verifies the BIP340 Schnorr signature via `coincurve`
3. A JWT is returned and stored in the session
4. Attendees register publicly via a QR code — no auth required

## License

MIT — see [LICENSE](LICENSE)
