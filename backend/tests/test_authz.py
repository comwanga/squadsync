"""Authorization (C4), public results (C1), and allocation lifecycle (C5) tests."""
import pytest
from coincurve import PrivateKey

from tests.conftest import make_nostr_event


@pytest.fixture
def other_headers(client):
    """Auth headers for a *second*, unrelated organizer."""
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    event = make_nostr_event(pk)
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": event})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest.fixture
def published_allocation(client, auth_headers):
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "H2026", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    slug = event["registration_slug"]
    for i, (experience, strength) in enumerate([
        ("advanced", "technical"),
        ("intermediate", "technical"),
        ("beginner", "design"),
        ("advanced", "coordination"),
    ]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"Person{i}", "email": f"p{i}@test.com",
            "primary_strength": strength, "experience_level": experience,
        })
    alloc = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{event['id']}/allocations/{alloc['id']}/publish", headers=auth_headers)
    return {"event": event, "alloc": alloc}


# --- C4: cross-tenant IDOR is blocked ---

def test_other_user_cannot_export_csv(client, other_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['alloc']['id']}/export/csv", headers=other_headers)
    assert res.status_code == 403


def test_other_user_cannot_list_teams(client, other_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['alloc']['id']}/teams", headers=other_headers)
    assert res.status_code == 403


def test_other_user_cannot_get_share_link(client, other_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['alloc']['id']}/export/link", headers=other_headers)
    assert res.status_code == 403


# --- C1: public results endpoint ---

def test_public_allocation_returns_no_email(client, published_allocation):
    res = client.get(f"/api/v1/public/allocations/{published_allocation['alloc']['id']}")
    assert res.status_code == 200
    body = res.json()
    assert "teams" in body
    members = [m for t in body["teams"] for m in t["members"]]
    assert members, "expected at least one member"
    for m in members:
        assert "email" not in m
        assert m["name"]


def test_public_allocation_draft_is_404(client, auth_headers):
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "Draft", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    slug = event["registration_slug"]
    for i in range(2):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"P{i}", "email": f"d{i}@test.com",
            "primary_strength": "technical", "experience_level": "beginner",
        })
    alloc = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers).json()
    # Not published -> must not be publicly readable
    res = client.get(f"/api/v1/public/allocations/{alloc['id']}")
    assert res.status_code == 404


# --- C5: lifecycle ---

def test_publish_closes_registration(client, auth_headers, published_allocation):
    slug = published_allocation["event"]["registration_slug"]
    info = client.get(f"/api/v1/events/{slug}/info").json()
    assert info["status"] == "allocated"
    # Registration now rejected
    res = client.post(f"/api/v1/events/{slug}/register", json={
        "name": "Late", "email": "late@test.com",
        "primary_strength": "technical", "experience_level": "beginner",
    })
    assert res.status_code == 400


def test_list_allocations_returns_latest_first(client, auth_headers, published_allocation):
    event_id = published_allocation["event"]["id"]
    res = client.get(f"/api/v1/events/{event_id}/allocations", headers=auth_headers)
    assert res.status_code == 200
    allocs = res.json()
    assert len(allocs) >= 1
    assert allocs[0]["id"] == published_allocation["alloc"]["id"]
    assert allocs[0]["teams"]
