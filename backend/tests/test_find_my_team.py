def _published(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "FMT", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    return e, a


def test_find_team_returns_my_team(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "p0@t.com"})
    assert res.status_code == 200
    team = res.json()
    assert "name" in team
    assert any(m["name"] == "P0" for m in team["members"])
    assert all("email" not in m for m in team["members"])


def test_find_team_case_insensitive(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "P0@T.COM"})
    assert res.status_code == 200


def test_find_team_unknown_email_404(client, auth_headers):
    _, a = _published(client, auth_headers)
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "nobody@t.com"})
    assert res.status_code == 404


def test_find_team_unpublished_404(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "D", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"d{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    res = client.post(f"/api/v1/public/allocations/{a['id']}/find-team", json={"email": "d0@t.com"})
    assert res.status_code == 404
