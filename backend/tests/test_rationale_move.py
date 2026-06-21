from tests.test_payout_endpoint import _setup_team


def test_move_clears_rationale(client, auth_headers, monkeypatch):
    from app.core.config import settings
    from app.services import rationale_service
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "k", raising=False)
    monkeypatch.setattr(rationale_service, "_classify", lambda event, payloads: {
        p["id"]: {"title": "Squad", "summary": "Balanced.", "strengths": ["a"], "gaps": []}
        for p in payloads
    })
    _, allocation_id, team_id, members = _setup_team(client, auth_headers, all_have_addresses=False)
    client.post(f"/api/v1/allocations/{allocation_id}/rationale", headers=auth_headers)

    teams = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    target = next(t["id"] for t in teams if t["id"] != team_id)
    mover = members[0]["id"]
    client.patch(f"/api/v1/allocations/{allocation_id}/members/{mover}",
                 headers=auth_headers, json={"team_id": target})

    teams_after = client.get(f"/api/v1/allocations/{allocation_id}/teams", headers=auth_headers).json()
    assert all(t["rationale"] is None for t in teams_after)
