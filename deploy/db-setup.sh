#!/usr/bin/env bash
# Развёртывание сервера базы данных library-db.
# Запуск от администратора (не от root), пароли передаются через переменные окружения:
#   OWNER_PASSWORD='...' APP_PASSWORD='...' bash db-setup.sh
# Пароли в репозитории не хранятся.

# Остановиться при первой же ошибке
set -euo pipefail

: "${OWNER_PASSWORD:?задайте OWNER_PASSWORD}"
: "${APP_PASSWORD:?задайте APP_PASSWORD}"

DB_NAME="library"
APP_HOST="192.168.56.10"
DB_HOST="192.168.56.11"

# Команды от имени postgres выполняем из /tmp, чтобы не было предупреждений о домашней папке
cd /tmp

echo "1. Установка PostgreSQL"
sudo apt-get update
sudo apt-get -y install postgresql
sudo systemctl enable --now postgresql

PG_VER="$(ls /etc/postgresql | sort -V | tail -1)"
PG_CONF="/etc/postgresql/$PG_VER/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VER/main/pg_hba.conf"

echo "2. Роли и база данных"
# Обе роли могут входить, но не суперпользователи и не создают базы и роли
for ROLE in library_owner library_app; do
    if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$ROLE'" | grep -q 1; then
        sudo -u postgres psql -c "CREATE ROLE $ROLE LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;"
    fi
done
sudo -u postgres psql -v op="$OWNER_PASSWORD" -v ap="$APP_PASSWORD" <<'SQL'
ALTER ROLE library_owner PASSWORD :'op';
ALTER ROLE library_app PASSWORD :'ap';
SQL

if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1; then
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER library_owner;"
fi

echo "3. Минимальные права приложения"
# Подключаться к базе может только library_app (и владелец)
sudo -u postgres psql <<SQL
REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;
GRANT CONNECT ON DATABASE $DB_NAME TO library_app;
SQL
# На таблицы, которые создаст library_owner (миграции), приложение получает только работу с данными
sudo -u postgres psql -d "$DB_NAME" <<'SQL'
GRANT USAGE ON SCHEMA public TO library_app;
ALTER DEFAULT PRIVILEGES FOR ROLE library_owner IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO library_app;
ALTER DEFAULT PRIVILEGES FOR ROLE library_owner IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO library_app;
SQL

echo "4. Доступ к базе только с сервера приложения"
# Слушать только localhost и внутренний адрес, не 0.0.0.0
sudo sed -i "s/^#\?listen_addresses\s*=.*/listen_addresses = 'localhost,$DB_HOST'/" "$PG_CONF"
HBA_LINE="host  $DB_NAME  library_owner,library_app  $APP_HOST/32  scram-sha-256"
sudo grep -qF "$HBA_LINE" "$PG_HBA" || echo "$HBA_LINE" | sudo tee -a "$PG_HBA" >/dev/null

sudo systemctl restart postgresql
sleep 2
sudo ss -tlnp | grep 5432
echo "Готово. Проверка с сервера приложения: psql \"host=$DB_HOST dbname=$DB_NAME user=library_app\" -c 'select 1;'"
