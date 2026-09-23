from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/loans", tags=["loans"])


@router.post("", response_model=schemas.LoanOut, status_code=201)
def issue_copy(data: schemas.LoanCreate, db: Session = Depends(get_db)):
    try:
        return crud.issue_copy(db, data)
    except crud.DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{loan_id}/return", response_model=schemas.LoanOut)
def return_copy(loan_id: int, db: Session = Depends(get_db)):
    try:
        return crud.return_copy(db, loan_id)
    except crud.DomainError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[schemas.LoanOut])
def list_loans(active_only: bool = False, db: Session = Depends(get_db)):
    return crud.list_loans(db, active_only=active_only)
