import pytest
from pydantic import ValidationError

from app import schemas
from app.models import LOAN_DAYS_DEFAULT, LOAN_DAYS_MAX


@pytest.mark.parametrize("year", [1450, 2024, 2100])
def test_book_year_within_bounds_is_valid(year):
    book = schemas.BookCreate(title="T", author_id=1, published_year=year)
    assert book.published_year == year


@pytest.mark.parametrize("year", [1449, 2101, 0, -5])
def test_book_year_out_of_bounds_is_rejected(year):
    with pytest.raises(ValidationError):
        schemas.BookCreate(title="T", author_id=1, published_year=year)


def test_book_title_length_boundaries():
    assert schemas.BookCreate(title="a", author_id=1).title == "a"
    assert len(schemas.BookCreate(title="a" * 255, author_id=1).title) == 255
    with pytest.raises(ValidationError):
        schemas.BookCreate(title="", author_id=1)
    with pytest.raises(ValidationError):
        schemas.BookCreate(title="a" * 256, author_id=1)


def test_user_password_and_username_minimum_length():
    assert schemas.UserCreate(username="abc", password="123456")
    with pytest.raises(ValidationError):
        schemas.UserCreate(username="ab", password="123456")
    with pytest.raises(ValidationError):
        schemas.UserCreate(username="abc", password="12345")


def test_loan_days_default_and_boundaries():
    assert schemas.LoanCreate(copy_id=1, borrower_name="I").loan_days == LOAN_DAYS_DEFAULT
    assert schemas.LoanCreate(copy_id=1, borrower_name="I", loan_days=1).loan_days == 1
    assert schemas.LoanCreate(copy_id=1, borrower_name="I", loan_days=LOAN_DAYS_MAX)
    for bad in (0, -1, LOAN_DAYS_MAX + 1):
        with pytest.raises(ValidationError):
            schemas.LoanCreate(copy_id=1, borrower_name="I", loan_days=bad)


def test_loan_requires_borrower_name():
    with pytest.raises(ValidationError):
        schemas.LoanCreate(copy_id=1, borrower_name="")


def test_copy_inventory_number_boundaries():
    assert schemas.CopyCreate(inventory_number="x" * 50, book_id=1, branch_id=1)
    for bad in ("", "x" * 51):
        with pytest.raises(ValidationError):
            schemas.CopyCreate(inventory_number=bad, book_id=1, branch_id=1)
