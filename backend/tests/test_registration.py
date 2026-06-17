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
