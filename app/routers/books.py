from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/books", tags=["books"])


@router.post("", response_model=schemas.BookOut, status_code=201)
def create_book(data: schemas.BookCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_book(db, data)
    except crud.DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[schemas.BookOut])
def list_books(faculty_id: Optional[int] = None, db: Session = Depends(get_db)):
    return crud.list_books(db, faculty_id=faculty_id)


@router.get("/{book_id}", response_model=schemas.BookOut)
def get_book(book_id: int, db: Session = Depends(get_db)):
    book = crud.get_book(db, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book
