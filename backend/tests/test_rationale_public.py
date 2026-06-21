from tests.test_payout_endpoint import _setup_team


def test_public_results_include_rationale(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": []}
        for p in payloads
    })
    event_id, allocation_id, _team_id, _members = _setup_team(client, auth_headers, all_have_addresses=False)
    client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)
    client.post(f"/api/v1/events/{event_id}/allocations/{allocation_id}/publish", headers=auth_headers)

    res = client.get(f"/api/v1/public/allocations/{allocation_id}")
    assert res.status_code == 200, res.text
    teams = res.json()["teams"]
    assert any(t.get("rationale") and t["rationale"]["title"] == "Squad" for t in teams)
