"""Unit tests for PIP-01 escrow descriptor protocol (build, parse, coordinate)."""

import json

from app.services.pip01 import (
    PIP01_ESCROW_KIND,
    EscrowType,
    EscrowDescriptorContent,
    build_escrow_event_template,
    parse_escrow_event,
    escrow_coordinate,
    escrow_coordinate_from_event,
    _normalize_networks,
    _find_tag_value,
)


def test_build_template_returns_minimal_unsigned_event():
    template = build_escrow_event_template(
        pubkey="abc123",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["lightning"],
    )
    assert template["pubkey"] == "abc123"
    assert template["kind"] == PIP01_ESCROW_KIND
    assert "id" not in template
    assert "sig" not in template
    assert len(template["tags"]) > 0

    d_tag = _find_tag_value(template["tags"], "d")
    assert d_tag == "escrow"

    content = json.loads(template["content"])
    assert content["escrow_type"] == EscrowType.CUSTODIAL_ESCROW
    assert content["networks"] == ["lightning"]


def test_build_template_uses_custom_identifier():
    template = build_escrow_event_template(
        pubkey="abc123",
        identifier="my-agent",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["lightning"],
    )
    assert _find_tag_value(template["tags"], "d") == "my-agent"


def test_build_template_sets_client_tag():
    template = build_escrow_event_template(
        pubkey="abc123",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["lightning"],
    )
    assert _find_tag_value(template["tags"], "client") == "squadsync-pip01"


def test_build_template_normalizes_networks():
    template = build_escrow_event_template(
        pubkey="abc123",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["  Lightning  ", "LIGHTNING", "lightning"],
    )
    content = json.loads(template["content"])
    assert content["networks"] == ["lightning"]

    network_tags = [t[1] for t in template["tags"] if t[0] == "network"]
    assert network_tags == ["lightning"]


def test_build_template_custodial_escrow_has_implementations():
    template = build_escrow_event_template(
        pubkey="abc123",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["lightning"],
        custody_authority="me",
        release_authority="event_organizer",
        refund_authority="me",
        invoice_network="lightning",
        invoice_currency="EUR",
    )
    content = json.loads(template["content"])
    assert content["custody_authority"] == "me"
    assert content["release_authority"] == "event_organizer"
    assert content["refund_authority"] == "me"
    assert len(content["implementations"]) == 1
    assert content["implementations"][0]["invoice_currency"] == "EUR"


def test_build_template_hold_invoice_has_extra_fields():
    template = build_escrow_event_template(
        pubkey="abc123",
        escrow_type=EscrowType.LIGHTNING_HOLD_INVOICE,
        networks=["lightning"],
        hold_expiry_rule="24h",
        settle_authority="receiver",
        cancel_authority="payer",
        preimage_visibility="sender",
    )
    content = json.loads(template["content"])
    assert content["hold_expiry_rule"] == "24h"
    assert content["settle_authority"] == "receiver"
    assert content["cancel_authority"] == "payer"
    assert content["preimage_visibility"] == "sender"
    assert "custody_authority" not in content


def test_parse_escrow_event_round_trips():
    template = build_escrow_event_template(
        pubkey="abc123",
        identifier="my-escrow",
        escrow_type=EscrowType.CUSTODIAL_ESCROW,
        networks=["lightning", "bitcoin"],
        release_trigger="allocation published",
        refund_trigger="48h after event end",
        dispute_policy="3-of-5 multisig",
        reference_format="squadsync-allocation-id",
    )
    parsed = parse_escrow_event(template)
    assert parsed.escrow_type == EscrowType.CUSTODIAL_ESCROW
    assert parsed.networks == ["lightning", "bitcoin"]
    assert parsed.release_rules["release_trigger"] == "allocation published"
    assert parsed.release_rules["refund_trigger"] == "48h after event end"
    assert parsed.dispute_rules["policy"] == "3-of-5 multisig"
    assert parsed.reference_format == "squadsync-allocation-id"


def test_parse_escrow_event_handles_malformed_content():
    event = {
        "id": "e1",
        "pubkey": "abc",
        "created_at": 1234567,
        "kind": PIP01_ESCROW_KIND,
        "tags": [
            ["d", "broken-escrow"],
            ["escrow_type", "custodial_escrow"],
            ["network", "lightning"],
        ],
        "content": "not valid json {{{",
        "sig": "ff",
    }
    parsed = parse_escrow_event(event)
    assert parsed.escrow_type == "custodial_escrow"
    assert parsed.networks == ["lightning"]


def test_parse_escrow_event_falls_back_to_tags_when_no_content():
    event = {
        "id": "e2",
        "pubkey": "abc",
        "created_at": 1,
        "kind": PIP01_ESCROW_KIND,
        "tags": [
            ["d", "fallback"],
            ["escrow_type", "lightning_hold_invoice"],
            ["network", "bitcoin"],
        ],
        "content": "{}",
        "sig": "00",
    }
    parsed = parse_escrow_event(event)
    assert parsed.escrow_type == "lightning_hold_invoice"
    assert parsed.networks == ["bitcoin"]


def test_escrow_coordinate():
    coord = escrow_coordinate("deadbeef", "my-agent")
    assert coord == "30361:deadbeef:my-agent"


def test_escrow_coordinate_defaults_identifier():
    coord = escrow_coordinate("deadbeef")
    assert coord == "30361:deadbeef:escrow"


def test_escrow_coordinate_from_event():
    event = {
        "kind": PIP01_ESCROW_KIND,
        "pubkey": "abc",
        "tags": [["d", "test-agent"]],
    }
    coord = escrow_coordinate_from_event(event)
    assert coord == "30361:abc:test-agent"


def test_normalize_networks_deduplicates_and_lowercases():
    assert _normalize_networks(["Bitcoin", "BITCOIN", "  bitcoin  "]) == ["bitcoin"]
    assert _normalize_networks([]) == []
    assert _normalize_networks(None) == []
    assert _normalize_networks(["  "]) == []


def test_find_tag_value():
    tags = [["d", "hello"], ["network", "lightning"]]
    assert _find_tag_value(tags, "d") == "hello"
    assert _find_tag_value(tags, "nonexistent") is None
    assert _find_tag_value([], "d") is None
    assert _find_tag_value([["d"]], "d") is None
