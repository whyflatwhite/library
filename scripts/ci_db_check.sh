#!/usr/bin/env bash
# Проверка миграций и резервного копирования на отдельной тестовой БД в Docker
# (в CI это демон Docker-in-Docker, на виртуальной машине обычный Docker).
# Использование:
#   bash scripts/ci_db_check.sh migrate   - миграции на чистой БД, откат и повторное применение
#   bash scripts/ci_db_check.sh backup    - копия, намеренное удаление данных, восстановление
# Работает в отдельном проекте Compose library_dbcheck, рабочие контейнеры не затрагиваются.
# Нужен файл .env с настройками POSTGRES_* (если его нет, берется .env.example).
set -euo pipefail
cd "$(dirname "$0")/.."

export COMPOSE="docker compose -p library_dbcheck"
export APP_PORT=18081
BACKUP_DIR=$(mktemp -d)
export BACKUP_DIR

[ -f .env ] || cp .env.example .env
grep -q '^POSTGRES_PASSWORD=' .env || { echo "FAIL: в .env нет настроек POSTGRES_*" >&2; exit 1; }

fail() {
  echo "FAIL: $*" >&2
  $COMPOSE logs --tail 30 >&2 || true
  exit 1
}
cleanup() {
  $COMPOSE down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$BACKUP_DIR"
}
trap cleanup EXIT

# SQL-запрос к БД внутри контейнера db (пароль не нужен: подключение по локальному сокету)
query() {
  $COMPOSE exec -T db sh -c 'psql -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -c "$0"' "$1"
}
alembic_current() { $COMPOSE exec -T api alembic current; }

$COMPOSE up -d --build --wait || fail "тестовая БД и приложение не запустились"

case "${1:-}" in
  migrate)
    echo "== Миграции на чистой БД =="
    bash scripts/container_db.sh migrate || fail "миграции не применились"
    alembic_current | grep -q "(head)" || fail "БД не на последней миграции"
    echo "== Откат на одну миграцию и повторное применение =="
    $COMPOSE exec -T api alembic downgrade -1 || fail "откат не удался"
    bash scripts/container_db.sh migrate || fail "повторное применение не удалось"
    alembic_current | grep -q "(head)" || fail "после повторного применения БД не на последней миграции"
    echo "OK: миграции применяются, откатываются и применяются снова"
    ;;

  backup)
    echo "== Подготовка: миграции и тестовые данные =="
    bash scripts/container_db.sh migrate || fail "миграции не применились"
    query "INSERT INTO authors (full_name) VALUES ('ci-backup-check')" >/dev/null
    echo "== Резервная копия =="
    bash scripts/container_db.sh backup || fail "копия не создалась"
    echo "== Намеренное удаление данных =="
    query "DELETE FROM authors" >/dev/null
    [ "$(query "SELECT COUNT(*) FROM authors")" = "0" ] || fail "данные не удалились"
    echo "== Восстановление =="
    ASSUME_YES=1 bash scripts/container_db.sh restore || fail "восстановление не удалось"
    count=$(query "SELECT COUNT(*) FROM authors WHERE full_name = 'ci-backup-check'")
    [ "$count" = "1" ] || fail "после восстановления данных нет"
    echo "OK: данные восстановлены из резервной копии"
    ;;

  *)
    echo "Использование: $0 migrate | backup" >&2
    exit 2
    ;;
esac
