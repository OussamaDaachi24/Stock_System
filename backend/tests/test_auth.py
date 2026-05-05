from tests.conftest import auth_headers


def test_login_success(client, admin_user):
    r = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "Password123!"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "access_token" in body["data"]["tokens"]


def test_login_bad_password(client, admin_user):
    r = client.post("/api/v1/auth/login", json={"email": admin_user.email, "password": "wrong"})
    assert r.status_code == 401


def test_me_endpoint(client, admin_token):
    r = client.get("/api/v1/auth/me", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["data"]["role"] == "admin"


def test_admin_can_create_user(client, admin_token):
    r = client.post(
        "/api/v1/admin/users",
        headers=auth_headers(admin_token),
        json={"email": "new@test.com", "name": "New", "password": "Password123!", "role": "operator"},
    )
    assert r.status_code == 201
    assert r.json()["data"]["email"] == "new@test.com"


def test_non_admin_cannot_create_user(client, operator_token):
    r = client.post(
        "/api/v1/admin/users",
        headers=auth_headers(operator_token),
        json={"email": "x@test.com", "name": "X", "password": "Password123!", "role": "operator"},
    )
    assert r.status_code == 403


def test_duplicate_email(client, admin_token, admin_user):
    r = client.post(
        "/api/v1/admin/users",
        headers=auth_headers(admin_token),
        json={"email": admin_user.email, "name": "X", "password": "Password123!", "role": "operator"},
    )
    assert r.status_code == 409
