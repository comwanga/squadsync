from uuid import UUID

import app.api.v1.allocation as alloc_mod
import app.services.team_notifications as tn

NPUB = "npub180cvv07tjdrrgpa0j7j7tmnyl2yr6yr7l8j4s3evf6u64th6gkwsyjh6w6"


def _published_with_npubs(client, auth_headers):
    """Create an active event, register 2 npub + 2 non-npub attendees, allocate, publish.

    NOTE: publish runs with SQUADSYNC_NSEC unset here, so any scheduled background
    notify task no-ops (writes nothing) — leaving the allocation clean for the
    direct notify_teams_task calls in each test.
    """
    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "Notify", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    regs = [
        ("A", "a@t.com", "technical", NPUB),
        ("B", "b@t.com", "design", NPUB),
        ("C", "c@t.com", "planning", None),
        ("D", "d@t.com", "coordination", None),
    ]
    for name, email, strength, npub in regs:
        body = {"name": name, "email": email, "primary_strength": strength,
                "experience_level": "intermediate"}
        if npub:
            body["npub"] = npub
        assert client.post(f"/api/v1/events/{e['registration_slug']}/register", json=body).status_code == 201
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    return e, a


def test_notify_dms_only_npub_members_once(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)

    calls = []
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: calls.append((npub, msg)) or True)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", "nsec1bot", raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    tn.notify_teams_task(UUID(a["id"]))
    assert len(calls) == 2  # only the two npub-having members
    assert all(npub == NPUB for npub, _ in calls)
    assert all("results/" in msg for _, msg in calls)

    # Dedup: a second run for the same allocation sends nothing.
    calls.clear()
    tn.notify_teams_task(UUID(a["id"]))
    assert calls == []


def test_notify_writes_no_row_on_send_failure(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", "nsec1bot", raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    # All sends fail → no dedup rows written.
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: False)
    tn.notify_teams_task(UUID(a["id"]))

    # A later re-run (now succeeding) retries both, proving nothing was suppressed.
    sent = []
    monkeypatch.setattr(tn, "send_dm", lambda npub, msg: sent.append(npub) or True)
    tn.notify_teams_task(UUID(a["id"]))
    assert len(sent) == 2


def test_notify_noop_when_nsec_unset(client, auth_headers, session_factory, monkeypatch):
    e, a = _published_with_npubs(client, auth_headers)
    calls = []
    monkeypatch.setattr(tn, "send_dm", lambda *args, **kwargs: calls.append(1) or True)
    monkeypatch.setattr(tn.settings, "SQUADSYNC_NSEC", None, raising=False)
    monkeypatch.setattr(tn, "SessionLocal", session_factory)

    tn.notify_teams_task(UUID(a["id"]))
    assert calls == []


def test_publish_schedules_notify_task(client, auth_headers, monkeypatch):
    scheduled = []
    monkeypatch.setattr(alloc_mod, "notify_teams_task", lambda aid: scheduled.append(aid))

    e = client.post("/api/v1/events", headers=auth_headers,
                    json={"title": "Sched", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{e['id']}", headers=auth_headers, json={"status": "active"})
    for i, s in enumerate(["technical", "design"]):
        client.post(f"/api/v1/events/{e['registration_slug']}/register", json={
            "name": f"P{i}", "email": f"s{i}@t.com",
            "primary_strength": s, "experience_level": "intermediate"})
    a = client.post(f"/api/v1/events/{e['id']}/allocate", headers=auth_headers).json()

    res = client.post(f"/api/v1/events/{e['id']}/allocations/{a['id']}/publish", headers=auth_headers)
    assert res.status_code == 200
    # TestClient runs BackgroundTasks after the response; the scheduled task ran.
    assert len(scheduled) == 1
    # Enforce the contract that a real UUID (not a string) is passed to the task.
    assert scheduled[0] == UUID(a["id"])
