def _event(client, auth_headers):
    event = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"title": "CSV", "team_count": 2},
    ).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    return event


def test_participant_csv_import_creates_and_updates(client, auth_headers):
    event = _event(client, auth_headers)
    csv_data = (
        "name,email,primary_strength,experience_level\n"
        "Ada,ada@example.com,technical,advanced\n"
        "Bo,bo@example.com,design,beginner\n"
    )
    first = client.post(
        f"/api/v1/events/{event['id']}/participants/import/csv",
        headers=auth_headers,
        files={"file": ("participants.csv", csv_data, "text/csv")},
    )
    assert first.status_code == 200
    assert first.json() == {"created": 2, "updated": 0, "skipped": 0, "errors": []}

    second = client.post(
        f"/api/v1/events/{event['id']}/participants/import/csv",
        headers=auth_headers,
        files={"file": (
            "participants.csv",
            "name,email,primary_strength,experience_level\nAda Lovelace,ada@example.com,research,advanced\n",
            "text/csv",
        )},
    )
    assert second.status_code == 200
    assert second.json()["updated"] == 1

    participants = client.get(f"/api/v1/events/{event['id']}/participants", headers=auth_headers).json()
    ada = next(p for p in participants if p["email"] == "ada@example.com")
    assert ada["name"] == "Ada Lovelace"
    assert ada["primary_strength"] == "research"


def test_participant_csv_export(client, auth_headers):
    event = _event(client, auth_headers)
    client.post(f"/api/v1/events/{event['registration_slug']}/register", json={
        "name": "Ada", "email": "ada@example.com",
        "primary_strength": "technical", "experience_level": "advanced",
    })
    res = client.get(f"/api/v1/events/{event['id']}/participants/export/csv", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "ada@example.com" in res.text
    assert "primary_strength" in res.text


def test_participant_csv_import_rejects_oversized_file(client, auth_headers):
    event = _event(client, auth_headers)
    res = client.post(
        f"/api/v1/events/{event['id']}/participants/import/csv",
        headers=auth_headers,
        files={"file": ("participants.csv", b"x" * 2_000_001, "text/csv")},
    )
    assert res.status_code == 413
