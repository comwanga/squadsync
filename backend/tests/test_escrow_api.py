"""API tests for escrow agent endpoints."""

import hashlib
import json
import time
from unittest.mock import patch

import pytest
from coincurve import PrivateKey


def make_signed_escrow_event(privkey: PrivateKey, identifier: str = "my-agent") -> dict:
    """Build and sign a kind-30361 escrow descriptor event."""
    pubkey_hex = privkey.public_key.format(compressed=True)[1:].hex()
    template = {
        "pubkey": pubkey_hex,
        "created_at": int(time.time()),
        "kind": 30361,
        "tags": [
            ["d", identifier],
            ["t", "escrow"],
            ["escrow_type", "custodial_escrow"],
            ["network", "lightning"],
            ["client", "squadsync-pip01"],
        ],
        "content": json.dumps(
            {
                "version": 1,
                "escrow_type": "custodial_escrow",
                "networks": ["lightning"],
                "funding_rules": {"required_confirmation": "deposit bolt11 paid"},
                "release_rules": {
                    "release_trigger": "allocation published",
                    "refund_trigger": "48h after event end",
                },
                "dispute_rules": {"policy": "3-of-5 multisig"},
                "reference_format": "squadsync-allocation-id",
                "updated_at": int(time.time()),
            },
            separators=(",", ":"),
        ),
    }
    serialized = json.dumps(
        [0, template["pubkey"], template["created_at"], template["kind"], template["tags"], template["content"]],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    template["id"] = event_id
    template["sig"] = privkey.sign_schnorr(bytes.fromhex(event_id)).hex()
    return template


@pytest.fixture
def nostr_privkey2():
    return PrivateKey()


@pytest.fixture
def auth_headers2(client, nostr_privkey2):
    """Second user for agent publishing tests."""
    pubkey = nostr_privkey2.public_key.format(compressed=True)[1:].hex()
    url = "http://testserver/auth/nostr"
    event = {
        "pubkey": pubkey,
        "created_at": int(time.time()),
        "kind": 27235,
        "tags": [["u", url], ["method", "POST"], ["nonce", "nonce2"]],
        "content": "",
    }
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    event_id = hashlib.sha256(serialized.encode()).hexdigest()
    event["id"] = event_id
    event["sig"] = nostr_privkey2.sign_schnorr(bytes.fromhex(event_id)).hex()
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_agents_returns_empty_when_no_agents(client, auth_headers):
    """GET /api/v1/escrow/agents returns empty list when no agents exist."""
    res = client.get("/api/v1/escrow/agents")
    assert res.status_code == 200
    body = res.json()
    assert "agents" in body
    assert isinstance(body["agents"], list)


def test_publish_agent_succeeds(client, auth_headers2, nostr_privkey2):
    """POST /api/v1/escrow/publish publishes a signed kind-30361 event."""
    event = make_signed_escrow_event(nostr_privkey2, identifier="publisher-test")

    with patch("app.api.v1.escrow.nostr_service.publish_event", return_value=True):
        res = client.post(
            "/api/v1/escrow/publish",
            headers=auth_headers2,
            json={"event": event},
        )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["coordinate"] is not None
    assert body["status"] == "published"


def test_publish_agent_rejects_wrong_pubkey(client, auth_headers, nostr_privkey2):
    """Publishing an event whose pubkey does not match the auth token is rejected."""
    event = make_signed_escrow_event(nostr_privkey2, identifier="spoofed")
    res = client.post(
        "/api/v1/escrow/publish",
        headers=auth_headers,
        json={"event": event},
    )
    assert res.status_code == 403


def test_publish_agent_rejects_wrong_kind(client, auth_headers2, nostr_privkey2):
    """Publishing an event with the wrong kind is rejected."""
    event = make_signed_escrow_event(nostr_privkey2)
    event["kind"] = 1
    res = client.post(
        "/api/v1/escrow/publish",
        headers=auth_headers2,
        json={"event": event},
    )
    assert res.status_code == 422


def test_list_agents_includes_published_agent(client, auth_headers2, nostr_privkey2):
    """After publishing, GET /agents includes the local agent."""
    event = make_signed_escrow_event(nostr_privkey2, identifier="listed-agent")

    with patch("app.api.v1.escrow.nostr_service.publish_event", return_value=True):
        pub_res = client.post(
            "/api/v1/escrow/publish",
            headers=auth_headers2,
            json={"event": event},
        )
    assert pub_res.status_code == 201

    with patch("app.api.v1.escrow.nostr_service.fetch_escrow_agents", return_value=[]):
        res = client.get("/api/v1/escrow/agents")
    assert res.status_code == 200
    body = res.json()
    coordinates = [a["coordinate"] for a in body["agents"]]
    assert pub_res.json()["coordinate"] in coordinates


def test_refresh_agents(client, auth_headers):
    """POST /api/v1/escrow/agents triggers a relay refresh."""
    with patch("app.api.v1.escrow.nostr_service.refresh_escrow_agents", return_value=[]):
        res = client.post("/api/v1/escrow/agents")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_escrow_payout_create_and_status_flow(client, auth_headers):
    """Full escrow payout lifecycle: create → funded → released."""
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Escrow Payout", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    r = client.post(
        f"/api/v1/events/{e['registration_slug']}/register",
        json={"name": "EscrowRecipient", "email": "er@t.com", "primary_strength": "technical", "experience_level": "advanced"},
    )
    assert r.status_code in (200, 201)

    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    teams = client.get(f"/api/v1/allocations/{a['id']}/teams", headers=auth_headers).json()

    payout_res = client.post(
        f"/api/v1/allocations/{a['id']}/payouts",
        headers=auth_headers,
        json={
            "team_id": str(teams[0]["id"]),
            "total_sats": 100,
            "escrow_coordinate": "30361:deadbeef:my-agent",
        },
    )
    assert payout_res.status_code == 201, payout_res.text
    payout = payout_res.json()
    assert payout["escrow_coordinate"] == "30361:deadbeef:my-agent"
    assert payout["escrow_status"] == "escrow_pending"
    assert len(payout["items"]) == 1

    funded_res = client.post(
        f"/api/v1/allocations/payouts/{payout['id']}/escrow-funded",
        headers=auth_headers,
    )
    assert funded_res.status_code == 200, funded_res.text
    assert funded_res.json()["escrow_status"] == "escrow_funded"

    released_res = client.post(
        f"/api/v1/allocations/payouts/{payout['id']}/escrow-released",
        headers=auth_headers,
    )
    assert released_res.status_code == 200, released_res.text
    assert released_res.json()["escrow_status"] == "escrow_released"


def test_escrow_funded_rejects_non_pending(client, auth_headers):
    """Marking funded on a direct payout is rejected."""
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Direct Payout", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    r = client.post(
        f"/api/v1/events/{e['registration_slug']}/register",
        json={"name": "DirectRecipient", "email": "dr@t.com", "primary_strength": "technical",
              "experience_level": "advanced", "lightning_address": "dr@getalby.com"},
    )
    assert r.status_code in (200, 201)
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    teams = client.get(f"/api/v1/allocations/{a['id']}/teams", headers=auth_headers).json()

    payout_res = client.post(
        f"/api/v1/allocations/{a['id']}/payouts",
        headers=auth_headers,
        json={"team_id": str(teams[0]["id"]), "total_sats": 100},
    )
    assert payout_res.status_code == 201

    funded_res = client.post(
        f"/api/v1/allocations/payouts/{payout_res.json()['id']}/escrow-funded",
        headers=auth_headers,
    )
    assert funded_res.status_code == 409
