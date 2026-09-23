from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/copies", tags=["copies"])


@router.post("", response_model=schemas.CopyOut, status_code=201)
def create_copy(data: schemas.CopyCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_copy(db, data)
    except crud.DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[schemas.CopyOut])
def list_copies(
    branch_id: Optional[int] = None, book_id: Optional[int] = None, db: Session = Depends(get_db)
):
    return crud.list_copies(db, branch_id=branch_id, book_id=book_id)
