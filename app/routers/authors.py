from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/authors", tags=["authors"])


@router.post("", response_model=schemas.AuthorOut, status_code=201)
def create_author(data: schemas.AuthorCreate, db: Session = Depends(get_db)):
    return crud.create_author(db, data)


@router.get("", response_model=list[schemas.AuthorOut])
def list_authors(db: Session = Depends(get_db)):
    return crud.list_authors(db)
