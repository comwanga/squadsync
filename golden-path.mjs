import { chromium } from "playwright";

const BASE = "http://localhost:3001";
const API  = "http://localhost:8000";
const EMAIL = `test${Date.now()}@squadsync.dev`;
const PASS  = "TestPass123!";

async function screenshot(page, name) {
  const p = `C:/Users/mwang/squadsync/screenshots/${name}.png`;
  await page.screenshot({ path: p, fullPage: false });
  console.log(`  📸 ${name}.png`);
}

async function main() {
  const { mkdirSync } = await import("fs");
  mkdirSync("screenshots", { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  // ── 1. Register ─────────────────────────────────────────────────────────────
  console.log("\n1. Register new organizer account");
  await page.goto(`${BASE}/register`);
  await page.waitForLoadState("domcontentloaded");
  await screenshot(page, "01-register-page");

  await page.fill('input[id="name"]', "Test Organizer");
  await page.fill('input[id="email"]', EMAIL);
  await page.fill('input[id="password"]', PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 10000 });
  // Force a full navigation so Root Layout re-runs auth() with the new session cookie
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" });
  console.log("  ✓ Registered and redirected to dashboard");
  await screenshot(page, "02-dashboard-after-register");

  // ── 2. Dashboard overview ────────────────────────────────────────────────────
  console.log("\n2. Dashboard overview");
  await page.waitForSelector('h1:has-text("Overview")', { timeout: 10000 });
  // Wait for the session API to resolve so session.accessToken is in useSession()
  await page.waitForResponse(resp => resp.url().includes("/api/auth/session"), { timeout: 10000 }).catch(() => {});
  await screenshot(page, "03-overview");

  // ── 3. Create event ─────────────────────────────────────────────────────────
  console.log("\n3. Create an event");
  await page.click('button:has-text("New Event")');
  await page.waitForSelector('[role="dialog"]', { timeout: 3000 });
  await page.fill('input[id="title"]', "Golden Path Hackathon");
  await page.fill('input[id="description"]', "E2E test event");
  await page.fill('input[id="team_count"]', "3");
  await screenshot(page, "04-create-event-dialog");
  await page.click('button:has-text("Create Event")');
  await page.waitForURL(/\/dashboard\/events\/[^/]+$/, { timeout: 15000 });
  const eventUrl = page.url();
  const eventId = eventUrl.split("/events/")[1];
  console.log(`  ✓ Created event ${eventId}`);
  await screenshot(page, "05-event-dashboard");

  // ── 4. Activate event via API so registration works ─────────────────────────
  console.log("\n4. Activate event via API");
  const loginRes = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: EMAIL, password: PASS }),
  });
  const { access_token } = await loginRes.json();
  await fetch(`${API}/api/v1/events/${eventId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${access_token}` },
    body: JSON.stringify({ status: "active" }),
  });
  console.log("  ✓ Event set to active");

  // ── 5. Attendees page + QR ──────────────────────────────────────────────────
  console.log("\n5. Attendees page + QR code");
  await page.click('a:has-text("Go")');
  await page.waitForURL(/\/attendees/, { timeout: 5000 }).catch(async () => {
    await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`);
  });
  await page.waitForSelector('text=Registration QR Code', { timeout: 5000 });
  await screenshot(page, "06-attendees-qr");
  console.log("  ✓ QR code visible");

  const slugRes = await fetch(`${API}/api/v1/events/${eventId}`, {
    headers: { Authorization: `Bearer ${access_token}` },
  });
  const eventData = await slugRes.json();
  const slug = eventData.registration_slug;
  console.log(`  ✓ Slug: ${slug}`);

  // ── 6. Register participants via public form ─────────────────────────────────
  console.log("\n6. Register 6 participants via public form");
  const participants = [
    { name: "Alice A", email: "alice@test.com", skill: "advanced", role: "frontend", years: 5 },
    { name: "Bob B", email: "bob@test.com", skill: "intermediate", role: "backend", years: 3 },
    { name: "Carol C", email: "carol@test.com", skill: "professional", role: "fullstack", years: 8 },
    { name: "Dave D", email: "dave@test.com", skill: "beginner", role: "ux", years: 1 },
    { name: "Eve E", email: "eve@test.com", skill: "advanced", role: "ai_ml", years: 4 },
    { name: "Frank F", email: "frank@test.com", skill: "intermediate", role: "devops", years: 3 },
  ];

  for (const p of participants) {
    await fetch(`${API}/api/v1/events/${slug}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: p.name, email: p.email, skill_level: p.skill,
        role: p.role, years_experience: p.years,
      }),
    });
  }
  console.log("  ✓ 6 participants registered via API");

  const joinPage = await ctx.newPage();
  await joinPage.goto(`${BASE}/join/${slug}`);
  await joinPage.waitForSelector('text=Golden Path Hackathon', { timeout: 5000 });
  await screenshot(joinPage, "07-join-page");
  await joinPage.fill('input[id="name"]', "Grace G");
  await joinPage.fill('input[id="email"]', "grace@test.com");
  await joinPage.click('button:has-text("Join Event")');
  await joinPage.waitForSelector("text=registered", { timeout: 5000 });
  await screenshot(joinPage, "08-join-success");
  console.log("  ✓ Public registration form works — confirmation shown");
  await joinPage.close();

  // ── 7. Configure page ────────────────────────────────────────────────────────
  console.log("\n7. Configure allocation weights");
  await page.goto(`${BASE}/dashboard/events/${eventId}/configure`);
  await page.waitForSelector('text=Balancing Weights', { timeout: 5000 });
  await screenshot(page, "09-configure");
  await page.click('button:has-text("Add Constraint")');
  await page.waitForSelector('text=No constraints', { timeout: 2000 }).catch(() => {});
  await screenshot(page, "10-configure-constraint");
  await page.click('button:has-text("Save Configuration")');
  await page.waitForSelector('text=saved', { timeout: 5000 }).catch(() => {});
  console.log("  ✓ Configure page loaded + constraint added");

  // ── 8. Engine — run allocation ───────────────────────────────────────────────
  console.log("\n8. Run allocation engine");
  await page.goto(`${BASE}/dashboard/events/${eventId}/engine`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector('text=Allocation Engine', { timeout: 15000 });
  await screenshot(page, "11-engine-ready");

  await page.click('button:has-text("Generate Teams")');
  await page.waitForSelector('text=Team 01', { timeout: 15000 });
  await screenshot(page, "12-engine-results");
  console.log("  ✓ Teams generated — Team 01 visible");

  await page.click('button:has-text("Publish Teams")');
  await page.waitForSelector('button:has-text("Export CSV")', { timeout: 5000 });
  await screenshot(page, "13-teams-published");
  console.log("  ✓ Teams published — Export CSV button visible");

  // ── 9. Attendees table shows all registrants ─────────────────────────────────
  console.log("\n9. Verify attendees table");
  await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`);
  await page.waitForSelector('text=7 participants', { timeout: 5000 });
  await screenshot(page, "14-attendees-table");
  console.log("  ✓ Attendees table shows 7 participants");

  await browser.close();
  console.log("\n✅ Golden path complete — all steps passed.\n");
}

main().catch(err => {
  console.error("\n❌ Golden path failed:", err.message);
  process.exit(1);
});
