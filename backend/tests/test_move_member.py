import pytest
from coincurve import PrivateKey
from tests.conftest import make_nostr_event


@pytest.fixture
def other_headers(client):
    pk = PrivateKey()
    pubkey = pk.public_key.format(compressed=True)[1:].hex()
    res = client.post("/auth/nostr", json={"pubkey": pubkey, "event": make_nostr_event(pk)})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def _alloc(client, auth_headers):
    e = client.post("/api/v1/events", headers=auth_headers, json={"title": "MV", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design", "planning", "coordination"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"p{i}@t.com", "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    return e, a


def _members(team):
    return {m["id"] for m in team["members"]}


def test_move_reassigns_member(client, auth_headers):
    _, a = _alloc(client, auth_headers)
    src, dst = a["teams"][0], a["teams"][1]
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=auth_headers, json={"team_id": dst["id"]})
    assert res.status_code == 200
    by_id = {t["id"]: t for t in res.json()["teams"]}
    assert pid not in _members(by_id[src["id"]])
    assert pid in _members(by_id[dst["id"]])


def test_move_rejected_when_published(client, auth_headers):
    _, a = _alloc(client, auth_headers)
    client.post(f"/api/v1/events/{a['event_id']}/allocations/{a['id']}/publish", headers=auth_headers)
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=auth_headers, json={"team_id": a["teams"][1]["id"]})
    assert res.status_code == 409


def test_move_requires_organizer(client, auth_headers, other_headers):
    _, a = _alloc(client, auth_headers)
    pid = a["teams"][0]["members"][0]["id"]
    res = client.patch(f"/api/v1/allocations/{a['id']}/members/{pid}",
                       headers=other_headers, json={"team_id": a["teams"][1]["id"]})
    assert res.status_code == 403
