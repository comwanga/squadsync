import { defineConfig, devices } from "@playwright/test";

/**
 * Route smoke tests. Boots the backend (migrated, SQLite) and the Next dev
 * server, signs in with a real generated Nostr identity, then visits every
 * nav destination and key route asserting none 404 or 500.
 *
 * The dashboard 404 class of bug only surfaces when authenticated — logged out,
 * the dashboard layout's auth() redirect to /login masks a missing route — so
 * these tests log in for real rather than hitting routes anonymously.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      // Migrate then serve the API. PUBLIC_API_URL is intentionally unset so the
      // NIP-98 binding uses the live request URL (http://localhost:8000/...),
      // which matches the URL the frontend signs.
      command:
        "python -m alembic upgrade head && python -m uvicorn app.main:app --port 8000",
      cwd: "../backend",
      url: "http://localhost:8000/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        DATABASE_URL: "sqlite:///./e2e_smoke.db",
        SECRET_KEY: "e2e-test-secret",
      },
    },
    {
      command: "npm run dev",
      url: "http://localhost:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8000",
        AUTH_SECRET: "e2e-test-secret-not-for-production",
        AUTH_URL: "http://localhost:3000",
      },
    },
  ],
});
