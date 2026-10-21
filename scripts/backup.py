import argparse
import os
import shutil
import sqlite3

# reason: pg_dump/pg_restore are launched without a shell, see _run()
import subprocess  # nosec B404
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from sqlalchemy.engine import URL, make_url

BACKUP_DIR = Path("backups")
PREFIX = "library_"


class BackupError(Exception):
    """Понятная пользователю ошибка резервного копирования/восстановления."""


def _backend(url: URL) -> str:
    name = url.get_backend_name()
    if name not in ("postgresql", "sqlite"):
        raise BackupError(f"Неподдерживаемая СУБД: {name}")
    return name


def _sqlite_path(url: URL) -> str:
    path = url.database
    if not path or path == ":memory:":
        raise BackupError("Для SQLite нужен файл БД (in-memory базу копировать нельзя)")
    return path


def _pg_connection_args(url: URL) -> list[str]:
    return [
        "--host",
        url.host or "localhost",
        "--port",
        str(url.port or 5432),
        "--username",
        url.username or "postgres",
        "--dbname",
        url.database or "",
    ]


def _pg_env(url: URL) -> dict[str, str]:
    env = os.environ.copy()
    if url.password:
        env["PGPASSWORD"] = url.password
    return env


def _find_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise BackupError(f"Не найдена утилита {name} (установите postgresql-client)")
    return path


def _run(cmd: list[str], env: dict[str, str]) -> None:
    try:
        # reason: cmd is a list built from validated config, no shell is used
        subprocess.run(cmd, env=env, check=True)  # nosec B603
    except subprocess.CalledProcessError as exc:
        raise BackupError(f"{Path(cmd[0]).name} завершилась с ошибкой {exc.returncode}") from exc


def backup(database_url: str, out_dir: Path = BACKUP_DIR, now: Optional[datetime] = None) -> Path:
    """Создает резервную копию и возвращает путь к файлу."""
    url = make_url(database_url)
    backend = _backend(url)
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    if backend == "sqlite":
        source = _sqlite_path(url)
        if not Path(source).exists():
            raise BackupError(f"Файл БД не найден: {source}")
        target = out_dir / f"{PREFIX}{stamp}.sqlite3"
        src = sqlite3.connect(source)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return target

    target = out_dir / f"{PREFIX}{stamp}.dump"
    cmd = [_find_tool("pg_dump"), "--format=custom", "--no-owner", "--file", str(target)]
    cmd += _pg_connection_args(url)
    try:
        _run(cmd, _pg_env(url))
    except BackupError:
        target.unlink(missing_ok=True)  # не оставляем битый файл «резервной копии»
        raise
    return target


def latest_backup(out_dir: Path = BACKUP_DIR) -> Path:
    files = sorted(out_dir.glob(f"{PREFIX}*")) if out_dir.exists() else []
    if not files:
        raise BackupError(f"В {out_dir} нет резервных копий")
    return files[-1]


def restore(database_url: str, backup_file: Path) -> None:
    """Заменяет содержимое БД содержимым резервной копии."""
    url = make_url(database_url)
    backend = _backend(url)
    if not backup_file.exists():
        raise BackupError(f"Файл резервной копии не найден: {backup_file}")

    if backend == "sqlite":
        src = sqlite3.connect(backup_file)
        dst = sqlite3.connect(_sqlite_path(url))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        return

    cmd = [_find_tool("pg_restore"), "--clean", "--if-exists", "--no-owner", "--single-transaction"]
    cmd += _pg_connection_args(url)
    cmd.append(str(backup_file))
    _run(cmd, _pg_env(url))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scripts.backup", description=__doc__)
    parser.add_argument("--database-url", help="по умолчанию DATABASE_URL из окружения/.env")
    parser.add_argument("--dir", type=Path, default=BACKUP_DIR, help="каталог копий")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("backup", help="создать резервную копию")
    res = sub.add_parser("restore", help="восстановить из резервной копии")
    res.add_argument("--file", type=Path, help="файл копии (по умолчанию самый свежий)")
    res.add_argument("--yes", action="store_true", help="не спрашивать подтверждение")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        database_url = args.database_url
        if not database_url:
            from app.config import settings

            database_url = settings.database_url
        shown = make_url(database_url).render_as_string(hide_password=True)

        if args.command == "backup":
            path = backup(database_url, args.dir)
            print(f"Резервная копия создана: {path}")
            return 0

        path = args.file or latest_backup(args.dir)
        print(f"База: {shown}\nКопия: {path}\nТекущие данные БД будут заменены!")
        if not args.yes and input("Продолжить? [y/N] ").strip().lower() not in ("y", "yes"):
            print("Отменено")
            return 1
        restore(database_url, path)
        print("Восстановление завершено")
        return 0
    except BackupError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
