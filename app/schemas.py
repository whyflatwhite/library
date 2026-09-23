from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models import CopyStatus


class AuthorCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    bio: Optional[str] = None


class AuthorOut(AuthorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class FacultyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class FacultyOut(FacultyCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: Optional[str] = None


class BranchOut(BranchCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BookCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    isbn: Optional[str] = Field(default=None, max_length=20)
    published_year: Optional[int] = Field(default=None, ge=1450, le=2100)
    author_id: int
    faculty_id: Optional[int] = None


class BookOut(BookCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class CopyCreate(BaseModel):
    inventory_number: str = Field(min_length=1, max_length=50)
    book_id: int
    branch_id: int


class CopyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    inventory_number: str
    status: CopyStatus
    book_id: int
    branch_id: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=255)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoanCreate(BaseModel):
    copy_id: int
    borrower_name: str = Field(min_length=1, max_length=255)


class LoanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    copy_id: int
    borrower_name: str
    issued_at: datetime
    returned_at: Optional[datetime]
