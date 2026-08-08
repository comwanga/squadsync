# Deploying SquadSync on Railway

Single-platform deployment — both frontend and backend run on Railway with a
managed PostgreSQL database. No Vercel, no Render.

---

## Step 1: Push this code to GitHub

Make sure the repo is up to date on `main`. Railway reads `railway.toml`
automatically when the repo is connected.

---

## Step 2: Create the Railway project

1. Go to [railway.app](https://railway.app) → **New Project**
2. Choose **Deploy from GitHub repo**
3. Select `comwanga/squadsync`
4. Railway reads `railway.toml` and provisions three services:

   | Service | What it is | Port |
   |---|---|---|
   | `squadsync-db` | PostgreSQL 16 | internal |
   | `squadsync-api` | FastAPI backend | 8000 |
   | `squadsync-web` | Next.js frontend | 3000 |

5. The initial builds will fail — that's expected. `squadsync-web` can't build
   without `NEXT_PUBLIC_API_URL` set, and `squadsync-api` needs the `SECRET_KEY`
   reference resolved. Move on to step 3.

> **If Railway only creates a single service** (tries to build the repo root
> with Railpack), delete the project and recreate it. Railway caches the
> project type at creation time — the `railway.toml` must be on the default
> branch *before* the project is created.

---

## Step 3: Link Postgres to the API service

1. In the Railway project, go to **squadsync-db → Variables**
2. There should be a `DATABASE_URL` entry already there. If not, generate a
   connection string (Railway usually auto-provisions it).
3. Go to **squadsync-api → Variables** and add a **Reference** variable:
   - Click **New Variable** → **Reference**
   - Source: `squadsync-db`
   - Variable: `DATABASE_URL`

   This injects the Postgres connection string into the API service.

---

## Step 4: Set required secrets

Go to **squadsync-api → Variables** and add:

| Key | Value |
|---|---|
| `SECRET_KEY` | Run `openssl rand -base64 32` in a terminal |

Go to **squadsync-web → Variables** and add:

| Key | Value |
|---|---|
| `AUTH_SECRET` | Run `openssl rand -base64 32` |

---

## Step 5: Get the service URLs

After the first deploy (even a failed one), Railway assigns public domains.

1. Go to **squadsync-api → Settings** → copy the domain
   Example: `squadsync-api.up.railway.app`
2. Go to **squadsync-web → Settings** → copy the domain
   Example: `squadsync-web.up.railway.app`

---

## Step 6: Set cross-reference variables

Go to **squadsync-api → Variables** and add:

| Key | Value |
|---|---|
| `PUBLIC_API_URL` | `https://squadsync-api.up.railway.app` (your actual API URL, NO trailing slash) |
| `FRONTEND_URL` | `https://squadsync-web.up.railway.app` (your actual web URL, NO trailing slash) |

Go to **squadsync-web → Variables** and add:

| Key | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://squadsync-api.up.railway.app` (same as `PUBLIC_API_URL` above) |

> `NEXT_PUBLIC_API_URL` must match `PUBLIC_API_URL` exactly. The NIP-98 auth
> binds to this URL, and a mismatch causes sign-in to fail silently.

---

## Step 7: Redeploy the web service

`NEXT_PUBLIC_API_URL` is inlined at **build time**. Changing it after deploy
requires a rebuild.

1. Go to **squadsync-web → Deployments**
2. Click the most recent deployment → **Redeploy**

Or push any commit to the repo — Railway picks it up automatically.

---

## Step 8: Verify

1. Open `https://squadsync-web.up.railway.app`
2. Click **Create organizer key** → save the recovery key → sign in
3. Create an event → activate it → register participants → allocate teams

---

## Environment reference

### squadsync-api

| Key | Required | Notes |
|---|---|---|
| `DATABASE_URL` | ✅ | Reference to `squadsync-db`. Auto-injected by Railway. |
| `SECRET_KEY` | ✅ | JWT signing key. Generate a strong random string. |
| `FRONTEND_URL` | ✅ | CORS origin. No trailing slash. |
| `PUBLIC_API_URL` | ✅ | NIP-98 auth binding. Must equal `NEXT_PUBLIC_API_URL`. |
| `ALGORITHM` | no | Defaults to `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | no | Defaults to `1440` (24h). |
| `ANTHROPIC_API_KEY` | optional | Enables AI normalization of free-text "Other" strengths. |
| `SQUADSYNC_NSEC` | optional | Dedicated bot Nostr nsec for DM signing. Unset → DMs no-op. |
| `FEEDBACK_NPUB` | optional | Owner npub for feedback DMs. |
| `NOSTR_RELAYS` | optional | Defaults to `damus.io,nos.lol,nostr.band`. |

### squadsync-web

| Key | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | ✅ | Must equal `PUBLIC_API_URL`. Inlined at build time. |
| `AUTH_SECRET` | ✅ | NextAuth session secret. 500 on `/api/auth/session` if missing. |

> **Do not set `AUTH_URL`.** The app uses `trustHost: true`, so Auth.js
> derives the URL from the request host automatically.

---

## Architecture

```
                   Railway load balancer
                          │
            ┌─────────────┴──────────────┐
            │                            │
    ┌───────▼──────┐            ┌────────▼──────┐
    │ squadsync-web│            │ squadsync-api │
    │  Next.js 16  │────HTTP────▶  FastAPI      │
    │  Dockerfile  │            │  Dockerfile   │
    │  port 3000   │            │  port 8000    │
    └──────────────┘            └───────┬───────┘
                                       │ TCP:5432
                               ┌───────▼──────┐
                               │ squadsync-db │
                               │ PostgreSQL 16│
                               └──────────────┘
```

All HTTPS terminates at Railway's load balancer. `squadsync-web` calls the
API through the Next.js backend proxy (`/api/backend/*`) which forwards
authenticated requests server-side.

---

## Migrations

Migrations run automatically on every deploy. The backend Dockerfile runs
`alembic upgrade head` before starting uvicorn.

To run manually:
```bash
railway connect --service squadsync-api
railway run "alembic upgrade head"
```

---

## Local development

Use Docker Compose:
```bash
docker compose up --build
```

Frontend: `http://localhost:3000`
API docs: `http://localhost:8000/docs`

---

## Gotchas

- **`NEXT_PUBLIC_*` requires a redeploy.** These are inlined at Next.js build
  time. Changing them in the dashboard has no effect until the service
  rebuilds.
- **URLs must match exactly.** `NEXT_PUBLIC_API_URL` and `PUBLIC_API_URL` must
  be identical, no trailing slash.
- **Cold starts.** Railway's hobby plan sleeps idle services. Upgrade for
  production use.
- **CORS is strict.** Only the `FRONTEND_URL` origin is allowed. If you add a
  custom domain, update `FRONTEND_URL` accordingly.
