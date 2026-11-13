#!/usr/bin/env bash
# make container-check: автоматическая проверка контейнерного окружения.
# Работает в отдельном проекте Compose library_check на порту 18080: рабочие контейнеры
# и их данные не затрагиваются. В конце все созданное удаляется.
# Через переменную DOCKER_HOST работает и с демоном Docker-in-Docker (CI).
set -euo pipefail
cd "$(dirname "$0")/.."

export COMPOSE="docker compose -p library_check"
export APP_PORT=18080
# APP_HOST: где доступны опубликованные порты (в CI с DinD это хост docker)
BASE="http://${APP_HOST:-127.0.0.1}:${APP_PORT}"
BACKUP_DIR=$(mktemp -d)
export BACKUP_DIR

ok() { echo "OK:   $*"; }
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

for tool in docker curl; do
  command -v "$tool" >/dev/null || { echo "FAIL: не найдена утилита $tool" >&2; exit 1; }
done
[ -f .env ] || { cp .env.example .env; echo "Создан .env из .env.example"; }
grep -q '^POSTGRES_PASSWORD=' .env || {
  echo "FAIL: в .env нет настроек POSTGRES_* (возьмите их из .env.example)" >&2
  exit 1
}

echo "== 1. Статические правила =="
if grep -nE ':latest' Dockerfile docker-compose.yml; then fail "используется тег latest"; fi
ok "тег latest не используется"
if grep -E '^FROM ' Dockerfile | grep -vqE '^FROM [^ ]+:[^ ]+'; then fail "в FROM нет версии образа"; fi
ok "базовый образ с зафиксированной версией"
last_user=$(grep -E '^USER ' Dockerfile | tail -n 1 | awk '{print $2}' || true)
case "$last_user" in ""|root|0) fail "в Dockerfile нет непривилегированного USER" ;; esac
ok "в Dockerfile задан USER $last_user"
if grep -niE '(PASSWORD|SECRET|TOKEN)' Dockerfile; then fail "в Dockerfile упомянуты секреты"; fi
ok "в Dockerfile нет секретов"
$COMPOSE config -q || fail "docker-compose.yml некорректен"
ok "docker-compose.yml корректен"

echo "== 2. Сборка и запуск =="
$COMPOSE up -d --build --wait || fail "окружение не запустилось (или healthcheck не стал healthy)"
ok "окружение собрано и запущено"
bash scripts/container_db.sh migrate >/dev/null || fail "миграции не применились"
ok "миграции применены в контейнере"
body=$(curl -fsS "$BASE/health") || fail "/health не отвечает"
grep -q '"ok"' <<<"$body" || fail "/health вернул неожиданный ответ: $body"
ok "/health отвечает"

echo "== 3. Безопасность и эксплуатация =="
uid=$($COMPOSE exec -T api id -u | tr -d '\r')
[ "$uid" != "0" ] || fail "приложение запущено от root"
ok "процесс приложения запущен от uid $uid (не root)"
[ -z "$($COMPOSE port db 5432 2>/dev/null || true)" ] || fail "порт БД опубликован наружу"
ok "порт БД не опубликован"
for service in db api; do
  cid=$($COMPOSE ps -q "$service")
  health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid")
  [ "$health" = "healthy" ] || fail "healthcheck у $service: $health"
  memory=$(docker inspect --format '{{.HostConfig.Memory}}' "$cid")
  cpu=$(docker inspect --format '{{.HostConfig.NanoCpus}}' "$cid")
  [ "$memory" -gt 0 ] && [ "$cpu" -gt 0 ] || fail "у $service не заданы ограничения ресурсов"
  ok "$service: healthcheck healthy, лимиты памяти и процессора заданы"
done

echo "== 4. Сохранность данных =="
marker="container-check-$(date +%s)"
curl -fsS -X POST "$BASE/authors" -H 'Content-Type: application/json' \
  -d "{\"full_name\": \"$marker\"}" >/dev/null || fail "не удалось создать запись"
$COMPOSE down >/dev/null
$COMPOSE up -d --wait || fail "не запустилось после пересоздания"
authors=$(curl -fsS "$BASE/authors") || fail "не удалось прочитать данные"
grep -q "$marker" <<<"$authors" || fail "данные пропали после пересоздания контейнеров"
ok "данные сохранились после пересоздания контейнеров"
$COMPOSE up -d --build --force-recreate --wait || fail "не запустилось после обновления образа"
authors=$(curl -fsS "$BASE/authors") || fail "не удалось прочитать данные"
grep -q "$marker" <<<"$authors" || fail "данные пропали после обновления образа"
ok "данные сохранились после обновления образа"

echo "== 5. Корректное завершение =="
cid=$($COMPOSE ps -q api)
start=$(date +%s)
$COMPOSE stop -t 20 api >/dev/null
elapsed=$(( $(date +%s) - start ))
code=$(docker inspect --format '{{.State.ExitCode}}' "$cid")
# 0 или 143 (SIGTERM) - корректное завершение, 137 (SIGKILL) - процесс пришлось убить
case "$code" in 0|143) ;; *) fail "код завершения $code, процесс не завершился по SIGTERM" ;; esac
[ "$elapsed" -lt 10 ] || fail "остановка заняла $elapsed с"
ok "приложение завершилось по сигналу за $elapsed с (код $code)"
$COMPOSE up -d --wait || fail "не запустилось после остановки"

echo "== 6. Резервная копия и восстановление в новый volume =="
bash scripts/container_db.sh backup >/dev/null || fail "резервная копия не создалась"
$COMPOSE down -v >/dev/null
$COMPOSE up -d --wait || fail "не запустилось с новым volume"
ASSUME_YES=1 bash scripts/container_db.sh restore >/dev/null || fail "восстановление не удалось"
authors=$(curl -fsS "$BASE/authors") || fail "не удалось прочитать данные"
grep -q "$marker" <<<"$authors" || fail "после восстановления данных нет"
ok "данные восстановлены из копии в новый volume"

echo "container-check: все проверки пройдены"
