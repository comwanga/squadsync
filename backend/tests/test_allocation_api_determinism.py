def _active_event(client, auth_headers):
    event = client.post(
        "/api/v1/events",
        headers=auth_headers,
        json={"title": "Deterministic API", "team_count": 3},
    ).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    return event


def _register_participants(client, slug):
    rows = [
        ("Ava", "advanced", "technical"),
        ("Ben", "advanced", "design"),
        ("Cam", "intermediate", "planning"),
        ("Dee", "intermediate", "coordination"),
        ("Eli", "beginner", "communication"),
        ("Flo", "beginner", "research"),
        ("Gia", "advanced", "domain_expert"),
        ("Hal", "intermediate", "technical"),
        ("Ira", "beginner", "design"),
    ]
    for idx, (name, experience, strength) in enumerate(rows):
        res = client.post(
            f"/api/v1/events/{slug}/register",
            json={
                "name": name,
                "email": f"det-{idx}@example.com",
                "primary_strength": strength,
                "experience_level": experience,
            },
        )
        assert res.status_code == 201


def _membership_signature(allocation):
    return sorted(
        sorted(member["email"] for member in team["members"])
        for team in allocation["teams"]
    )


def test_api_allocation_is_deterministic_for_same_participants_and_settings(client, auth_headers):
    event = _active_event(client, auth_headers)
    _register_participants(client, event["registration_slug"])

    first = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers)
    second = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["snapshot_hash"] == second.json()["snapshot_hash"]
    assert _membership_signature(first.json()) == _membership_signature(second.json())
