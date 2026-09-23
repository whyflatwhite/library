def test_create_book_requires_existing_author(client):
    response = client.post("/books", json={"title": "Clean Code", "author_id": 999})
    assert response.status_code == 400


def test_create_book_success(client):
    author = client.post("/authors", json={"full_name": "Robert Martin"}).json()
    response = client.post("/books", json={"title": "Clean Code", "author_id": author["id"]})
    assert response.status_code == 201
    assert response.json()["title"] == "Clean Code"


def test_create_book_invalid_year_rejected(client):
    author = client.post("/authors", json={"full_name": "Someone"}).json()
    response = client.post(
        "/books", json={"title": "Bad Year Book", "author_id": author["id"], "published_year": 999}
    )
    assert response.status_code == 422
