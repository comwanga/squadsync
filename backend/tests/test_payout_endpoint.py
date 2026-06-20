import hashlib

from tests.lightning_helpers import invoice_for_preimage


def _setup_team(client, auth_headers, all_have_addresses):
    """Register 4 participants, allocate into 2 teams, return the first team.

    Returns (event_id, allocation_id, team_id, members) where `members` is the
    list of member dicts (each has 'id' and 'name') on teams[0].
    """
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "BTC++ Payout", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    strengths = ["technical", "design", "planning", "coordination"]
    for i in range(4):
        body = {"name": f"P{i}", "email": f"p{i}@t.com",
                "primary_strength": strengths[i], "experience_level": "intermediate"}
        if all_have_addresses:
            body["lightning_address"] = f"p{i}@getalby.com"
        r = client.post(f"/api/v1/events/{e['registration_slug']}/register", json=body)
        assert r.status_code in (200, 201), r.text
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    teams = client.get(f"/api/v1/allocations/{a['id']}/teams", headers=auth_headers).json()
    assert teams and teams[0]["members"], "expected a non-empty first team"
    return e["id"], a["id"], teams[0]["id"], teams[0]["members"]


def _pay_all(client, headers, payout):
    """Report a valid (verifiable) preimage for every item, simulating the browser."""
    final = payout
    for item in payout["items"]:
        preimage = hashlib.sha256(item["id"].encode()).hexdigest()
        res = client.post(
            f"/api/v1/allocations/payouts/{payout['id']}/items/{item['id']}/result",
            headers=headers, json={"bolt11": invoice_for_preimage(preimage), "preimage": preimage},
        )
        assert res.status_code == 200, res.text
        final = res.json()
    return final


def test_create_payout_returns_pending_without_a_credential(client, auth_headers):
    # The server never receives a spend credential — it returns pending items.
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending"
    assert sum(i["amount_sats"] for i in body["items"]) == 210
    assert len(body["items"]) == len(members)


def test_payout_422_when_member_missing_address(client, auth_headers):
    # No participant has an address, so any team triggers the pre-flight 422.
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
    })
    assert res.status_code == 422
    assert "missing" in res.text.lower()


def test_payout_address_override_fills_missing(client, auth_headers):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=False)
    overrides = {m["id"]: f"{m['name']}@getalby.com" for m in members}

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210, "addresses": overrides,
    })
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "pending"
    # Every item carries the organizer-supplied address.
    assert {i["lightning_address"] for i in body["items"]} == set(overrides.values())


def test_payout_idempotent_second_call_rejected(client, auth_headers):
    # A team must never get a second payout (double-click / client retry).
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)
    body = {"team_id": str(team_id), "total_sats": 210}

    first = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json=body)
    assert first.status_code == 201, first.text
    second = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json=body)
    assert second.status_code == 409, second.text


def test_payout_rejects_amount_over_ceiling(client, auth_headers, monkeypatch):
    from app.core.config import settings as app_settings
    monkeypatch.setattr(app_settings, "PAYOUT_MAX_SATS", 500, raising=False)
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=True)

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 501,
    })
    assert res.status_code == 422, res.text
    assert "exceeds" in res.text.lower()


def test_public_results_include_payout_summary(client, auth_headers):
    event_id, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    payout = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers,
                         json={"team_id": str(team_id), "total_sats": 210}).json()
    final = _pay_all(client, auth_headers, payout)
    assert final["status"] == "complete"
    client.post(f"/api/v1/events/{event_id}/allocations/{allocation_id}/publish", headers=auth_headers)

    res = client.get(f"/api/v1/public/allocations/{allocation_id}")
    assert res.status_code == 200, res.text
    summary = res.json()["payouts"]
    assert summary[0]["total_sats"] == 210
    assert summary[0]["paid_count"] == len(members)
    assert summary[0]["member_count"] == len(members)
    # never leak the credential or invoice/preimage secrets
    for leaked in ("nwc", "preimage", "bolt11", "lightning_address"):
        assert leaked not in res.text.lower()


def test_payout_models_importable_and_persist(db):
    import uuid
    from app.models.payout import Payout, PayoutItem

    payout = Payout(event_id=uuid.uuid4(), allocation_id=uuid.uuid4(),
                    team_label="Team Satoshi", total_sats=210, status="pending")
    db.add(payout)
    db.flush()
    item = PayoutItem(payout_id=payout.id, participant_id=uuid.uuid4(),
                      lightning_address="ada@getalby.com", amount_sats=105, status="pending")
    db.add(item)
    db.commit()
    assert payout.id is not None and item.payout_id == payout.id
