from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app import auth, models, schemas


class DomainError(Exception):
    pass


def create_author(db: Session, data: schemas.AuthorCreate) -> models.Author:
    author = models.Author(**data.model_dump())
    db.add(author)
    db.commit()
    db.refresh(author)
    return author


def list_authors(db: Session):
    return db.query(models.Author).order_by(models.Author.id).all()


def get_author(db: Session, author_id: int) -> Optional[models.Author]:
    return db.get(models.Author, author_id)


def create_faculty(db: Session, data: schemas.FacultyCreate) -> models.Faculty:
    faculty = models.Faculty(**data.model_dump())
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return faculty


def list_faculties(db: Session):
    return db.query(models.Faculty).order_by(models.Faculty.id).all()


def create_branch(db: Session, data: schemas.BranchCreate) -> models.Branch:
    branch = models.Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


def list_branches(db: Session):
    return db.query(models.Branch).order_by(models.Branch.id).all()


def create_book(db: Session, data: schemas.BookCreate) -> models.Book:
    if get_author(db, data.author_id) is None:
        raise DomainError(f"Автор с id={data.author_id} не найден")
    if data.faculty_id is not None and db.get(models.Faculty, data.faculty_id) is None:
        raise DomainError(f"Факультет с id={data.faculty_id} не найден")
    book = models.Book(**data.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


def list_books(db: Session, faculty_id: Optional[int] = None):
    query = db.query(models.Book)
    if faculty_id is not None:
        query = query.filter(models.Book.faculty_id == faculty_id)
    return query.order_by(models.Book.id).all()


def get_book(db: Session, book_id: int) -> Optional[models.Book]:
    return db.get(models.Book, book_id)


def create_copy(db: Session, data: schemas.CopyCreate) -> models.Copy:
    if get_book(db, data.book_id) is None:
        raise DomainError(f"Книга с id={data.book_id} не найдена")
    if db.get(models.Branch, data.branch_id) is None:
        raise DomainError(f"Филиал с id={data.branch_id} не найден")
    copy_ = models.Copy(**data.model_dump(), status=models.CopyStatus.AVAILABLE)
    db.add(copy_)
    db.commit()
    db.refresh(copy_)
    return copy_


def list_copies(db: Session, branch_id: Optional[int] = None, book_id: Optional[int] = None):
    query = db.query(models.Copy)
    if branch_id is not None:
        query = query.filter(models.Copy.branch_id == branch_id)
    if book_id is not None:
        query = query.filter(models.Copy.book_id == book_id)
    return query.order_by(models.Copy.id).all()


def get_copy(db: Session, copy_id: int) -> Optional[models.Copy]:
    return db.get(models.Copy, copy_id)


def issue_copy(db: Session, data: schemas.LoanCreate) -> models.Loan:
    copy_ = get_copy(db, data.copy_id)
    if copy_ is None:
        raise DomainError(f"Экземпляр с id={data.copy_id} не найден")
    if copy_.status != models.CopyStatus.AVAILABLE:
        raise DomainError(
            f"Нельзя выдать экземпляр id={copy_.id}: сначала оформите возврат предыдущей выдачи."
        )
    loan = models.Loan(copy_id=copy_.id, borrower_name=data.borrower_name)
    copy_.status = models.CopyStatus.ISSUED  # type: ignore[assignment]
    db.add(loan)
    db.add(copy_)
    db.commit()
    db.refresh(loan)
    return loan


def return_copy(db: Session, loan_id: int) -> models.Loan:
    loan = db.get(models.Loan, loan_id)
    if loan is None:
        raise DomainError(f"Выдача с id={loan_id} не найдена")
    if loan.returned_at is not None:
        raise DomainError(f"Выдача id={loan_id} уже закрыта возвратом")
    loan.returned_at = datetime.utcnow()
    copy_ = get_copy(db, loan.copy_id)
    copy_.status = models.CopyStatus.AVAILABLE  # type: ignore[assignment]
    db.add(loan)
    db.add(copy_)
    db.commit()
    db.refresh(loan)
    return loan


def list_loans(db: Session, active_only: bool = False):
    query = db.query(models.Loan)
    if active_only:
        query = query.filter(models.Loan.returned_at.is_(None))
    return query.order_by(models.Loan.id).all()


def create_user(db: Session, data: schemas.UserCreate) -> models.User:
    existing = db.query(models.User).filter(models.User.username == data.username).first()
    if existing is not None:
        raise DomainError(f"Пользователь с логином '{data.username}' уже существует")
    user = models.User(username=data.username, password_hash=auth.hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        return None
    if not auth.verify_password(password, str(user.password_hash)):
        return None
    return user


def create_session(db: Session, user_id: int) -> str:
    token = auth.generate_token()
    session = models.UserSession(token=token, user_id=user_id)
    db.add(session)
    db.commit()
    return token


def report_popular_books(db: Session, limit: int = 10):
    return (
        db.query(models.Book.id, models.Book.title, func.count(models.Loan.id).label("loans_count"))
        .join(models.Copy, models.Copy.book_id == models.Book.id)
        .join(models.Loan, models.Loan.copy_id == models.Copy.id)
        .group_by(models.Book.id, models.Book.title)
        .order_by(func.count(models.Loan.id).desc())
        .limit(limit)
        .all()
    )


def report_copies_by_branch(db: Session):
    rows = db.query(models.Branch.id, models.Branch.name).order_by(models.Branch.id).all()
    result = []
    for branch_id, branch_name in rows:
        total = db.query(models.Copy).filter(models.Copy.branch_id == branch_id).count()
        issued = (
            db.query(models.Copy)
            .filter(
                models.Copy.branch_id == branch_id, models.Copy.status == models.CopyStatus.ISSUED
            )
            .count()
        )
        result.append(
            {
                "branch_id": branch_id,
                "branch_name": branch_name,
                "total_copies": total,
                "issued_copies": issued,
            }
        )
