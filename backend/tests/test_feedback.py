from app.api.v1 import feedback as feedback_api


def test_feedback_requires_auth(client):
    res = client.post("/api/v1/feedback", json={"message": "hello"})
    assert res.status_code in (401, 403)


def test_feedback_persists_and_returns_201(client, auth_headers, db, monkeypatch):
    # No DM should be attempted unless FEEDBACK_NPUB is set; assert it stays unsent.
    calls = []
    monkeypatch.setattr(feedback_api, "send_dm", lambda *a, **k: calls.append(a) or True)
    monkeypatch.setattr(feedback_api.settings, "FEEDBACK_NPUB", None, raising=False)

    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "great app"})
    assert res.status_code == 201
    assert res.json() == {"detail": "received"}

    from app.models.feedback import Feedback
    rows = db.query(Feedback).all()
    assert len(rows) == 1
    assert rows[0].message == "great app"
    assert calls == []  # unconfigured recipient → no DM scheduled


def test_feedback_schedules_dm_when_npub_set(client, auth_headers, monkeypatch):
    calls = []
    monkeypatch.setattr(feedback_api, "send_dm", lambda npub, msg: calls.append((npub, msg)) or True)
    monkeypatch.setattr(
        feedback_api.settings, "FEEDBACK_NPUB", "npub1ownerxxxxxxxxxxxxxxxxxxxxxxxxxxx", raising=False
    )

    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "ping"})
    assert res.status_code == 201
    assert len(calls) == 1
    npub, msg = calls[0]
    assert npub == "npub1ownerxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    assert "ping" in msg


def test_feedback_rejects_empty_message(client, auth_headers):
    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": ""})
    assert res.status_code == 422


def test_feedback_rejects_overlong_message(client, auth_headers):
    res = client.post("/api/v1/feedback", headers=auth_headers, json={"message": "x" * 2001})
    assert res.status_code == 422
