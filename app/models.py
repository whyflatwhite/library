import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CopyStatus(str, enum.Enum):
    AVAILABLE = "available"
    ISSUED = "issued"
    LOST = "lost"


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    bio = Column(Text, nullable=True)
    books = relationship("Book", back_populates="author", cascade="all, delete-orphan")


class Faculty(Base):
    __tablename__ = "faculties"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    books = relationship("Book", back_populates="faculty")


class Branch(Base):
    __tablename__ = "branches"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    address = Column(String(255), nullable=True)
    copies = relationship("Copy", back_populates="branch")


class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    isbn = Column(String(20), nullable=True, unique=True)
    published_year = Column(Integer, nullable=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculties.id"), nullable=True)
    author = relationship("Author", back_populates="books")
    faculty = relationship("Faculty", back_populates="books")
    copies = relationship("Copy", back_populates="book", cascade="all, delete-orphan")


class Copy(Base):
    __tablename__ = "copies"
    __table_args__ = (UniqueConstraint("inventory_number", name="uq_copy_inventory_number"),)
    id = Column(Integer, primary_key=True)
    inventory_number = Column(String(50), nullable=False)
    status: Column[CopyStatus] = Column(
        Enum(CopyStatus, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=CopyStatus.AVAILABLE,
    )
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    book = relationship("Book", back_populates="copies")
    branch = relationship("Branch", back_populates="copies")
    loans = relationship("Loan", back_populates="copy")


class Loan(Base):
    __tablename__ = "loans"
    id = Column(Integer, primary_key=True)
    copy_id = Column(Integer, ForeignKey("copies.id"), nullable=False)
    borrower_name = Column(String(255), nullable=False)
    issued_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    returned_at = Column(DateTime, nullable=True)
    copy = relationship("Copy", back_populates="loans")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    token = Column(String(64), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    user = relationship("User", back_populates="sessions")
