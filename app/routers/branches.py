from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/branches", tags=["branches"])


@router.post("", response_model=schemas.BranchOut, status_code=201)
def create_branch(data: schemas.BranchCreate, db: Session = Depends(get_db)):
    return crud.create_branch(db, data)


@router.get("", response_model=list[schemas.BranchOut])
def list_branches(db: Session = Depends(get_db)):
    return crud.list_branches(db)
