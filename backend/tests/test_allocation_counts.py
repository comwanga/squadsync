def _make_active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Counts", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def test_allocation_reports_auto_normalized_count(client, auth_headers):
    e = _make_active_event(client, auth_headers)
    slug = e["registration_slug"]
    client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Carol", "email": "carol@t.com",
        "primary_strength": "other", "strength_other": "Agronomist", "experience_level": "advanced"})
    for i, s in enumerate(["technical", "design", "planning"]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    res = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    assert res.status_code == 200
    body = res.json()
    assert body["auto_normalized"] == 1
    assert body["ai_normalized"] == 0
