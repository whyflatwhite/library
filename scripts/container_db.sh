#!/usr/bin/env bash
# Миграции, резервная копия и восстановление БД в контейнерном окружении.
# Использование:
#   bash scripts/container_db.sh migrate
#   bash scripts/container_db.sh backup
#   bash scripts/container_db.sh restore [backups/library_....dump]
# Пароль не передается: pg_dump и pg_restore запускаются внутри контейнера db.
set -euo pipefail
cd "$(dirname "$0")/.."

COMPOSE=${COMPOSE:-docker compose}
BACKUP_DIR=${BACKUP_DIR:-backups}
command=${1:-}

case "$command" in
  migrate)
    $COMPOSE exec -T api alembic upgrade head
    ;;

  backup)
    mkdir -p "$BACKUP_DIR"
    file="$BACKUP_DIR/library_$(date +%Y%m%d_%H%M%S).dump"
    if $COMPOSE exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' > "$file"; then
      echo "Резервная копия создана: $file"
    else
      rm -f "$file"
      echo "Ошибка: не удалось создать резервную копию" >&2
      exit 1
    fi
    ;;

  restore)
    file=${2:-}
    if [ -z "$file" ]; then
      file=$(ls -1 "$BACKUP_DIR"/library_*.dump 2>/dev/null | sort | tail -n 1 || true)
    fi
    if [ -z "$file" ] || [ ! -f "$file" ]; then
      echo "Ошибка: файл резервной копии не найден" >&2
      exit 1
    fi
    echo "Копия: $file"
    echo "Текущие данные БД будут заменены!"
    if [ "${ASSUME_YES:-0}" != "1" ]; then
      read -r -p "Продолжить? [y/N] " answer
      case "$answer" in y|Y|yes) ;; *) echo "Отменено"; exit 1 ;; esac
    fi
    $COMPOSE exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --single-transaction' < "$file"
    echo "Восстановление завершено"
    ;;

  *)
    echo "Использование: $0 migrate | backup | restore [файл]" >&2
    exit 2
    ;;
esac
