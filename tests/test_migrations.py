"""Проверка миграций Alembic на временной SQLite: чистая БД и БД с данными."""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TABLES = {
    "authors",
    "faculties",
    "branches",
    "books",
    "copies",
    "loans",
    "users",
    "sessions",
}


def _alembic(db_file: Path, *args: str) -> None:
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db_file.as_posix()}"}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _tables(db_file: Path) -> set:
    return set(inspect(create_engine(f"sqlite:///{db_file.as_posix()}")).get_table_names())


def _version(db_file: Path) -> str:
    with sqlite3.connect(db_file) as conn:
        return conn.execute("SELECT version_num FROM alembic_version").fetchone()[0]


@pytest.fixture()
def db_file(tmp_path):
    return tmp_path / "migrate.sqlite3"


def test_there_are_at_least_three_sequential_migrations():
    names = sorted(p.name for p in (ROOT / "migrations" / "versions").glob("0*.py"))
    assert len(names) >= 3
    assert [n[:4] for n in names] == [f"{i:04d}" for i in range(1, len(names) + 1)]


def test_clean_database_upgrades_to_head(db_file):
    _alembic(db_file, "upgrade", "head")
    assert EXPECTED_TABLES <= _tables(db_file)
    assert _version(db_file) == "0003"


def test_upgrade_keeps_existing_data_and_fills_due_date(db_file):
    _alembic(db_file, "upgrade", "0002")
    with sqlite3.connect(db_file) as conn:
        conn.executescript(
            """
            INSERT INTO authors (id, full_name) VALUES (1, 'Author');
            INSERT INTO branches (id, name) VALUES (1, 'Main');
            INSERT INTO books (id, title, author_id) VALUES (1, 'Book', 1);
            INSERT INTO copies (id, inventory_number, status, book_id, branch_id)
                VALUES (1, 'INV-1', 'issued', 1, 1);
            INSERT INTO loans (id, copy_id, borrower_name, issued_at)
                VALUES (1, 1, 'Ivan', '2026-01-01 10:00:00.000000');
            """
        )

    _alembic(db_file, "upgrade", "head")

    with sqlite3.connect(db_file) as conn:
        row = conn.execute("SELECT borrower_name, due_at FROM loans WHERE id = 1").fetchone()
        assert conn.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 1
    assert row[0] == "Ivan"
    assert row[1].startswith("2026-01-15 10:00:00")


def test_downgrade_removes_due_date_column(db_file):
    _alembic(db_file, "upgrade", "head")
    _alembic(db_file, "downgrade", "0002")
    engine = create_engine(f"sqlite:///{db_file.as_posix()}")
    columns = {c["name"] for c in inspect(engine).get_columns("loans")}
    assert "due_at" not in columns
    assert _version(db_file) == "0002"
