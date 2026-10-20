from datetime import datetime, timedelta

from tests.helpers import issue, make_copy


def _dt(value):
    return datetime.fromisoformat(value)


def test_issue_unknown_copy_is_rejected(client):
    response = issue(client, 999)
    assert response.status_code == 400
    assert "не найден" in response.json()["detail"]


def test_return_unknown_loan_is_rejected(client):
    response = client.post("/loans/999/return")
    assert response.status_code == 400
    assert "не найдена" in response.json()["detail"]


def test_cannot_return_same_loan_twice(client):
    copy_ = make_copy(client)
    loan = issue(client, copy_["id"]).json()
    assert client.post(f"/loans/{loan['id']}/return").status_code == 200
    second = client.post(f"/loans/{loan['id']}/return")
    assert second.status_code == 400
    assert "уже закрыта" in second.json()["detail"]


def test_copy_status_follows_loan_lifecycle(client):
    copy_ = make_copy(client)
    assert copy_["status"] == "available"
    loan = issue(client, copy_["id"]).json()
    assert client.get("/copies").json()[0]["status"] == "issued"
    client.post(f"/loans/{loan['id']}/return")
    assert client.get("/copies").json()[0]["status"] == "available"


def test_default_due_date_is_14_days_after_issue(client):
    copy_ = make_copy(client)
    loan = issue(client, copy_["id"]).json()
    assert _dt(loan["due_at"]) - _dt(loan["issued_at"]) == timedelta(days=14)


def test_custom_loan_days_sets_due_date(client):
    copy_ = make_copy(client)
    loan = issue(client, copy_["id"], loan_days=3).json()
    assert _dt(loan["due_at"]) - _dt(loan["issued_at"]) == timedelta(days=3)


def test_loan_days_out_of_range_is_rejected(client):
    copy_ = make_copy(client)
    assert issue(client, copy_["id"], loan_days=0).status_code == 422
    assert issue(client, copy_["id"], loan_days=91).status_code == 422
