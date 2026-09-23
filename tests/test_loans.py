def _create_available_copy(client):
    author = client.post("/authors", json={"full_name": "Author X"}).json()
    book = client.post("/books", json={"title": "Book X", "author_id": author["id"]}).json()
    branch = client.post("/branches", json={"name": "Central"}).json()
    copy_ = client.post(
        "/copies",
        json={"inventory_number": "INV-001", "book_id": book["id"], "branch_id": branch["id"]},
    ).json()
    return copy_


def test_cannot_issue_already_issued_copy(client):
    copy_ = _create_available_copy(client)
    first = client.post("/loans", json={"copy_id": copy_["id"], "borrower_name": "Ivan"})
    assert first.status_code == 201
    second = client.post("/loans", json={"copy_id": copy_["id"], "borrower_name": "Petr"})
    assert second.status_code == 400
    assert "уже выдан" in second.json()["detail"]


def test_can_issue_again_after_return(client):
    copy_ = _create_available_copy(client)
    loan = client.post("/loans", json={"copy_id": copy_["id"], "borrower_name": "Ivan"}).json()
    ret = client.post(f"/loans/{loan['id']}/return")
    assert ret.status_code == 200
    assert ret.json()["returned_at"] is not None
    second = client.post("/loans", json={"copy_id": copy_["id"], "borrower_name": "Petr"})
    assert second.status_code == 201
