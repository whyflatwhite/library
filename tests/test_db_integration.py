import pytest
from sqlalchemy.exc import IntegrityError

from app import models
from app.config import settings


def _author(db, name="Author"):
    author = models.Author(full_name=name)
    db.add(author)
    db.commit()
    return author


def test_test_configuration_is_isolated_from_real_database():
    assert settings.app_env == "test"
    assert settings.database_url.startswith("sqlite")


@pytest.mark.parametrize("round_number", [1, 2])
def test_every_test_starts_with_empty_database(db_session, round_number):
    assert db_session.query(models.Author).count() == 0
    _author(db_session)
    assert db_session.query(models.Author).count() == 1


def test_isbn_must_be_unique(db_session):
    author = _author(db_session)
    db_session.add(models.Book(title="One", isbn="111", author_id=author.id))
    db_session.commit()
    db_session.add(models.Book(title="Two", isbn="111", author_id=author.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_inventory_number_must_be_unique(db_session):
    author = _author(db_session)
    book = models.Book(title="B", author_id=author.id)
    branch = models.Branch(name="Main")
    db_session.add_all([book, branch])
    db_session.commit()
    db_session.add(models.Copy(inventory_number="X-1", book_id=book.id, branch_id=branch.id))
    db_session.commit()
    db_session.add(models.Copy(inventory_number="X-1", book_id=book.id, branch_id=branch.id))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_required_columns_reject_null(db_session):
    db_session.add(models.Author(full_name=None))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_loan_due_date_default_is_filled(db_session):
    author = _author(db_session)
    branch = models.Branch(name="Main")
    book = models.Book(title="B", author_id=author.id)
    db_session.add_all([branch, book])
    db_session.commit()
    copy_ = models.Copy(inventory_number="C-1", book_id=book.id, branch_id=branch.id)
    db_session.add(copy_)
    db_session.commit()
    loan = models.Loan(copy_id=copy_.id, borrower_name="Ivan")
    db_session.add(loan)
    db_session.commit()
    assert loan.due_at is not None
    assert loan.due_at > loan.issued_at
