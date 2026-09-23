from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/popular-books")
def popular_books(limit: int = 10, db: Session = Depends(get_db)):
    rows = crud.report_popular_books(db, limit=limit)
    return [{"book_id": r[0], "title": r[1], "loans_count": r[2]} for r in rows]


@router.get("/copies-by-branch")
def copies_by_branch(db: Session = Depends(get_db)):
    return crud.report_copies_by_branch(db)
