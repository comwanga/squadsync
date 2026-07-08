# Contributing

SquadSync should stay simple by default: create an event, share a QR/link, let participants join without accounts, generate deterministic teams, and publish results.

## Local Development

```bash
docker compose up --build
```

Or run services manually:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m uvicorn app.main:app --port 8000

cd ../frontend
npm install
cp .env.local.example .env.local
npm run dev
```

## Checks

```bash
npm test
npm run lint
npm run build
npm run e2e
```

Backend tests use SQLite and do not require Postgres. The app must work without an Anthropic API key and without reward payout setup.

## Product Guardrails

- Participant registration must not require login.
- Team generation must be deterministic, explainable, reproducible, and testable.
- Optional AI may normalize free-text strengths, but must not decide teams.
- Optional rewards must stay out of the default onboarding path.
- Avoid protocol and wallet jargon in primary user screens.
