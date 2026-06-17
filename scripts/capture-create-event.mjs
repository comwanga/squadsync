// Re-captures ONLY the create-event guide screenshot (02-create-event.png).
// The dialog gained an "Event date & time (optional)" field after the original
// shot was taken, so the old screenshot misses it. This fills every field
// (including the date) and shoots the dialog.
// Prereqs: backend on :8000 and frontend on :3000 (see scripts/capture-guide.mjs header).
//   node scripts/capture-create-event.mjs
import { chromium } from "playwright";
import { generateSecretKey } from "nostr-tools";
import { nsecEncode } from "nostr-tools/nip19";
import { mkdirSync } from "fs";

const BASE = process.env.GUIDE_BASE ?? "http://localhost:3000";
const OUT = "frontend/public/guide";

const SK = generateSecretKey();
const NSEC = nsecEncode(SK);

async function main() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await ctx.newPage();

  // Log in (the dashboard is auth-gated).
  await page.goto(`${BASE}/login`);
  await page.fill('input[id="nsec"]', NSEC);
  await page.click('button:has-text("Connect with nsec key")');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 90000 });
  await page.waitForSelector('h1:has-text("Overview")', { timeout: 60000 });

  // Open the Create Event dialog and fill every field, including the date/time.
  await page.click('button:has-text("New Event")');
  await page.waitForSelector('[role="dialog"]', { timeout: 10000 });
  await page.fill('input[id="title"]', "AI for Agriculture Hackathon");
  await page.fill("#description", "Build AI + satellite tools to improve crop yields.");
  await page.fill('input[id="event_at"]', "2026-07-15T09:00");
  await page.fill('input[id="team_count"]', "3");
  await page.fill('input[id="participant_limit"]', "30");
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${OUT}/02-create-event.png`, fullPage: false });
  console.log("📸 02-create-event.png recaptured");

  await browser.close();
}

main().catch(e => { console.error("❌ capture failed:", e.message); process.exit(1); });
