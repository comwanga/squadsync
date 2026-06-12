import pytest


@pytest.fixture
def published_allocation(client, auth_headers):
    # Create event
    event = client.post("/api/v1/events", headers=auth_headers, json={"title": "H2026", "team_count": 2}).json()
    client.patch(f"/api/v1/events/{event['id']}", headers=auth_headers, json={"status": "active"})
    slug = event["registration_slug"]

    # Register 4 participants
    for i, (skill, role, years) in enumerate([
        ("advanced", "frontend", 4),
        ("intermediate", "backend", 2),
        ("beginner", "ux", 0),
        ("professional", "fullstack", 8),
    ]):
        client.post(f"/api/v1/events/{slug}/register", json={
            "name": f"Person{i}", "email": f"p{i}@test.com",
            "skill_level": skill, "role": role, "years_experience": years
        })

    # Run and publish allocation
    alloc = client.post(f"/api/v1/events/{event['id']}/allocate", headers=auth_headers).json()
    client.post(f"/api/v1/events/{event['id']}/allocations/{alloc['id']}/publish", headers=auth_headers)
    return alloc


def test_export_csv(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/csv", headers=auth_headers)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    content = res.text
    assert "Team" in content
    assert "Person" in content


def test_export_pdf(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/pdf", headers=auth_headers)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert res.content[:4] == b"%PDF"


def test_export_share_link(client, auth_headers, published_allocation):
    res = client.get(f"/api/v1/allocations/{published_allocation['id']}/export/link", headers=auth_headers)
    assert res.status_code == 200
    assert "url" in res.json()
    assert published_allocation["id"] in res.json()["url"]
