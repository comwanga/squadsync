// Captures the 8 guide screenshots into frontend/public/guide/.
// Prereqs (run in separate terminals from repo root):
//   1) backend:  cd backend && DATABASE_URL="sqlite:///./guide.db" SECRET_KEY=guide \
//                python -m alembic upgrade head && \
//                DATABASE_URL="sqlite:///./guide.db" SECRET_KEY=guide PUBLIC_API_URL=http://localhost:8000 \
//                python -m uvicorn app.main:app --port 8000
//   2) frontend: cd frontend && NEXT_PUBLIC_API_URL=http://localhost:8000 AUTH_SECRET=guide-secret \
//                AUTH_URL=http://localhost:3000 npm run dev   (serves on :3000)
//   3) capture:  node scripts/capture-guide.mjs
import { chromium } from "playwright";
import { generateSecretKey, getPublicKey, finalizeEvent } from "nostr-tools";
import { nsecEncode } from "nostr-tools/nip19";
import { mkdirSync } from "fs";

const BASE = process.env.GUIDE_BASE ?? "http://localhost:3000";
const API = process.env.GUIDE_API ?? "http://localhost:8000";
const OUT = "frontend/public/guide";

const SK = generateSecretKey();
const PK = getPublicKey(SK);
const NSEC = nsecEncode(SK);

const shot = async (page, name) => {
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: false });
  console.log(`  📸 ${name}.png`);
};

async function token() {
  const event = finalizeEvent(
    { kind: 27235, created_at: Math.floor(Date.now() / 1000), tags: [["u", `${API}/auth/nostr`], ["method", "POST"]], content: "" },
    SK
  );
  const res = await fetch(`${API}/auth/nostr`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pubkey: PK, event }),
  });
  if (!res.ok) throw new Error(`/auth/nostr ${res.status}: ${await res.text()}`);
  return (await res.json()).access_token;
}

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  // 01 login
  await page.goto(`${BASE}/login`);
  await page.waitForLoadState("domcontentloaded");
  await shot(page, "01-login");

  await page.fill('input[id="nsec"]', NSEC);
  await page.click('button:has-text("Connect with nsec key")');
  // Dev-mode first-hit route compilation can be slow — use generous timeouts.
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 90000 });
  await page.goto(`${BASE}/dashboard`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector('h1:has-text("Overview")', { timeout: 60000 });

  // 02 create-event dialog
  await page.click('button:has-text("New Event")');
  await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
  await page.fill('input[id="title"]', "AI for Agriculture Hackathon");
  await page.fill('#description', "Build AI + satellite tools to improve crop yields.");
  await page.fill('input[id="team_count"]', "3");
  await shot(page, "02-create-event");
  await page.click('button:has-text("Create Event")');
  await page.waitForURL(/\/dashboard\/events\/[^/]+$/, { timeout: 15000 });
  const eventId = page.url().split("/events/")[1];

  // 03 event dashboard
  await page.waitForLoadState("domcontentloaded");
  await shot(page, "03-event-dashboard");

  // activate via API
  const t = await token();
  await fetch(`${API}/api/v1/events/${eventId}`, {
    method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
    body: JSON.stringify({ status: "active" }),
  });
  const slug = (await (await fetch(`${API}/api/v1/events/${eventId}`, { headers: { Authorization: `Bearer ${t}` } })).json()).registration_slug;

  // register participants via API (NEW fields)
  const people = [
    { name: "Alice", email: "alice@t.com", primary_strength: "technical", experience_level: "advanced" },
    { name: "Bob", email: "bob@t.com", primary_strength: "design", experience_level: "intermediate" },
    { name: "Carol", email: "carol@t.com", primary_strength: "other", strength_other: "Agronomist", experience_level: "advanced" },
    { name: "Dave", email: "dave@t.com", primary_strength: "planning", experience_level: "beginner" },
    { name: "Eve", email: "eve@t.com", primary_strength: "research", experience_level: "advanced" },
    { name: "Frank", email: "frank@t.com", primary_strength: "coordination", experience_level: "intermediate" },
  ];
  for (const p of people) {
    await fetch(`${API}/api/v1/events/${slug}/register`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(p),
    });
  }

  // 04 attendees + QR
  await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Registration QR Code", { timeout: 45000 });
  await shot(page, "04-attendees-qr");

  // 05 public join form (NEW form)
  const join = await ctx.newPage();
  await join.goto(`${BASE}/join/${slug}`, { waitUntil: "domcontentloaded" });
  await join.waitForSelector("text=Primary Strength", { timeout: 45000 });
  await shot(join, "05-join-form");
  await join.close();

  // 06 configure
  await page.goto(`${BASE}/dashboard/events/${eventId}/configure`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Balancing Weights", { timeout: 45000 });
  await shot(page, "06-configure");

  // 07 engine results
  await page.goto(`${BASE}/dashboard/events/${eventId}/engine`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForSelector("text=Allocation Engine", { timeout: 45000 });
  await page.click('button:has-text("Generate Teams")');
  await page.waitForSelector("text=Team 01", { timeout: 45000 });
  await shot(page, "07-engine-results");

  // 08 published
  await page.click('button:has-text("Publish Teams")');
  await page.waitForSelector('button:has-text("Export CSV")', { timeout: 20000 });
  await shot(page, "08-published");

  // 09 attendees after allocation — shows categorized "Other" + Source badge
  await page.goto(`${BASE}/dashboard/events/${eventId}/attendees`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Registration QR Code", { timeout: 45000 });
  await shot(page, "09-ai-category");

  await browser.close();
  console.log("\n✅ Guide screenshots captured to frontend/public/guide/\n");
}

main().catch(e => { console.error("❌ capture failed:", e.message); process.exit(1); });
