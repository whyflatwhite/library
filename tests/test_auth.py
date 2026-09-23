def test_register_and_login(client):
    r = client.post("/auth/register", json={"username": "librarian1", "password": "secret123"})
    assert r.status_code == 201

    r = client.post("/auth/login", json={"username": "librarian1", "password": "secret123"})
    assert r.status_code == 200
    token = r.json()["access_token"]

    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["username"] == "librarian1"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "librarian2", "password": "secret123"})
    r = client.post("/auth/login", json={"username": "librarian2", "password": "wrong"})
    assert r.status_code == 401


def test_me_without_token(client):
    r = client.get("/auth/me")
    assert r.status_code == 401


def test_duplicate_username(client):
    client.post("/auth/register", json={"username": "librarian3", "password": "secret123"})
    r = client.post("/auth/register", json={"username": "librarian3", "password": "other123"})
    assert r.status_code == 400
