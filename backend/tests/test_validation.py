"""Server-side validation (H3) and registration dedup (H4)."""


def _active_event(client, auth_headers, **overrides):
    payload = {"title": "V", "team_count": 3}
    payload.update(overrides)
    event = client.post("/api/v1/events", headers=auth_headers, json=payload).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    return event


# --- H3: event validation ---

def test_create_event_rejects_team_count_below_two(client, auth_headers):
    res = client.post("/api/v1/events", headers=auth_headers, json={"title": "X", "team_count": 1})
    assert res.status_code == 422


def test_update_event_rejects_unknown_status(client, auth_headers):
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "X", "team_count": 2}).json()
    res = client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "bogus"})
    assert res.status_code == 422


# --- H3: registration validation (no more 500s on bad enum values) ---

def test_register_rejects_invalid_skill_level(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "skill_level": "wizard", "role": "frontend", "years_experience": 1,
    })
    assert res.status_code == 422


def test_register_rejects_invalid_role(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "skill_level": "beginner", "role": "astronaut", "years_experience": 1,
    })
    assert res.status_code == 422


def test_register_rejects_negative_experience(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "skill_level": "beginner", "role": "frontend", "years_experience": -5,
    })
    assert res.status_code == 422


# --- H4: duplicate email dedup ---

def test_duplicate_email_rejected(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    body = {
        "name": "A", "email": "dup@test.com",
        "skill_level": "beginner", "role": "frontend", "years_experience": 1,
    }
    first = client.post(f"/api/v1/events/{slug}/register", json=body)
    assert first.status_code == 201
    second = client.post(f"/api/v1/events/{slug}/register", json={**body, "name": "B"})
    assert second.status_code == 400
