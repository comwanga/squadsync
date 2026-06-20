// In-browser Lightning send (self-custody). The NWC spend credential lives only
// here in the browser and is never sent to the backend; the server only verifies
// the preimage we report. See docs/superpowers/specs/2026-06-20-self-custody-payouts-design.md.
import { finalizeEvent, nip04, type Event } from "nostr-tools";

export class LightningError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "LightningError";
  }
}

function hexToBytes(hex: string): Uint8Array {
  const clean = hex.trim();
  if (!/^[0-9a-fA-F]*$/.test(clean) || clean.length % 2 !== 0) {
    throw new LightningError("invalid hex");
  }
  return new Uint8Array(clean.match(/.{2}/g)?.map((b) => parseInt(b, 16)) ?? []);
}

// --- LNURL-pay (LUD-16) ---

export function lud16ToUrl(address: string): string {
  const addr = address.trim().toLowerCase();
  const parts = addr.split("@");
  if (parts.length !== 2 || !parts[0] || !parts[1]) {
    throw new LightningError(`malformed lightning address: ${address}`);
  }
  return `https://${parts[1]}/.well-known/lnurlp/${parts[0]}`;
}

/** Resolve a `name@domain` address to a bolt11 invoice for `sats`. */
export async function resolveInvoice(address: string, sats: number): Promise<string> {
  const res = await fetch(lud16ToUrl(address));
  if (!res.ok) throw new LightningError(`failed to resolve ${address}`);
  const params = await res.json();
  if (!params.callback || params.minSendable == null || params.maxSendable == null) {
    throw new LightningError(`invalid LNURL-pay response for ${address}`);
  }
  const msat = sats * 1000;
  if (msat < params.minSendable || msat > params.maxSendable) {
    throw new LightningError(
      `amount ${sats} sat outside payable range ` +
        `[${params.minSendable / 1000}, ${params.maxSendable / 1000}] sat`
    );
  }
  const callback = new URL(params.callback);
  callback.searchParams.set("amount", String(msat));
  const inv = await fetch(callback.toString());
  if (!inv.ok) throw new LightningError("invoice request failed");
  const data = await inv.json();
  if (!data.pr) throw new LightningError("LNURL callback returned no invoice");
  return data.pr as string;
}

// --- NWC (NIP-47) pay_invoice ---

export interface NwcConnection {
  walletPubkey: string;
  relay: string;
  secret: string; // hex private key — stays in the browser
}

export function parseNwcUri(uri: string): NwcConnection {
  const trimmed = uri.trim();
  if (!trimmed.startsWith("nostr+walletconnect://")) {
    throw new LightningError("not a nostr+walletconnect URI");
  }
  const url = new URL(trimmed);
  const walletPubkey = (url.host || url.pathname.replace(/^\/+/, "")).toLowerCase();
  const relay = url.searchParams.get("relay");
  const secret = url.searchParams.get("secret");
  if (!walletPubkey || !relay || !secret) {
    throw new LightningError("NWC URI missing wallet pubkey, relay, or secret");
  }
  return { walletPubkey, relay, secret };
}

/** Build the signed, NIP-04-encrypted kind-23194 pay_invoice request event. */
export async function buildPayRequest(conn: NwcConnection, bolt11: string): Promise<Event> {
  const sk = hexToBytes(conn.secret);
  const body = JSON.stringify({ method: "pay_invoice", params: { invoice: bolt11 } });
  const content = await nip04.encrypt(sk, conn.walletPubkey, body);
  return finalizeEvent(
    {
      kind: 23194,
      created_at: Math.floor(Date.now() / 1000),
      tags: [["p", conn.walletPubkey]],
      content,
    },
    sk
  );
}

/** Pay `bolt11` via the wallet in `uri`. Resolves to the payment preimage. */
export async function payWithNwc(uri: string, bolt11: string, timeoutMs = 30000): Promise<string> {
  const conn = parseNwcUri(uri);
  const request = await buildPayRequest(conn, bolt11);
  const sk = hexToBytes(conn.secret);
  const subId = request.id.slice(0, 16);

  return new Promise<string>((resolve, reject) => {
    const ws = new WebSocket(conn.relay);
    let settled = false;
    const finish = (fn: () => void) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try { ws.close(); } catch { /* already closing */ }
      fn();
    };
    const timer = setTimeout(
      () => finish(() => reject(new LightningError("timed out waiting for wallet response"))),
      timeoutMs
    );

    ws.onopen = () => {
      // Subscribe BEFORE publishing so a fast response can't be missed.
      ws.send(JSON.stringify(["REQ", subId, {
        kinds: [23195], authors: [conn.walletPubkey], "#e": [request.id],
      }]));
      ws.send(JSON.stringify(["EVENT", request]));
    };
    ws.onmessage = async (msg) => {
      let frame: unknown;
      try {
        frame = JSON.parse(typeof msg.data === "string" ? msg.data : "");
      } catch { return; }
      if (!Array.isArray(frame) || frame[0] !== "EVENT" || frame[1] !== subId) return;
      try {
        const plaintext = await nip04.decrypt(sk, conn.walletPubkey, frame[2].content);
        const data = JSON.parse(plaintext);
        if (data.error) {
          const m = typeof data.error === "object" ? data.error.message : String(data.error);
          finish(() => reject(new LightningError(m || "wallet returned an error")));
        } else if (data.result?.preimage) {
          finish(() => resolve(data.result.preimage as string));
        } else {
          finish(() => reject(new LightningError("wallet response had no preimage")));
        }
      } catch (e) {
        finish(() => reject(e instanceof Error ? e : new LightningError(String(e))));
      }
    };
    ws.onerror = () => finish(() => reject(new LightningError("relay connection failed")));
  });
}
