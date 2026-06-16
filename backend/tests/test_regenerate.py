def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "RG", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def _register(client, slug, n):
    for i, s in enumerate(["technical", "design", "planning", "coordination"][:n]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})


def test_regenerate_replaces_draft(client, auth_headers):
    e = _active_event(client, auth_headers); _register(client, e["registration_slug"], 4)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    allocs = client.get(f"/api/v1/events/{e['id']}/allocations", headers=auth_headers).json()
    assert len([a for a in allocs if a["status"] == "draft"]) == 1


def test_regenerate_preserves_published(client, auth_headers):
    e = _active_event(client, auth_headers); _register(client, e["registration_slug"], 4)
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    allocs = client.get(f"/api/v1/events/{e['id']}/allocations", headers=auth_headers).json()
    assert any(x["id"] == a["id"] and x["status"] == "published" for x in allocs)
    assert len([x for x in allocs if x["status"] == "draft"]) == 1
