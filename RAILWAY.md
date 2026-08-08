# Deploying SquadSync on Railway

Single-platform deployment — both frontend and backend run on Railway with a
managed PostgreSQL database. No Vercel, no Render.

---

## Quick deploy

1. Push this branch to GitHub.

2. In the Railway dashboard → **New Project** → **Deploy from GitHub repo**
   → select this repository.

3. Railway reads `railway.toml` and provisions:
   - `squadsync-db` — managed PostgreSQL 16
   - `squadsync-api` — FastAPI backend (builds from `backend/Dockerfile`)
   - `squadsync-web` — Next.js frontend (builds from `frontend/Dockerfile`)

4. Set the required secrets. Go to each service → **Variables** and set:

   **squadsync-api**
   | Key | How to get |
   |---|---|
   | `SECRET_KEY` | Generate: `openssl rand -base64 32` |
   | `DATABASE_URL` | Railway auto-injects this from the Postgres link — no need to set it |
   | `FRONTEND_URL` | Railway URL of `squadsync-web`, e.g. `https://squadsync-web.up.railway.app` |
   | `PUBLIC_API_URL` | Railway URL of `squadsync-api`, e.g. `https://squadsync-api.up.railway.app` |

   **squadsync-web**
   | Key | How to get |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | Same as `PUBLIC_API_URL` above — **must match exactly** |
   | `AUTH_SECRET` | Generate: `openssl rand -base64 32` — must be the same value in every environment |

   > **Do not set `AUTH_URL`.** The app uses `trustHost: true`, so Auth.js derives
   > the URL from the request host.

5. **Redeploy** after setting variables — Railway needs to rebuild `squadsync-web`
   since `NEXT_PUBLIC_API_URL` is inlined at build time.

6. Done. Open `squadsync-web`'s Railway URL.

---

## Environment reference

| Key | Service | Required | Notes |
|---|---|---|---|
| `DATABASE_URL` | api | ✅ | Auto-injected by Railway from the Postgres service link |
| `SECRET_KEY` | api | ✅ | JWT signing key. Generate a strong random string |
| `FRONTEND_URL` | api | ✅ | CORS origin. No trailing slash |
| `PUBLIC_API_URL` | api | ✅ | Used for NIP-98 auth URL binding. Must equal `NEXT_PUBLIC_API_URL` |
| `NEXT_PUBLIC_API_URL` | web | ✅ | Inlined at build time. Must equal `PUBLIC_API_URL` |
| `AUTH_SECRET` | web | ✅ | NextAuth session secret. Must be set or `/api/auth/session` returns 500 |
| `ANTHROPIC_API_KEY` | api | optional | Enables AI normalization of free-text "Other" strengths |
| `SQUADSYNC_NSEC` | api | optional | Dedicated bot Nostr nsec for DM signing. Unset → DMs no-op |
| `FEEDBACK_NPUB` | api | optional | Owner npub for feedback DMs |
| `NOSTR_RELAYS` | api | optional | Defaults to `relay.damus.io,nos.lol,relay.nostr.band` |

---

## Architecture

```
                   ┌──────────────────────┐
                   │   load balancer      │
                   │   (Railway)          │
                   └──────┬───────────────┘
                          │
            ┌─────────────┴──────────────┐
            │                            │
    ┌───────▼──────┐            ┌────────▼──────┐
    │ squadsync-web│            │ squadsync-api │
    │  Next.js 16  │────HTTP────▶  FastAPI      │
    │  port 3000   │            │  port 8000    │
    └──────────────┘            └───────┬───────┘
                                       │
                                       │ TCP:5432
                                       │
                               ┌───────▼──────┐
                               │ squadsync-db │
                               │ PostgreSQL 16│
                               └──────────────┘
```

All HTTPS terminates at Railway's load balancer. Internal traffic between
services uses Railway's private network (service DNS names).

---

## Running migrations

Migrations run automatically on every deploy — the backend's `CMD` runs
`alembic upgrade head` before starting the server. To run them manually:

```bash
railway connect --service squadsync-api
railway run "alembic upgrade head"
```

---

## Local development

For local dev, use Docker Compose:

```bash
docker compose up --build
```

Frontend: `http://localhost:3000`
Backend health: `http://localhost:8000/health`
API docs: `http://localhost:8000/docs`

No env changes needed for local — `docker-compose.yml` has defaults for all
required variables.

---

## Gotchas

- **`NEXT_PUBLIC_*` needs a rebuild.** Changing `NEXT_PUBLIC_API_URL` after deploy
  won't take effect until the web service redeploys — these vars are inlined at
  build time.
- **URLs must match exactly.** `NEXT_PUBLIC_API_URL` and `PUBLIC_API_URL` must be
  identical, no trailing slash — NIP-98 auth binds to this URL.
- **Railway free tier** includes $5 credit/month. The Postgres + two services fit
  within that for light use. Monitor usage in the dashboard.
- **Cold starts.** Railway's hobby plan has a sleep policy after inactivity.
  Upgrade to a paid plan for production use.
