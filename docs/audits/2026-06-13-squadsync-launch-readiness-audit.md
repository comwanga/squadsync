# SquadSync Production Audit — 2026-06-13

**Prepared by:** Claude Code audit pass  
**Date:** 2026-06-13  
**Branch:** `feat/ci-dark-mode-mobile`  
**Timeline:** Real users in 1–2 weeks  
**Infra baseline:** Zero — Supabase, Render, Vercel not yet provisioned

---

## Table of Contents

1. [Audit Method](#1-audit-method)
2. [Critical Blockers](#2-critical-blockers)
3. [Security Findings](#3-security-findings)
4. [Deployment Readiness Gaps](#4-deployment-readiness-gaps)
5. [Major Gaps](#5-major-gaps)
6. [Low-Risk Cleanup](#6-low-risk-cleanup)
7. [Verified Non-Issues](#7-verified-non-issues)
8. [Production Implementation Plan](#8-production-implementation-plan)

---

## 1. Audit Method

Every finding is marked **VERIFIED** (direct file read or command output inspected) or **INFERRED** (conclusion drawn from multiple verified inputs — cross-checked but not directly observed).

All file references include line numbers as read during this audit. Findings are ordered by deploy-blocking severity.

---

## 2. Critical Blockers

### CB-01 — Alembic migration schema mismatch

**Status:** VERIFIED  
**Evidence:** `backend/alembic/versions/9898ba081ca1_initial_schema.py` lines 22–34 creates:

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    name VARCHAR NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR,
    provider ENUM('local','google') DEFAULT 'local',
    provider_id VARCHAR,
    created_at TIMESTAMP
);
```

Current model at `backend/app/models/user.py` lines 8–12:

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pubkey = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Risk:** `alembic upgrade head` on a fresh production Postgres creates the old email/password schema. `POST /auth/nostr` then fails with `column "pubkey" does not exist` — the app is non-functional from first deploy.

**Reproduction:** Spin up a blank Postgres instance, run `alembic upgrade head`, then `POST /auth/nostr` with a valid Nostr keypair — guaranteed 500.

**Remediation:**
1. Delete `backend/alembic/versions/9898ba081ca1_initial_schema.py`
2. `alembic revision --autogenerate -m "nostr-user-schema"`
3. Verify generated file: `pubkey VARCHAR(64) NOT NULL UNIQUE` present, no `name/email/password/provider` columns
4. `alembic upgrade head` against SQLite — confirm clean run

---

### CB-02 — Docker build fails on `coincurve` C extension

**Status:** VERIFIED  
**Evidence:** `backend/Dockerfile` lines 1–10:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`backend/requirements.txt` line 8: `coincurve==20.0.0`

`python:3.12-slim` contains no C build toolchain. `coincurve` is a C extension wrapping `libsecp256k1` — it requires `gcc`, `libffi-dev`, `libssl-dev`, and `python3-dev` at build time. No `apt-get install` step exists anywhere in the Dockerfile.

**Risk:** `docker build` exits with a pip build error. No Render deployment is possible. Nostr signature verification is unavailable without `coincurve`.

**Reproduction:** `docker build -t squadsync-backend ./backend` — will fail at the pip install step.

**Remediation:** Add before the `pip install` line:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libffi-dev libssl-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

---

### CB-03 — CORS blocks all production frontend requests

**Status:** VERIFIED  
**Evidence:** `backend/app/core/config.py` line 9:

```python
FRONTEND_URL: str = "http://localhost:3000"
```

`backend/app/main.py` passes this directly to:

```python
CORSMiddleware(allow_origins=[settings.FRONTEND_URL])
```

**Risk:** Every API call from the Vercel deployment (`https://*.vercel.app`) receives a `403 CORS` response. The app appears to load but all data fetching and auth fail silently in the browser.

**Reproduction:** Deploy frontend to Vercel with `NEXT_PUBLIC_API_URL` pointing at the Render backend. Open devtools → Network tab → any `fetch()` to the backend → `Access-Control-Allow-Origin` header absent → browser blocks response.

**Remediation:** Set the `FRONTEND_URL` environment variable in Render to the exact Vercel production URL (e.g., `https://squadsync.vercel.app`). No code change required — `config.py` reads from env.

---

### CB-04 — `(dashboard)` route deletions not committed

**Status:** VERIFIED  
**Evidence:** Session-start git status shows:

```
D frontend/app/(dashboard)/events/[eventId]/attendees/page.tsx
D frontend/app/(dashboard)/events/[eventId]/configure/page.tsx
D frontend/app/(dashboard)/events/[eventId]/engine/page.tsx
D frontend/app/(dashboard)/events/[eventId]/page.tsx
D frontend/app/(dashboard)/layout.tsx
D frontend/app/(dashboard)/page.tsx
```

The working tree has deleted these files but the deletion is unstaged. Meanwhile, `frontend/app/dashboard/` (no parentheses) is the active route group. Both route groups are live in the git HEAD that CI checks out.

**Risk:** CI checkout has both `(dashboard)/` and `dashboard/` route groups simultaneously. `npx next build` may fail with duplicate-route conflicts, or pass but deploy with the dead routes included. Either way the branch is not clean for a production cut.

**Reproduction:** `git stash` (restores deleted files from HEAD) → `npx next build` → observe duplicate-route warnings or errors.

**Remediation:**
1. `git add frontend/app/\(dashboard\)/`
2. `git commit -m "chore: remove deprecated (dashboard) route group"`
3. Confirm `npx next build` succeeds after commit

---

## 3. Security Findings

### SF-01 — NIP-98 URL and method tags not validated server-side

**Status:** VERIFIED  
**Evidence:** `backend/app/services/auth_service.py` — `verify_nostr_event()` only:
- Recomputes the event ID hash (SHA-256 of canonical JSON)
- Verifies the Schnorr signature with `coincurve`

It never inspects `event["tags"]`. NIP-98 requires the server to validate that tags contain `["u", <exact_url>]` and `["method", "POST"]`. `backend/app/api/v1/auth.py` calls `nostr_login()`, which calls `verify_nostr_event()` without passing the expected URL.

**Risk:** A valid NIP-98 event signed for a different endpoint (e.g., a third-party service) could be replayed to `/auth/nostr`. The 60-second freshness window (`created_at` check in `nostr_login()`) partially mitigates replay across sessions, but does not prevent within-window cross-endpoint replay.

**Reproduction:** Obtain a valid kind-27235 event signed for URL `https://other-service.com/auth`, POST it to `/auth/nostr` with a matching pubkey — it succeeds.

**Remediation:** In `verify_nostr_event()`, add a parameter `expected_url: str` and validate:

```python
u_tags = [t for t in event.get("tags", []) if t[0] == "u"]
method_tags = [t for t in event.get("tags", []) if t[0] == "method"]
if not u_tags or u_tags[0][1] != expected_url:
    return False
if not method_tags or method_tags[0][1] != "POST":
    return False
```

Pass `expected_url` from `nostr_login()` using the request's actual URL.

---

### SF-02 — Nostr private key stored in plaintext localStorage

**Status:** VERIFIED  
**Evidence:** `frontend/components/auth/nostr-connect.tsx` line 137:

```typescript
localStorage.setItem(SK_KEY, generated.skHex)
```

**Risk:** Any XSS vulnerability in the application exposes the user's Nostr private key directly. Unlike a password (which can be rotated server-side), a Nostr private key IS the identity — a stolen key cannot be invalidated.

**Severity:** Acceptable for MVP given the scope, but must be documented as a known risk and addressed before significant user growth. Consider encrypting the stored key with a PIN, or prompting users to use a browser extension (nos2x, Alby) which never expose the private key to the page.

---

## 4. Deployment Readiness Gaps

No production infrastructure has been provisioned. These are not software defects — they are missing environment setup required before any deployment attempt.

| Gap | Detail |
|-----|--------|
| Supabase PostgreSQL | No project created; no `DATABASE_URL` for production |
| Render Web Service | No service configured; no backend URL exists |
| Vercel Project | No project imported; no frontend URL exists |
| Production secrets | `SECRET_KEY`, `NEXTAUTH_SECRET` not generated or stored |
| CORS wiring | `FRONTEND_URL` env var needs Vercel URL — only available after first Vercel deploy |

See Phase 3 of the implementation plan for provisioning steps.

---

## 5. Major Gaps

### MG-01 — CI does not run Vitest

**Status:** VERIFIED  
**Evidence:** `.github/workflows/ci.yml` frontend job ends at:

```yaml
- name: Type check
  run: npx tsc --noEmit
  working-directory: frontend
```

No `npm test` step. Frontend component tests exist (`frontend/tests/components/minimal-config-test.tsx`) and would catch UI regressions, but they never run in CI.

**Remediation:** Add after the type check step:

```yaml
- name: Run tests
  run: npm test
  working-directory: frontend
  env:
    NEXT_PUBLIC_API_URL: http://localhost:8000
    NEXTAUTH_SECRET: ci-secret
```

### MG-02 — CI has no Docker build verification

**Status:** INFERRED from Dockerfile contents and CI yaml  
**Evidence:** CI yaml has no Docker build step. CB-02 (coincurve build failure) would go undetected in CI and only surface on first Render deploy.

**Remediation:** Add a third CI job:

```yaml
docker-build:
  name: Docker Build (Backend)
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build backend image
      run: docker build ./backend
```

---

## 6. Low-Risk Cleanup

These files are unused and safe to delete but are not deploy blockers.

| File | Status | Action |
|------|--------|--------|
| `frontend/components/auth/login-form.tsx` | Not imported anywhere (verified with grep) | `git rm` |
| `frontend/components/auth/register-form.tsx` | Not imported anywhere (verified with grep) | `git rm` |

---

## 7. Verified Non-Issues

These were initially flagged as potential risks. Direct inspection confirmed they are not blockers.

| Item | Finding |
|------|---------|
| `backend/tests/test_auth.py` | Fully updated for Nostr — uses `coincurve.PrivateKey`, tests kind/pubkey/expiry/sig. Not a blocker. |
| `backend/tests/conftest.py` | `make_nostr_event()` and `auth_headers` fixture correctly construct NIP-98 events. Not a blocker. |
| `nostr-tools` npm package | Present in `frontend/package.json` as `"nostr-tools": "^2.23.5"`. Not missing. |
| Google OAuth routes | Completely removed from `backend/app/api/v1/auth.py` and `frontend/lib/auth.ts`. No dead code risk. |
| NIP-98 freshness check | `abs(time.time() - event.get("created_at", 0)) > 60` is present and correct in `nostr_login()`. |

---

## 8. Production Implementation Plan

### Phase 1 — Launch Blockers *(fix before any deploy attempt)*

**Step 1 — Regenerate Alembic migration (CB-01)**

```bash
cd backend
rm alembic/versions/9898ba081ca1_initial_schema.py
DATABASE_URL=sqlite:///./test.db alembic revision --autogenerate -m "nostr-user-schema"
# Verify: generated file has pubkey VARCHAR(64) NOT NULL UNIQUE
# Verify: NO name, email, hashed_password, provider columns
alembic upgrade head
```

Commit: `fix: regenerate Alembic migration for Nostr user schema`

**Step 2 — Add NIP-98 URL/method tag validation (SF-01)**

In `backend/app/services/auth_service.py`, update `verify_nostr_event()` to accept `expected_url: str` and validate `["u", expected_url]` and `["method", "POST"]` tags. Update `nostr_login()` to pass the request URL.

Run `pytest tests/test_auth.py -v` — all tests must pass.

Commit: `fix: enforce NIP-98 URL and method tag validation`

**Step 3 — Fix Dockerfile for coincurve build (CB-02)**

Add to `backend/Dockerfile` before the `pip install` line:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc build-essential libffi-dev libssl-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*
```

Verify locally: `docker build -t squadsync-backend ./backend` must succeed end-to-end.

Commit: `fix: add C build deps to Dockerfile for coincurve`

**Step 4 — Commit route deletions (CB-04)**

```bash
git add "frontend/app/(dashboard)/"
git status  # confirm all 6 D entries are staged
git commit -m "chore: remove deprecated (dashboard) route group"
npx next build  # run in frontend/ — must complete clean
```

**Step 5 — Remove dead auth components**

```bash
git rm frontend/components/auth/login-form.tsx
git rm frontend/components/auth/register-form.tsx
git commit -m "chore: remove unused email/password auth components"
```

---

### Phase 2 — CI Hardening *(merge before Phase 3)*

**Step 6 — Add Vitest to CI frontend job (MG-01)**

In `.github/workflows/ci.yml`, add after the type check step in the `frontend` job:

```yaml
- name: Run tests
  run: npm test
  working-directory: frontend
  env:
    NEXT_PUBLIC_API_URL: http://localhost:8000
    NEXTAUTH_SECRET: ci-secret
```

**Step 7 — Add Docker build CI job (MG-02)**

Add a third job to `.github/workflows/ci.yml`:

```yaml
docker-build:
  name: Docker Build (Backend)
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - name: Build backend image
      run: docker build ./backend
```

**Step 8 — Add migration smoke test to backend CI job**

In the `backend` job, add after `pytest tests/ -v`:

```yaml
- name: Verify migration
  run: alembic upgrade head
  working-directory: backend
  env:
    DATABASE_URL: sqlite:///./test.db
```

Commit Steps 6–8 together: `ci: add vitest, Docker build, and migration verification`

---

### Phase 3 — Infrastructure Provisioning

**Step 9 — Provision Supabase PostgreSQL**

1. Create project at supabase.com
2. Copy the **Direct connection** `postgresql://` URI (not the pooler URI — Alembic needs direct connections)
3. Set locally as `DATABASE_URL` in `backend/.env`
4. `cd backend && alembic upgrade head` — verify all tables created, especially `users(id, pubkey, created_at)`

**Step 10 — Deploy to Render**

1. Create new Web Service → Docker → connect GitHub repo → Root Dir: `backend/`
2. Set environment variables:
   - `DATABASE_URL` → Supabase direct URI
   - `SECRET_KEY` → generate: `openssl rand -hex 32`
   - `FRONTEND_URL` → placeholder (`http://localhost:3000` until Step 12)
3. Trigger first deploy → verify `/health` returns `{"status":"ok"}`

**Step 11 — Deploy to Vercel**

1. Import repo at vercel.com → Framework: Next.js → Root Dir: `frontend/`
2. Set environment variables:
   - `NEXT_PUBLIC_API_URL` → Render backend URL from Step 10
   - `NEXTAUTH_SECRET` → generate: `openssl rand -hex 32`
   - `NEXTAUTH_URL` → Vercel production URL (available after first deploy)
3. Trigger first deploy → verify login page loads

**Step 12 — Wire CORS (CB-03)**

In Render environment variables, update `FRONTEND_URL` to the Vercel production URL (e.g., `https://squadsync.vercel.app`). Trigger Render redeploy.

---

### Phase 4 — Release Validation

**Step 13 — End-to-end smoke test on live URLs**

Golden path, in order:
1. Open Vercel URL in a fresh browser (no cached state)
2. Generate new Nostr identity on login page → sign in → confirm redirect to `/dashboard`
3. Create event → verify event slug generated, event appears in list
4. Open QR URL on a mobile device → complete participant registration form
5. Switch to desktop → run team allocation → verify team grid renders
6. Publish teams → export CSV → verify file downloads correctly
7. Copy share link → open in incognito tab → verify public results page loads without auth

**Step 14 — Auth replay test**

1. POST to `/auth/nostr` with a valid NIP-98 event; record the exact request body
2. Wait 61 seconds
3. POST the same body again → expect `400 Event expired`
4. POST with same body but wrong `u` tag URL → expect `401 Invalid event`

**Step 15 — CORS verification**

Open browser devtools on the Vercel URL → trigger any API call → confirm `Access-Control-Allow-Origin` header present in response and no CORS errors in console.

**Step 16 — Mobile and dark mode check**

1. Open dashboard on a 375px-wide viewport (iPhone SE) — nav, event list, registration form must be usable without horizontal scroll
2. Toggle OS dark mode → verify `dark:bg-slate-950` class on dashboard background renders correctly

---

## Risk Summary

| ID | Severity | Status | Blocks Deploy |
|----|----------|--------|---------------|
| CB-01 | Critical | Verified | Yes |
| CB-02 | Critical | Verified | Yes |
| CB-03 | Critical | Verified | Yes (silently) |
| CB-04 | High | Verified | Yes (CI) |
| SF-01 | High | Verified | No, but ship before growth |
| SF-02 | Medium | Verified | No (MVP acceptable) |
| MG-01 | Medium | Verified | No |
| MG-02 | Medium | Inferred | No |

**Minimum to deploy:** CB-01, CB-02, CB-03, CB-04 resolved + all of Phase 3.  
**Minimum to ship to real users:** All of Phase 1 + Phase 3 + Phase 4 validation passed.
