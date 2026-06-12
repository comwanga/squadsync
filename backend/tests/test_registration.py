import pytest


@pytest.fixture
def active_event(client, auth_headers):
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "Hackathon", "team_count": 3}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    return event


def test_get_public_event_info(client, active_event):
    slug = active_event["registration_slug"]
    res = client.get(f"/api/v1/events/{slug}/info")
    assert res.status_code == 200
    assert res.json()["title"] == "Hackathon"


def test_register_participant(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "skill_level": "intermediate",
        "role": "frontend",
        "years_experience": 3
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alice"
    assert data["composite_score"] is not None


def test_composite_score_computed_correctly(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "skill_level": "advanced",   # K=3
        "role": "backend",
        "years_experience": 5        # E=3
    })
    # Default weights 0.5 each: Sc = (0.5*3) + (0.5*3) = 3.0
    assert res.json()["composite_score"] == pytest.approx(3.0)


def test_duplicate_registration_rejected(client, active_event):
    slug = active_event["registration_slug"]
    payload = {"name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0}
    client.post(f"/api/v1/events/{slug}/register", json=payload)
    res = client.post(f"/api/v1/events/{slug}/register", json=payload)
    assert res.status_code == 400


def test_list_participants(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0
    })
    res = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_delete_participant(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    p = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "skill_level": "beginner", "role": "ux", "years_experience": 0
    }).json()
    res = client.delete(f"/api/v1/events/{active_event['id']}/participants/{p['id']}", headers=auth_headers)
    assert res.status_code == 200
    remaining = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers).json()
    assert len(remaining) == 0
