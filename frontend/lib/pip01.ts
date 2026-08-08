import type { Event as NostrEvent } from "nostr-tools";

export const PIP01_ESCROW_KIND = 30361;

export enum EscrowType {
  LightningHoldInvoice = "lightning_hold_invoice",
  CustodialEscrow = "custodial_escrow",
}

export interface EscrowDescriptorContent {
  version: number;
  escrow_type: string;
  networks: string[];
  funding_rules: { required_confirmation: string };
  release_rules: { release_trigger: string; refund_trigger: string };
  dispute_rules: { policy: string };
  reference_format: string;
  invoice_network?: string | null;
  invoice_asset?: string | null;
  invoice_currency?: string | null;
  invoice_amount_rule?: string | null;
  hold_expiry_rule?: string | null;
  settle_authority?: string | null;
  cancel_authority?: string | null;
  custody_authority?: string | null;
  release_authority?: string | null;
  refund_authority?: string | null;
  invoice_expiry_rule?: string | null;
  implementations?: Array<{
    network: string;
    invoice_asset?: string | null;
    invoice_currency?: string | null;
    invoice_amount_rule?: string | null;
    invoice_expiry_rule?: string | null;
    payout_network?: string | null;
  }> | null;
  preimage_visibility?: string | null;
  payout_network?: string | null;
  updated_at: number;
}

function normalizeNetworks(networks: string[] | undefined): string[] {
  const normalized =
    networks?.map((n) => n.trim().toLowerCase()).filter(Boolean) ?? [];
  return [...new Set(normalized)];
}

function findTagValue(
  tags: string[][],
  name: string,
): string | undefined {
  return tags.find((tag) => tag[0] === name)?.[1];
}

interface BuildEscrowTemplateParams {
  pubkey: string;
  identifier?: string;
  escrowType: string;
  networks: string[];
  requiredConfirmation?: string;
  releaseTrigger?: string;
  refundTrigger?: string;
  disputePolicy?: string;
  referenceFormat?: string;
  invoiceNetwork?: string;
  invoiceAsset?: string;
  invoiceCurrency?: string;
  invoiceAmountRule?: string;
  holdExpiryRule?: string;
  settleAuthority?: string;
  cancelAuthority?: string;
  custodyAuthority?: string;
  releaseAuthority?: string;
  refundAuthority?: string;
  invoiceExpiryRule?: string;
  preimageVisibility?: string;
  payoutNetwork?: string;
}

export function buildEscrowEventTemplate(
  params: BuildEscrowTemplateParams,
): Pick<NostrEvent, "pubkey" | "created_at" | "kind" | "tags" | "content"> {
  const now = new Date();
  const normalizedNetworks = normalizeNetworks(params.networks);
  const trimmedType = params.escrowType.trim();

  const content: EscrowDescriptorContent = {
    version: 1,
    escrow_type: trimmedType,
    networks: normalizedNetworks,
    funding_rules: {
      required_confirmation: (params.requiredConfirmation ?? "").trim(),
    },
    release_rules: {
      release_trigger: (params.releaseTrigger ?? "").trim(),
      refund_trigger: (params.refundTrigger ?? "").trim(),
    },
    dispute_rules: {
      policy: (params.disputePolicy ?? "").trim(),
    },
    reference_format: (params.referenceFormat ?? "").trim(),
    invoice_network: params.invoiceNetwork?.trim() || null,
    invoice_asset: params.invoiceAsset?.trim() || null,
    invoice_currency: params.invoiceCurrency?.trim() || null,
    invoice_amount_rule: params.invoiceAmountRule?.trim() || null,
    payout_network: params.payoutNetwork?.trim() || null,
    updated_at: Math.floor(now.getTime() / 1000),
  };

  if (trimmedType === EscrowType.LightningHoldInvoice) {
    content.hold_expiry_rule = params.holdExpiryRule?.trim() || null;
    content.settle_authority = params.settleAuthority?.trim() || null;
    content.cancel_authority = params.cancelAuthority?.trim() || null;
    content.preimage_visibility = params.preimageVisibility?.trim() || null;
  }

  if (trimmedType === EscrowType.CustodialEscrow) {
    content.custody_authority = params.custodyAuthority?.trim() || null;
    content.release_authority = params.releaseAuthority?.trim() || null;
    content.refund_authority = params.refundAuthority?.trim() || null;
    content.invoice_expiry_rule =
      params.invoiceExpiryRule?.trim() || null;
    content.implementations = [
      {
        network: (params.invoiceNetwork ?? "").trim(),
        invoice_asset: params.invoiceAsset?.trim() || null,
        invoice_currency: params.invoiceCurrency?.trim() || null,
        invoice_amount_rule: params.invoiceAmountRule?.trim() || null,
        invoice_expiry_rule: params.invoiceExpiryRule?.trim() || null,
        payout_network: params.payoutNetwork?.trim() || null,
      },
    ];
  }

  const identifier = params.identifier?.trim() || "escrow";

  return {
    pubkey: params.pubkey,
    created_at: Math.floor(now.getTime() / 1000),
    kind: PIP01_ESCROW_KIND,
    tags: [
      ["d", identifier],
      ["t", "escrow"],
      ["escrow_type", trimmedType],
      ...normalizedNetworks.map((network) => ["network", network]),
      ["client", "squadsync-pip01"],
    ],
    content: JSON.stringify(content),
  };
}

export function parseEscrowEvent(
  event: NostrEvent,
): EscrowDescriptorContent | null {
  try {
    return JSON.parse(event.content) as EscrowDescriptorContent;
  } catch {
    return null;
  }
}

export function escrowCoordinate(
  pubkey: string,
  identifier = "escrow",
): string {
  return `${PIP01_ESCROW_KIND}:${pubkey}:${identifier.trim() || "escrow"}`;
}

export function escrowCoordinateFromEvent(event: NostrEvent): string {
  const identifier = findTagValue(event.tags, "d") || "escrow";
  return `${event.kind}:${event.pubkey}:${identifier}`;
}
