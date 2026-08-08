"""PIP-01 escrow descriptor protocol layer (kind 30361).

Port of the Pontmore PIP‑01 spec for building, parsing, and validating
escrow descriptor events on Nostr.

The browser signs events; this module builds unsigned templates and parses
received events from relays.
"""

import json
import time as _time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


PIP01_ESCROW_KIND = 30361


class EscrowType(str, Enum):
    LIGHTNING_HOLD_INVOICE = "lightning_hold_invoice"
    CUSTODIAL_ESCROW = "custodial_escrow"


class Implementation(BaseModel):
    network: str
    invoice_asset: Optional[str] = None
    invoice_currency: Optional[str] = None
    invoice_amount_rule: Optional[str] = None
    invoice_expiry_rule: Optional[str] = None
    payout_network: Optional[str] = None


class EscrowDescriptorContent(BaseModel):
    version: int = 1
    escrow_type: str
    networks: list[str] = Field(default_factory=list)
    funding_rules: dict = Field(default_factory=lambda: {"required_confirmation": ""})
    release_rules: dict = Field(default_factory=lambda: {"release_trigger": "", "refund_trigger": ""})
    dispute_rules: dict = Field(default_factory=lambda: {"policy": ""})
    reference_format: str = ""
    invoice_network: Optional[str] = None
    invoice_asset: Optional[str] = None
    invoice_currency: Optional[str] = None
    invoice_amount_rule: Optional[str] = None
    hold_expiry_rule: Optional[str] = None
    settle_authority: Optional[str] = None
    cancel_authority: Optional[str] = None
    custody_authority: Optional[str] = None
    release_authority: Optional[str] = None
    refund_authority: Optional[str] = None
    invoice_expiry_rule: Optional[str] = None
    implementations: Optional[list[Implementation]] = None
    preimage_visibility: Optional[str] = None
    payout_network: Optional[str] = None
    updated_at: int = 0


def _normalize_networks(networks: list[str] | None) -> list[str]:
    if not networks:
        return []
    normalized = [n.strip().lower() for n in networks if n.strip()]
    return list(dict.fromkeys(normalized))


def _find_tag_value(tags: list[list[str]], name: str) -> str | None:
    for tag in tags:
        if tag[0] == name and len(tag) >= 2:
            return tag[1]
    return None


def build_escrow_event_template(
    *,
    pubkey: str,
    identifier: str = "",
    escrow_type: str,
    networks: list[str],
    required_confirmation: str = "",
    release_trigger: str = "",
    refund_trigger: str = "",
    dispute_policy: str = "",
    reference_format: str = "",
    invoice_network: str = "",
    invoice_asset: str = "",
    invoice_currency: str = "",
    invoice_amount_rule: str = "",
    hold_expiry_rule: str = "",
    settle_authority: str = "",
    cancel_authority: str = "",
    custody_authority: str = "",
    release_authority: str = "",
    refund_authority: str = "",
    invoice_expiry_rule: str = "",
    preimage_visibility: str = "",
    payout_network: str = "",
) -> dict:
    """Build an unsigned kind-30361 event that the browser will sign.

    Returns a dict with pubkey, created_at, kind, tags, and content — ready
    for the client to stamp id + sig via nostr-tools finalizeEvent().
    """
    now = _time.time()
    normalized_networks = _normalize_networks(networks)
    trimmed_type = escrow_type.strip()
    trimmed_id = identifier.strip() or "escrow"

    content = {
        "version": 1,
        "escrow_type": trimmed_type,
        "networks": normalized_networks,
        "funding_rules": {"required_confirmation": required_confirmation.strip()},
        "release_rules": {
            "release_trigger": release_trigger.strip(),
            "refund_trigger": refund_trigger.strip(),
        },
        "dispute_rules": {"policy": dispute_policy.strip()},
        "reference_format": reference_format.strip(),
        "invoice_network": invoice_network.strip() or None,
        "invoice_asset": invoice_asset.strip() or None,
        "invoice_currency": invoice_currency.strip() or None,
        "invoice_amount_rule": invoice_amount_rule.strip() or None,
        "payout_network": payout_network.strip() or None,
        "updated_at": int(now),
    }

    if trimmed_type == EscrowType.LIGHTNING_HOLD_INVOICE:
        content["hold_expiry_rule"] = hold_expiry_rule.strip() or None
        content["settle_authority"] = settle_authority.strip() or None
        content["cancel_authority"] = cancel_authority.strip() or None
        content["preimage_visibility"] = preimage_visibility.strip() or None

    if trimmed_type == EscrowType.CUSTODIAL_ESCROW:
        content["custody_authority"] = custody_authority.strip() or None
        content["release_authority"] = release_authority.strip() or None
        content["refund_authority"] = refund_authority.strip() or None
        content["invoice_expiry_rule"] = invoice_expiry_rule.strip() or None
        content["implementations"] = [
            {
                "network": invoice_network.strip(),
                "invoice_asset": invoice_asset.strip() or None,
                "invoice_currency": invoice_currency.strip() or None,
                "invoice_amount_rule": invoice_amount_rule.strip() or None,
                "invoice_expiry_rule": invoice_expiry_rule.strip() or None,
                "payout_network": payout_network.strip() or None,
            }
        ]

    tags = [
        ["d", trimmed_id],
        ["t", "escrow"],
        ["escrow_type", trimmed_type],
        *[[network_tag, n] for network_tag, n in zip(["network"] * len(normalized_networks), normalized_networks)],
        ["client", "squadsync-pip01"],
    ]

    return {
        "pubkey": pubkey,
        "created_at": int(now),
        "kind": PIP01_ESCROW_KIND,
        "tags": [list(t) for t in tags],
        "content": json.dumps(content, separators=(",", ":")),
    }


def parse_escrow_event(event: dict) -> EscrowDescriptorContent:
    """Parse a raw Nostr kind-30361 event into a typed descriptor.

    Returns an EscrowDescriptorContent on success. If the content field is
    malformed JSON, the model will have networks populated from tags instead.
    """
    tags = event.get("tags", [])
    identifier = _find_tag_value(tags, "d") or "escrow"
    escrow_type = _find_tag_value(tags, "escrow_type") or ""
    networks = _normalize_networks(
        [t[1] for t in tags if t[0] == "network" and len(t) >= 2]
    )

    try:
        raw = json.loads(event.get("content", "{}"))
        if not isinstance(raw, dict):
            raise ValueError("content is not a JSON object")
        return EscrowDescriptorContent(
            version=raw.get("version", 1),
            escrow_type=raw.get("escrow_type", escrow_type),
            networks=_normalize_networks(raw.get("networks")) or networks,
            funding_rules=raw.get("funding_rules", {"required_confirmation": ""}),
            release_rules=raw.get("release_rules", {"release_trigger": "", "refund_trigger": ""}),
            dispute_rules=raw.get("dispute_rules", {"policy": ""}),
            reference_format=raw.get("reference_format", ""),
            invoice_network=raw.get("invoice_network"),
            invoice_asset=raw.get("invoice_asset"),
            invoice_currency=raw.get("invoice_currency"),
            invoice_amount_rule=raw.get("invoice_amount_rule"),
            hold_expiry_rule=raw.get("hold_expiry_rule"),
            settle_authority=raw.get("settle_authority"),
            cancel_authority=raw.get("cancel_authority"),
            custody_authority=raw.get("custody_authority"),
            release_authority=raw.get("release_authority"),
            refund_authority=raw.get("refund_authority"),
            invoice_expiry_rule=raw.get("invoice_expiry_rule"),
            implementations=(
                [Implementation(**i) for i in raw.get("implementations", [])]
                if isinstance(raw.get("implementations"), list)
                else None
            ),
            preimage_visibility=raw.get("preimage_visibility"),
            payout_network=raw.get("payout_network"),
            updated_at=raw.get("updated_at", 0),
        )
    except (json.JSONDecodeError, ValueError):
        return EscrowDescriptorContent(
            version=1,
            escrow_type=escrow_type,
            networks=networks,
            updated_at=event.get("created_at", 0),
        )


def escrow_coordinate_from_event(event: dict) -> str:
    """Return a kind:pubkey:identifier coordinate from a Nostr event dict."""
    kind = event.get("kind", PIP01_ESCROW_KIND)
    pubkey = event.get("pubkey", "")
    identifier = _find_tag_value(event.get("tags", []), "d") or "escrow"
    return f"{kind}:{pubkey}:{identifier}"


def escrow_coordinate(pubkey: str, identifier: str = "escrow") -> str:
    """Return a kind:pubkey:identifier coordinate for a given pubkey + identifier."""
    return f"{PIP01_ESCROW_KIND}:{pubkey}:{identifier.strip() or 'escrow'}"
