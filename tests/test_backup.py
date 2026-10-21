"""Резервное копирование и восстановление"""

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from scripts import backup as backup_module


@pytest.fixture()
def database(tmp_path):
    """Файловая БД SQLite с двумя авторами; возвращает (url, engine)."""
    url = f"sqlite:///{(tmp_path / 'library.sqlite3').as_posix()}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE authors (id INTEGER PRIMARY KEY, full_name TEXT NOT NULL)"))
        conn.execute(text("INSERT INTO authors (full_name) VALUES ('Tolstoy'), ('Pushkin')"))
    yield url, engine
    engine.dispose()


def _names(engine):
    with engine.connect() as conn:
        return [r[0] for r in conn.execute(text("SELECT full_name FROM authors ORDER BY id"))]


def test_backup_restore_after_deletion_and_corruption(database, tmp_path):
    url, engine = database
    copy_path = backup_module.backup(url, tmp_path / "backups")
    assert copy_path.exists()
    assert copy_path.name.startswith("library_")

    with engine.begin() as conn:  # намеренное удаление и порча данных
        conn.execute(text("DELETE FROM authors WHERE full_name = 'Pushkin'"))
        conn.execute(text("UPDATE authors SET full_name = 'BROKEN'"))
    assert _names(engine) == ["BROKEN"]

    backup_module.restore(url, copy_path)
    assert _names(engine) == ["Tolstoy", "Pushkin"]


def test_cli_backup_and_restore(database, tmp_path, capsys):
    url, engine = database
    folder = str(tmp_path / "cli")
    assert backup_module.main(["--database-url", url, "--dir", folder, "backup"]) == 0
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM authors"))
    args = ["--database-url", url, "--dir", folder, "restore", "--yes"]
    assert backup_module.main(args) == 0
    assert _names(engine) == ["Tolstoy", "Pushkin"]
    assert "Восстановление завершено" in capsys.readouterr().out


PG_URL = "postgresql+psycopg://library_owner:S3cret@db.local:5433/library"


@pytest.fixture()
def fake_pg(monkeypatch):
    calls = []

    def fake_run(cmd, env, check):
        calls.append((cmd, env))
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(backup_module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(backup_module.subprocess, "run", fake_run)
    return calls


def test_postgres_backup_command_hides_password(fake_pg, tmp_path):
    path = backup_module.backup(PG_URL, tmp_path)
    cmd, env = fake_pg[0]
    assert Path(cmd[0]).name == "pg_dump"
    assert "--format=custom" in cmd
    assert cmd[cmd.index("--host") + 1] == "db.local"
    assert cmd[cmd.index("--port") + 1] == "5433"
    assert cmd[cmd.index("--username") + 1] == "library_owner"
    assert cmd[cmd.index("--dbname") + 1] == "library"
    assert "S3cret" not in " ".join(cmd)
    assert env["PGPASSWORD"] == "S3cret"
    assert path.suffix == ".dump"


def test_postgres_restore_command_replaces_objects(fake_pg, tmp_path):
    dump = tmp_path / "library_20261019_123005.dump"
    dump.write_bytes(b"dump")
    backup_module.restore(PG_URL, dump)
    cmd, env = fake_pg[0]
    assert Path(cmd[0]).name == "pg_restore"
    assert "--clean" in cmd and "--single-transaction" in cmd
    assert cmd[-1] == str(dump)
    assert "S3cret" not in " ".join(cmd)
