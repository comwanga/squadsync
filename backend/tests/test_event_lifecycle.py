import pytest
from coincurve import PrivateKey
from tests.conftest import make_nostr_event


@pytest.fixture
def other_headers(client):
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(pk)
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _active_event(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "LC", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    return e


def test_event_at_roundtrips(client, auth_headers):
    res = client.post("/api/v1/events", headers=auth_headers,
                      json={"title": "Dated", "team_count": 2, "event_at": "2026-07-15T14:00:00"})
    assert res.status_code == 201
    assert res.json()["event_at"].startswith("2026-07-15T14:00")


def test_archive_keeps_row_and_filters(client, auth_headers):
    e = _active_event(client, auth_headers)
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "archived"})
    active = client.get("/api/v1/events", headers=auth_headers).json()
    assert all(x["id"] != e["id"] for x in active)
    archived = client.get("/api/v1/events?archived=true", headers=auth_headers).json()
    assert any(x["id"] == e["id"] for x in archived)


def test_delete_hard_removes_event_and_children(client, auth_headers, db):
    from app.models.participant import Participant
    from app.models.allocation import Allocation
    e = _active_event(client, auth_headers)
    slug = e["registration_slug"]
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers)
    res = client.delete(f"/api/v1/events/{e['id']}", headers=auth_headers)
    assert res.status_code == 200
    assert client.get(f"/api/v1/events/{e['id']}", headers=auth_headers).status_code == 404
    import uuid as _uuid
    eid = _uuid.UUID(e["id"])
    assert db.query(Participant).filter(Participant.event_id == eid).count() == 0
    assert db.query(Allocation).filter(Allocation.event_id == eid).count() == 0


def test_delete_requires_organizer(client, auth_headers, other_headers):
    e = _active_event(client, auth_headers)
    assert client.delete(f"/api/v1/events/{e['id']}", headers=other_headers).status_code == 403
