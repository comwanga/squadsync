import { describe, it, expect, vi, afterEach } from "vitest";
import { lud16ToUrl, parseNwcUri, resolveInvoice, LightningError } from "@/lib/lightning";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("lud16ToUrl", () => {
  it("builds the .well-known LNURL-pay URL", () => {
    expect(lud16ToUrl("Ada@Getalby.com")).toBe("https://getalby.com/.well-known/lnurlp/ada");
  });

  it("rejects a malformed address", () => {
    expect(() => lud16ToUrl("not-an-address")).toThrow(LightningError);
  });
});

describe("parseNwcUri", () => {
  it("extracts wallet pubkey, relay, and secret", () => {
    const conn = parseNwcUri("nostr+walletconnect://ABCD?relay=wss://relay.example&secret=00ff");
    expect(conn.walletPubkey).toBe("abcd");
    expect(conn.relay).toBe("wss://relay.example");
    expect(conn.secret).toBe("00ff");
  });

  it("rejects a non-NWC URI", () => {
    expect(() => parseNwcUri("https://nope")).toThrow(LightningError);
  });

  it("rejects an NWC URI missing the secret", () => {
    expect(() => parseNwcUri("nostr+walletconnect://abcd?relay=wss://r")).toThrow(LightningError);
  });
});

describe("resolveInvoice", () => {
  it("requests an invoice for the amount in msat and returns the bolt11", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ callback: "https://getalby.com/cb", minSendable: 1000, maxSendable: 1_000_000_000 }),
      })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ pr: "lnbc105fake" }) });
    vi.stubGlobal("fetch", fetchMock);

    const invoice = await resolveInvoice("ada@getalby.com", 105);

    expect(invoice).toBe("lnbc105fake");
    expect(fetchMock).toHaveBeenCalledTimes(2);
    // amount is sent in millisats on the callback
    expect(String(fetchMock.mock.calls[1][0])).toContain("amount=105000");
  });

  it("rejects an amount outside the payable range before requesting an invoice", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ callback: "https://x/cb", minSendable: 1_000_000, maxSendable: 2_000_000 }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(resolveInvoice("ada@getalby.com", 1)).rejects.toThrow(LightningError);
    expect(fetchMock).toHaveBeenCalledTimes(1); // never reached the callback
  });
});
