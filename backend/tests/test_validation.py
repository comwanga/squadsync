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

def test_register_rejects_invalid_experience_level(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "primary_strength": "technical", "experience_level": "wizard",
    })
    assert res.status_code == 422


def test_register_rejects_invalid_primary_strength(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "primary_strength": "astronaut", "experience_level": "beginner",
    })
    assert res.status_code == 422


def test_register_rejects_other_without_text(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "A", "email": "a@test.com",
        "primary_strength": "other", "experience_level": "beginner",
    })
    assert res.status_code == 422


# --- H4: duplicate email dedup ---

def test_duplicate_email_cannot_update_existing_participant(client, auth_headers):
    event = _active_event(client, auth_headers)
    slug = event["registration_slug"]
    body = {
        "name": "A", "email": "dup@test.com",
        "primary_strength": "technical", "experience_level": "beginner",
    }
    first = client.post(f"/api/v1/events/{slug}/register", json=body)
    assert first.status_code == 201
    second = client.post(f"/api/v1/events/{slug}/register", json={
        **body, "name": "B", "primary_strength": "design", "experience_level": "advanced",
    })
    assert second.status_code == 409

    participants = client.get(
        f"/api/v1/events/{event['id']}/participants", headers=auth_headers
    ).json()
    assert participants[0]["name"] == "A"
    assert participants[0]["primary_strength"] == "technical"


def test_allocation_config_rejects_invalid_constraints(client, auth_headers):
    event = _active_event(client, auth_headers)
    invalid_role = client.put(
        f"/api/v1/events/{event['id']}/config",
        headers=auth_headers,
        json={"role_constraints": {"astronaut": 1}},
    )
    invalid_count = client.put(
        f"/api/v1/events/{event['id']}/config",
        headers=auth_headers,
        json={"role_constraints": {"technical": 0}},
    )
    assert invalid_role.status_code == 422
    assert invalid_count.status_code == 422


def test_readiness_checks_database(client):
    res = client.get("/ready")
    assert res.status_code == 200
    assert res.json() == {"status": "ready"}
