# Deploying SquadSync (Vercel + Render)

Frontend → **Vercel** (native Next.js). Backend + Postgres → **Render** (Docker, via `render.yaml`).

There's a deliberate ordering because the two services reference each other's URLs.

---

## 1. Backend + database on Render

1. Push this branch to GitHub (already done if you're on `fix/launch-blockers-p0-p1`).
2. Render Dashboard → **New → Blueprint** → select this repo.
3. Render reads `render.yaml` and provisions:
   - `squadsync-db` — free Postgres
   - `squadsync-api` — the Docker web service
   `DATABASE_URL` and `SECRET_KEY` are wired/generated automatically. Migrations run
   on every deploy (the Docker `CMD` runs `alembic upgrade head` before serving).
4. When the API is live, copy its URL (e.g. `https://squadsync-api.onrender.com`) and set
   **`PUBLIC_API_URL`** to that exact value in the service's **Environment** tab.
5. Leave **`FRONTEND_URL`** for now — you'll set it after Vercel (step 2).
6. Confirm `https://<your-api>.onrender.com/health` returns `{"status":"ok"}`.

## 2. Frontend on Vercel

1. Vercel → **Add New → Project** → import this repo.
2. **Root Directory: `frontend`** (important — the app isn't at the repo root).
3. Add environment variables. **Set them for _all_ environments (Production **and** Preview)** —
   each variable's environment checkboxes must include Preview, or branch/preview deployments
   500 on `/api/auth/session` (Auth.js `MissingSecret`):

   | Key | Value | Environments |
   |---|---|---|
   | `NEXT_PUBLIC_API_URL` | `https://squadsync-api.onrender.com` (your API URL — **must equal `PUBLIC_API_URL`**) | Production + Preview |
   | `AUTH_SECRET` | a strong random string — `openssl rand -base64 32` | Production + Preview |

   > **Do not set `AUTH_URL`.** The app sets `trustHost: true`, so Auth.js derives the URL from
   > the request host — this is what lets each Vercel **preview** URL work. A single hardcoded
   > `AUTH_URL` would break preview deployments (their URLs differ per branch/commit).

4. Deploy. Copy the resulting Vercel URL.

## 3. Close the loop

1. Back in Render → `squadsync-api` → Environment → set **`FRONTEND_URL`** to your Vercel
   URL (e.g. `https://squadsync.vercel.app`). Save — the service restarts.
2. Done. Open the Vercel URL and run the end-to-end test below.

---

## Environment reference

**Render — `squadsync-api`**

| Key | Source | Notes |
|---|---|---|
| `DATABASE_URL` | auto (blueprint) | from `squadsync-db` |
| `SECRET_KEY` | auto-generated | JWT signing key |
| `ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | 24h |
| `FRONTEND_URL` | **you set** | Vercel origin, for CORS. No trailing slash. |
| `PUBLIC_API_URL` | **you set** | this API's own https URL. Must equal `NEXT_PUBLIC_API_URL`. |
| `ANTHROPIC_API_KEY` | *optional* | enables AI normalization of free-text "Other" strengths. Unset = deterministic slug fallback. |
| `SQUADSYNC_NSEC` | *optional* | dedicated **bot** Nostr secret key (`nsec1…`) that signs/encrypts outgoing DMs. Never a personal key. Unset = DMs are a no-op. |
| `FEEDBACK_NPUB` | *optional* | owner's public key (`npub1…`) that receives Settings feedback DMs. |
| `NOSTR_RELAYS` | *optional* | comma-separated relay URLs. Defaults to `relay.damus.io,nos.lol,relay.nostr.band`. |

> **Nostr DM (optional).** The Settings feedback box (and later team notifications) send Nostr NIP-04 DMs. All three vars above are optional — leave them unset and feedback is still saved to the DB; only the DM is skipped. `SQUADSYNC_NSEC` must be a dedicated bot key, never a personal nsec.

**Vercel — frontend** (Root Directory `frontend`)

Set both for **Production + Preview** (see §2):

| Key | Notes |
|---|---|
| `NEXT_PUBLIC_API_URL` | API URL, must equal `PUBLIC_API_URL`. Build-time inlined. |
| `AUTH_SECRET` | NextAuth session secret. Required in every environment — if missing on Preview, those deployments 500 on `/api/auth/session`. |

`AUTH_URL` is intentionally **not** set — `trustHost: true` derives it from the request host so preview URLs work.

---

## End-to-end smoke test

1. Open the Vercel URL → sign in (generate a new Nostr identity).
2. Create an event → open it → set status to **Active** (registration only opens for active events).
3. Go to **Attendees** → the QR now encodes `https://<your-app>.vercel.app/join/<slug>`.
4. Scan it with a phone on **any** network → the registration form loads → submit.
5. Back on the dashboard, the attendee appears; run the engine, publish, and the share link
   (`/results/<id>`) is publicly viewable.

---

## Gotchas

- **URLs must match exactly.** `NEXT_PUBLIC_API_URL` (frontend) and `PUBLIC_API_URL` (backend)
  must be identical, with no trailing slash — the NIP-98 login binds to this URL.
- **Render free tier sleeps on idle.** The first request after inactivity takes ~30–50s to
  wake (cold start). Fine for testing; upgrade the plan for a real event.
- **Render free Postgres is time-limited** (expires after the free window). Don't put data you
  care about on it long-term.
- **CORS is strict.** Only the exact `FRONTEND_URL` origin is allowed. Vercel *preview*
  deployments have different URLs and will fail CORS — test on the production domain.
- **Changing `NEXT_PUBLIC_*` on Vercel requires a redeploy** (these are inlined at build time).
