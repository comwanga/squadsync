def test_create_event(client, auth_headers):
    res = client.post("/api/v1/events", headers=auth_headers, json={
        "title": "Hackathon 2026",
        "team_count": 10
    })
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Hackathon 2026"
    assert "registration_slug" in data
    assert len(data["registration_slug"]) == 8


def test_list_events_empty(client, auth_headers):
    res = client.get("/api/v1/events", headers=auth_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_events_returns_own(client, auth_headers):
    client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5})
    res = client.get("/api/v1/events", headers=auth_headers)
    assert len(res.json()) == 1


def test_get_event(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.get(f"/api/v1/events/{created['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["id"] == created["id"]


def test_update_event(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "Old", "team_count": 5}).json()
    res = client.patch(f"/api/v1/events/{created['id']}", headers=auth_headers, json={"title": "New"})
    assert res.status_code == 200
    assert res.json()["title"] == "New"


def test_delete_event_archives_it(client, auth_headers):
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.delete(f"/api/v1/events/{created['id']}", headers=auth_headers)
    assert res.status_code == 200
    detail = client.get(f"/api/v1/events/{created['id']}", headers=auth_headers).json()
    assert detail["status"] == "archived"


def test_invite_co_organizer(client, auth_headers):
    # Register second user
    client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "pass123"})
    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    res = client.post(
        f"/api/v1/events/{created['id']}/co-organizers",
        headers=auth_headers,
        json={"email": "bob@example.com"}
    )
    assert res.status_code == 200


def test_co_organizer_can_view_event(client, auth_headers):
    client.post("/auth/register", json={"name": "Bob", "email": "bob@example.com", "password": "pass123"})
    bob_token = client.post("/auth/login", json={"email": "bob@example.com", "password": "pass123"}).json()["access_token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    created = client.post("/api/v1/events", headers=auth_headers, json={"title": "E1", "team_count": 5}).json()
    client.post(f"/api/v1/events/{created['id']}/co-organizers", headers=auth_headers, json={"email": "bob@example.com"})

    res = client.get(f"/api/v1/events/{created['id']}", headers=bob_headers)
    assert res.status_code == 200
