import { describe, it, expect } from "vitest";
import {
  PIP01_ESCROW_KIND,
  EscrowType,
  buildEscrowEventTemplate,
  parseEscrowEvent,
  escrowCoordinate,
  escrowCoordinateFromEvent,
} from "@/lib/pip01";

describe("buildEscrowEventTemplate", () => {
  it("returns an unsigned event with correct kind and tags", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc123",
      escrowType: EscrowType.CustodialEscrow,
      networks: ["lightning"],
    });

    expect(template.pubkey).toBe("abc123");
    expect(template.kind).toBe(PIP01_ESCROW_KIND);
    expect("id" in template).toBe(false);
    expect("sig" in template).toBe(false);
    expect(template.tags).toEqual(
      expect.arrayContaining([
        ["d", "escrow"],
        ["t", "escrow"],
        ["escrow_type", "custodial_escrow"],
        ["network", "lightning"],
        ["client", "squadsync-pip01"],
      ]),
    );

    const content = JSON.parse(template.content);
    expect(content.escrow_type).toBe("custodial_escrow");
    expect(content.networks).toEqual(["lightning"]);
  });

  it("uses custom identifier", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc",
      identifier: "my-agent",
      escrowType: EscrowType.CustodialEscrow,
      networks: ["lightning"],
    });
    const dTag = template.tags.find((t) => t[0] === "d")?.[1];
    expect(dTag).toBe("my-agent");
  });

  it("normalizes networks (dedup + lowercase)", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc",
      escrowType: EscrowType.CustodialEscrow,
      networks: ["  Lightning  ", "LIGHTNING", "lightning"],
    });
    const content = JSON.parse(template.content);
    expect(content.networks).toEqual(["lightning"]);
  });

  it("includes custodial escrow extra fields", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc",
      escrowType: EscrowType.CustodialEscrow,
      networks: ["lightning"],
      custodyAuthority: "me",
      releaseAuthority: "organizer",
      refundAuthority: "me",
      invoiceCurrency: "EUR",
    });
    const content = JSON.parse(template.content);
    expect(content.custody_authority).toBe("me");
    expect(content.release_authority).toBe("organizer");
    expect(content.refund_authority).toBe("me");
    expect(content.implementations).toHaveLength(1);
    expect(content.implementations[0].invoice_currency).toBe("EUR");
  });

  it("includes hold invoice extra fields", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc",
      escrowType: EscrowType.LightningHoldInvoice,
      networks: ["lightning"],
      holdExpiryRule: "24h",
      settleAuthority: "receiver",
      cancelAuthority: "payer",
      preimageVisibility: "sender",
    });
    const content = JSON.parse(template.content);
    expect(content.hold_expiry_rule).toBe("24h");
    expect(content.settle_authority).toBe("receiver");
    expect(content.cancel_authority).toBe("payer");
    expect(content.preimage_visibility).toBe("sender");
    expect(content.custody_authority).toBeUndefined();
  });

  it("round-trips through parseEscrowEvent", () => {
    const template = buildEscrowEventTemplate({
      pubkey: "abc",
      identifier: "my-escrow",
      escrowType: EscrowType.CustodialEscrow,
      networks: ["lightning", "bitcoin"],
      releaseTrigger: "allocation published",
      refundTrigger: "48h after event end",
      disputePolicy: "3-of-5 multisig",
      referenceFormat: "squadsync-allocation-id",
    });

    const signedEvent = {
      ...template,
      id: "event1",
      sig: "signature1",
    };

    const parsed = parseEscrowEvent(signedEvent);
    expect(parsed).not.toBeNull();
    expect(parsed!.escrow_type).toBe("custodial_escrow");
    expect(parsed!.release_rules.release_trigger).toBe(
      "allocation published",
    );
    expect(parsed!.dispute_rules.policy).toBe("3-of-5 multisig");
  });

  it("parseEscrowEvent returns null for malformed content", () => {
    const parsed = parseEscrowEvent({
      id: "e1",
      pubkey: "abc",
      created_at: 1,
      kind: PIP01_ESCROW_KIND,
      tags: [],
      content: "not json {{{",
      sig: "ff",
    });
    expect(parsed).toBeNull();
  });
});

describe("escrowCoordinate", () => {
  it("formats kind:pubkey:identifier", () => {
    expect(escrowCoordinate("deadbeef", "my-agent")).toBe(
      "30361:deadbeef:my-agent",
    );
  });

  it("defaults identifier to escrow", () => {
    expect(escrowCoordinate("deadbeef")).toBe("30361:deadbeef:escrow");
  });
});

describe("escrowCoordinateFromEvent", () => {
  it("extracts coordinate from a Nostr event", () => {
    const coord = escrowCoordinateFromEvent({
      id: "e1",
      pubkey: "abc",
      created_at: 1,
      kind: PIP01_ESCROW_KIND,
      tags: [["d", "test-agent"]],
      content: "{}",
      sig: "ff",
    });
    expect(coord).toBe("30361:abc:test-agent");
  });
});
