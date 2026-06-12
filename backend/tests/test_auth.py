def test_register_success(client):
    res = client.post("/auth/register", json={
        "name": "Alice",
        "email": "alice@example.com",
        "password": "secret123"
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_register_duplicate_email(client):
    payload = {"name": "Alice", "email": "alice@example.com", "password": "secret123"}
    client.post("/auth/register", json=payload)
    res = client.post("/auth/register", json=payload)
    assert res.status_code == 400


def test_login_success(client, registered_user):
    res = client.post("/auth/login", json=registered_user)
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_login_wrong_password(client, registered_user):
    res = client.post("/auth/login", json={"email": registered_user["email"], "password": "wrong"})
    assert res.status_code == 401


def test_protected_route_without_token(client):
    res = client.get("/api/v1/events")
    assert res.status_code == 401


def test_protected_route_with_token(client, auth_headers):
    res = client.get("/api/v1/events", headers=auth_headers)
    assert res.status_code == 200


from unittest.mock import patch


def test_google_oauth_new_user(client):
    mock_idinfo = {
        "sub": "google-uid-123",
        "email": "googleuser@gmail.com",
        "name": "Google User",
    }
    with patch("app.services.auth_service.verify_google_token", return_value=mock_idinfo):
        res = client.post("/auth/google", json={"token": "fake-google-token"})
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_google_oauth_existing_user(client):
    mock_idinfo = {
        "sub": "google-uid-123",
        "email": "googleuser@gmail.com",
        "name": "Google User",
    }
    with patch("app.services.auth_service.verify_google_token", return_value=mock_idinfo):
        client.post("/auth/google", json={"token": "fake-google-token"})
        res = client.post("/auth/google", json={"token": "fake-google-token"})
    assert res.status_code == 200
