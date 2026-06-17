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


def _stub_lightning(monkeypatch):
    """Stub LNURL + NWC so no real network happens. Returns the list of paid bolt11s."""
    from app.services import lnurl_service, nwc_service
    monkeypatch.setattr(lnurl_service, "resolve_lnurl",
                        lambda addr: {"callback": "https://x/cb", "minSendable": 1000, "maxSendable": 10_000_000})
    monkeypatch.setattr(lnurl_service, "request_invoice", lambda params, amount_sats: f"lnbc{amount_sats}fake")
    paid = []
    monkeypatch.setattr(nwc_service, "pay_invoice",
                        lambda uri, bolt11: (paid.append(bolt11), "preimage_" + bolt11)[1])
    return paid


def test_payout_pays_team_and_records_results(client, auth_headers, monkeypatch):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=True)
    paid = _stub_lightning(monkeypatch)

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
    })

    assert res.status_code == 201, res.text
    body = res.json()
    assert body["status"] == "complete"
    assert len(body["items"]) == len(members)
    assert sum(i["amount_sats"] for i in body["items"]) == 210   # full pot paid, no sats lost
    assert all(i["status"] == "paid" and i["preimage"] for i in body["items"])
    assert len(paid) == len(members)


def test_payout_422_when_member_missing_address(client, auth_headers):
    # No participant has an address, so any team triggers the pre-flight 422.
    _, allocation_id, team_id, _ = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
    })
    assert res.status_code == 422
    assert "missing" in res.text.lower()


def test_payout_address_override_fills_missing(client, auth_headers, monkeypatch):
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=False)
    _stub_lightning(monkeypatch)
    # Supply an address for every member of teams[0] via the override map.
    overrides = {m["id"]: f"{m['name']}@getalby.com" for m in members}

    res = client.post(f"/api/v1/allocations/{allocation_id}/payouts", headers=auth_headers, json={
        "team_id": str(team_id), "total_sats": 210,
        "nwc": "nostr+walletconnect://abc?relay=wss://r&secret=00",
        "addresses": overrides,
    })
    assert res.status_code == 201, res.text
    assert res.json()["status"] == "complete"


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
