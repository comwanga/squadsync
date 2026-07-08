# SquadSync Frontend

Next.js app for the SquadSync organizer dashboard, participant join flow, and public team results.

## Local Setup

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

The frontend expects the API at `NEXT_PUBLIC_API_URL`, which defaults to `http://localhost:8000` in the example env file.

## Environment

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
AUTH_URL=http://localhost:3000
AUTH_SECRET=change-me-to-a-long-random-string
```

Optional AI and rewards settings are backend-only. The frontend works without them.

## Scripts

```bash
npm run dev       # start Next.js locally
npm run lint      # ESLint
npm test          # Vitest unit/component tests
npm run build     # production build
npm run test:e2e  # Playwright route smoke tests
```

## Product Notes

Keep the default flow simple:

1. Organizer creates an event.
2. Organizer shares a QR code or link.
3. Participants join without accounts.
4. Organizer generates deterministic teams.
5. Results are shared publicly.

Do not introduce protocol or wallet terminology into primary screens. Optional advanced settings should stay out of the normal onboarding path.
