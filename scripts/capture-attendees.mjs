// Re-captures ONLY the attendees guide screenshot (04-attendees-qr.png).
// The previous capture fired before the page finished loading — the QR card was
// still a skeleton and the table showed "0 participants". This waits for the QR
// card to fully render (its "Download PNG" button) AND for the populated table
// (the "6 participants" footer) before shooting, so both the QR and the roster
// are clearly visible.
// Prereqs: backend on :8000 and frontend on :3000 (see scripts/capture-guide.mjs header).
//   node scripts/capture-attendees.mjs
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

  // Log in (the attendees page is auth-gated) — same key the API token uses.
  await page.goto(`${BASE}/login`);
  await page.fill('input[id="nsec"]', NSEC);
  await page.click('button:has-text("Connect with nsec key")');
  await page.waitForURL(`${BASE}/dashboard`, { timeout: 90000 });
  await page.waitForSelector('h1:has-text("Overview")', { timeout: 60000 });

  // Create + activate an event and register participants via the API (same user).
  const t = await token();
  const headers = { "Content-Type": "application/json", Authorization: `Bearer ${t}` };
  const ev = await (await fetch(`${API}/api/v1/events`, {
    method: "POST", headers, body: JSON.stringify({ title: "AI for Agriculture Hackathon", team_count: 3 }),
  })).json();
  await fetch(`${API}/api/v1/events/${ev.id}`, { method: "PATCH", headers, body: JSON.stringify({ status: "active" }) });
  const slug = (await (await fetch(`${API}/api/v1/events/${ev.id}`, { headers })).json()).registration_slug;

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

  // Attendees page — wait for BOTH the fully-rendered QR card and the populated table.
  await page.goto(`${BASE}/dashboard/events/${ev.id}/attendees`, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("text=Registration QR Code", { timeout: 60000 });
  await page.waitForSelector('button:has-text("Download PNG")', { timeout: 60000 }); // QR card done
  await page.waitForSelector("text=6 participants", { timeout: 60000 });             // table populated
  await page.waitForSelector("text=Carol", { timeout: 60000 });                      // rows painted
  // Settle a beat so the QR svg + logo overlay are fully painted before the shot.
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${OUT}/04-attendees-qr.png`, fullPage: false });
  console.log("📸 04-attendees-qr.png recaptured");

  await browser.close();
}

main().catch(e => { console.error("❌ capture failed:", e.message); process.exit(1); });
