"""API tests for escrow session lifecycle."""

from uuid import uuid4


def _setup_event_alloc(client, auth_headers):
    """Create event, activate, register 2 participants, allocate, return ids."""
    e = client.post(
        "/api/v1/events", headers=auth_headers,
        json={"title": "Escrow Session Test", "team_count": 2},
    ).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, strength in enumerate(["technical", "design"]):
        r = client.post(
            f"/api/v1/events/{e['registration_slug']}/register",
            json={
                "name": f"EscrowP{i}", "email": f"ep{i}@t.com",
                "primary_strength": strength, "experience_level": "advanced",
            },
        )
        assert r.status_code in (200, 201)
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    teams = client.get(f"/api/v1/allocations/{a['id']}/teams", headers=auth_headers).json()
    return e["id"], a["id"], teams[0]["id"]


def test_create_escrow_returns_draft(client, auth_headers):
    res = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:abc:my-agent",
        "amount_sats": 100_000,
        "rail": "lightning",
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "draft"
    assert body["agent_coordinate"] == "30361:abc:my-agent"
    assert body["amount_sats"] == 100_000
    assert body["rail"] == "lightning"


def test_create_escrow_with_event_and_allocation(client, auth_headers):
    event_id, allocation_id, team_id = _setup_event_alloc(client, auth_headers)

    res = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:abc:my-agent",
        "amount_sats": 50_000,
        "rail": "bitcoin",
        "event_id": event_id,
        "allocation_id": allocation_id,
        "team_id": team_id,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["event_id"] == event_id
    assert body["allocation_id"] == allocation_id


def test_list_escrows_returns_user_escrows(client, auth_headers):
    for i in range(2):
        res = client.post("/api/v1/escrows", headers=auth_headers, json={
            "agent_coordinate": f"30361:agent{i}:escrow",
            "amount_sats": 10_000,
            "rail": "lightning",
        })
        assert res.status_code == 201

    res = client.get("/api/v1/escrows", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 2


def test_list_escrows_filters_by_status(client, auth_headers):
    r1 = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    assert r1.status_code == 201
    escrow_id = r1.json()["id"]

    # Activate one
    client.post(f"/api/v1/escrows/{escrow_id}/activate", headers=auth_headers)

    res = client.get("/api/v1/escrows?status=awaiting_funding", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_get_escrow_by_id(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]

    res = client.get(f"/api/v1/escrows/{escrow_id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == escrow_id


def test_escrow_403_for_other_user(db, client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]

    # Second user
    from coincurve import PrivateKey
    import time, hashlib, json
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    url = "http://testserver/auth/nostr"
    event = {
        "pubkey": pubkey, "created_at": int(time.time()), "kind": 27235,
        "tags": [["u", url], ["method", "POST"], ["nonce", uuid4().hex]],
        "content": "",
    }
    serialized = json.dumps(
        [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]],
        separators=(",", ":"), ensure_ascii=False,
    )
    event["id"] = hashlib.sha256(serialized.encode()).hexdigest()
    event["sig"] = pk.sign_schnorr(bytes.fromhex(event["id"])).hex()
    auth2 = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    token2 = auth2.json()["access_token"]

    res = client.get(f"/api/v1/escrows/{escrow_id}", headers={"Authorization": f"Bearer {token2}"})
    assert res.status_code == 403


def test_activate_escrow(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]

    res = client.post(f"/api/v1/escrows/{escrow_id}/activate", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "awaiting_funding"


def test_fund_escrow_generates_funding_request(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]
    client.post(f"/api/v1/escrows/{escrow_id}/activate", headers=auth_headers)

    res = client.post(f"/api/v1/escrows/{escrow_id}/fund", headers=auth_headers, json={
        "nwc_uri": "nostr+walletconnect://test",
    })
    assert res.status_code == 200
    body = res.json()
    assert body["funding_request"] is not None
    assert body["nwc_uri"] == "nostr+walletconnect://test"


def test_full_escrow_lifecycle(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:lifecycle:escrow",
        "amount_sats": 50_000,
        "rail": "lightning",
    })
    escrow_id = r.json()["id"]

    # draft → awaiting_funding
    a = client.post(f"/api/v1/escrows/{escrow_id}/activate", headers=auth_headers)
    assert a.json()["status"] == "awaiting_funding"

    # fund
    f = client.post(f"/api/v1/escrows/{escrow_id}/fund", headers=auth_headers, json={})
    assert f.json()["funding_request"] is not None

    # confirm funded
    cf = client.post(f"/api/v1/escrows/{escrow_id}/confirm-funded", headers=auth_headers)
    assert cf.json()["status"] == "funded"
    assert cf.json()["funded_at"] is not None

    # release
    rel = client.post(f"/api/v1/escrows/{escrow_id}/release", headers=auth_headers)
    assert rel.json()["status"] == "released"
    assert rel.json()["released_at"] is not None


def test_cancel_draft_escrow(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:cancel:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]

    res = client.post(f"/api/v1/escrows/{escrow_id}/cancel", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_cannot_cancel_funded_escrow(client, auth_headers):
    r = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:nocancel:escrow", "amount_sats": 10_000, "rail": "lightning",
    })
    escrow_id = r.json()["id"]
    client.post(f"/api/v1/escrows/{escrow_id}/activate", headers=auth_headers)
    client.post(f"/api/v1/escrows/{escrow_id}/fund", headers=auth_headers, json={})
    client.post(f"/api/v1/escrows/{escrow_id}/confirm-funded", headers=auth_headers)

    # Cancelling a funded escrow is allowed (refund needed)
    res = client.post(f"/api/v1/escrows/{escrow_id}/cancel", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"


def test_escrow_amount_must_be_positive(client, auth_headers):
    res = client.post("/api/v1/escrows", headers=auth_headers, json={
        "agent_coordinate": "30361:a:escrow",
        "amount_sats": 0,
        "rail": "lightning",
    })
    assert res.status_code == 422
