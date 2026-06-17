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
        "primary_strength": "technical",
        "experience_level": "intermediate",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alice"
    assert data["composite_score"] is not None
    # Preset strength is normalized immediately, with source "preset".
    assert data["normalized_strength"] == "technical"
    assert data["strength_source"] == "preset"


def test_composite_score_computed_correctly(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Bob",
        "email": "bob@example.com",
        "primary_strength": "technical",
        "experience_level": "advanced",   # advanced -> 3.0
    })
    assert res.json()["composite_score"] == pytest.approx(3.0)


def test_register_other_requires_text(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Carol", "email": "carol@example.com",
        "primary_strength": "other", "experience_level": "beginner",
    })
    assert res.status_code == 422  # strength_other missing


def test_register_other_with_text_is_pending(client, active_event):
    slug = active_event["registration_slug"]
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Dan", "email": "dan@example.com",
        "primary_strength": "other", "strength_other": "Agronomist",
        "experience_level": "advanced",
    })
    assert res.status_code == 201
    data = res.json()
    # Other entries are not normalized until allocation runs.
    assert data["normalized_strength"] is None


def test_duplicate_registration_rejected(client, active_event):
    slug = active_event["registration_slug"]
    payload = {"name": "Alice", "email": "alice@example.com", "primary_strength": "design", "experience_level": "beginner"}
    client.post(f"/api/v1/events/{slug}/register", json=payload)
    res = client.post(f"/api/v1/events/{slug}/register", json=payload)
    assert res.status_code == 400


def test_list_participants(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "primary_strength": "design", "experience_level": "beginner"
    })
    res = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers)
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_delete_participant(client, auth_headers, active_event):
    slug = active_event["registration_slug"]
    p = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Alice", "email": "alice@example.com", "primary_strength": "design", "experience_level": "beginner"
    }).json()
    res = client.delete(f"/api/v1/events/{active_event['id']}/participants/{p['id']}", headers=auth_headers)
    assert res.status_code == 200
    remaining = client.get(f"/api/v1/events/{active_event['id']}/participants", headers=auth_headers).json()
    assert len(remaining) == 0


# --- B2b: optional npub at registration ---

NPUB = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"


def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "Reg", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def _register(client, slug, **overrides):
    body = {
        "name": "Alice", "email": "alice@t.com",
        "primary_strength": "technical", "experience_level": "intermediate",
    }
    body.update(overrides)
    return client.post(f"/api/v1/events/{slug}/register", json=body)


def test_register_accepts_and_normalizes_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    # Uppercased + surrounding whitespace must be normalized to canonical lowercase.
    res = _register(client, e["registration_slug"], npub=f"  {NPUB.upper()}  ")
    assert res.status_code == 201
    assert res.json()["npub"] == NPUB


def test_register_rejects_malformed_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="bad@t.com", npub="not-an-npub")
    assert res.status_code == 422


def test_register_rejects_nsec_as_npub(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="nsec@t.com",
                    npub="nsec1vl029mgpspedva04g90vltkh6fvh240zqtv9k0t9af8935ke9laqsnlfe9")
    assert res.status_code == 422


def test_register_blank_npub_stored_none(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="blank@t.com", npub="   ")
    assert res.status_code == 201
    assert res.json()["npub"] is None


def test_register_omitted_npub_stored_none(client, auth_headers):
    e = _active_event(client, auth_headers)
    res = _register(client, e["registration_slug"], email="omit@t.com")
    assert res.status_code == 201
    assert res.json()["npub"] is None


def test_register_accepts_lightning_address(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "BTC++ Demo", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    res = client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
        "name": "Ada", "email": "ada@example.com",
        "primary_strength": "technical", "experience_level": "advanced",
        "lightning_address": "ada@getalby.com",
    })
    assert res.status_code in (200, 201)
    assert res.json()["lightning_address"] == "ada@getalby.com"
