// Re-captures ONLY the join-form guide screenshot (05-join-form.png) after the
// registration form gained the optional npub field (B2b). Other guide shots are
// captured at 1280px where layout is unchanged, so they don't need regenerating.
// Prereqs: backend on :8000 and frontend on :3000 (see scripts/capture-guide.mjs header).
//   node scripts/capture-join.mjs
import { chromium } from "playwright";
import { generateSecretKey, getPublicKey, finalizeEvent } from "nostr-tools";
import { mkdirSync } from "fs";

const BASE = process.env.GUIDE_BASE ?? "http://localhost:3000";
const API = process.env.GUIDE_API ?? "http://localhost:8000";
const OUT = "frontend/public/guide";

const SK = generateSecretKey();
const PK = getPublicKey(SK);

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
  const t = await token();
  const ev = await (await fetch(`${API}/api/v1/events`, {
    method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
    body: JSON.stringify({ title: "AI for Agriculture Hackathon", team_count: 3 }),
  })).json();
  await fetch(`${API}/api/v1/events/${ev.id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${t}` },
    body: JSON.stringify({ status: "active" }),
  });
  const slug = (await (await fetch(`${API}/api/v1/events/${ev.id}`, { headers: { Authorization: `Bearer ${t}` } })).json()).registration_slug;

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const join = await ctx.newPage();
  await join.goto(`${BASE}/join/${slug}`, { waitUntil: "domcontentloaded" });
  await join.waitForSelector("text=Primary Strength", { timeout: 90000 });
  await join.waitForSelector('input[id="npub"]', { timeout: 90000 }); // new B2b field must render
  await join.screenshot({ path: `${OUT}/05-join-form.png`, fullPage: false });
  console.log("📸 05-join-form.png recaptured");
  await browser.close();
}

main().catch(e => { console.error("❌ capture failed:", e.message); process.exit(1); });
