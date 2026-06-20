from tests.test_payout_endpoint import _setup_team


def test_rationale_requires_api_key_returns_400(client, auth_headers, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", None, raising=False)
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    assert res.status_code == 400
    assert "anthropic" in res.text.lower()


def test_rationale_generates_and_persists(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": ["b"]}
        for p in payloads
    })
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    assert res.status_code == 200, res.text
    body = res.json()
    assert all(r["title"] == "Squad" for r in body.values())
    teams = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    assert all(t["rationale"]["summary"] == "Balanced." for t in teams)


def test_rationale_requires_organizer(client, auth_headers, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    _, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    from tests.conftest import make_nostr_event
    from coincurve import PrivateKey
    other = PrivateKey()
    pubkey = other.public_key.format(compressed=True)[1:].hex()
    token = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(other)}).json()["access_token"]
    res = client.post(f"/api/v1/allocations/{allocation_id}/rationale",
                      headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in (401, 403, 404)
