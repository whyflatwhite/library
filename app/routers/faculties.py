from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/faculties", tags=["faculties"])


@router.post("", response_model=schemas.FacultyOut, status_code=201)
def create_faculty(data: schemas.FacultyCreate, db: Session = Depends(get_db)):
    return crud.create_faculty(db, data)


@router.get("", response_model=list[schemas.FacultyOut])
def list_faculties(db: Session = Depends(get_db)):
    return crud.list_faculties(db)
