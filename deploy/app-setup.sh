#!/usr/bin/env bash
# Развёртывание сервера приложения library-app.
# Запуск от администратора (не от root): bash app-setup.sh
# Повторный запуск обновляет код и перезапускает службу.
# Пароли в репозитории не хранятся — только в /etc/library/*.env на сервере.

# Остановиться при первой же ошибке
set -euo pipefail

REPO_URL="git@github.com:whyflatwhite/library.git"
APP_DIR="/opt/library"
APP_USER="libapp"
CONF_DIR="/etc/library"
ADMIN_USER="$(id -un)"

if [ "$ADMIN_USER" = "root" ]; then
    echo "Запускайте от своего пользователя, не от root" >&2
    exit 1
fi

echo "1. Среда выполнения"
sudo apt-get update
sudo apt-get -y install python3 python3-venv python3-pip postgresql-client libpq5 git curl

# Системный пользователь приложения: без пароля, без домашней папки, без входа в систему
id "$APP_USER" >/dev/null 2>&1 || sudo adduser --system --group --no-create-home --shell /usr/sbin/nologin "$APP_USER"

echo "2. Код приложения"
[ -d "$APP_DIR" ] || sudo install -d -o "$ADMIN_USER" -g "$APP_USER" -m 750 "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO_URL" "$APP_DIR"
fi

[ -d "$APP_DIR/.venv" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo "3. Права на код"
# Приложение (группа libapp) может код только читать, остальные — ничего
sudo chgrp -R "$APP_USER" "$APP_DIR"
sudo chmod -R g+rX,g-w,o-rwx "$APP_DIR"
# setgid: файлы, появившиеся после git pull, тоже получат группу libapp
sudo find "$APP_DIR" -type d -exec chmod g+s {} +

echo "4. Настройки вне кода"
# 751: администратор может дойти до migrate.env, но список файлов посторонним не виден
sudo install -d -o root -g "$APP_USER" -m 751 "$CONF_DIR"
[ -f "$CONF_DIR/library.env" ] || sudo install -o root -g "$APP_USER" -m 640 "$APP_DIR/deploy/library.env.example" "$CONF_DIR/library.env"
[ -f "$CONF_DIR/migrate.env" ] || sudo install -o root -g "$ADMIN_USER" -m 640 "$APP_DIR/deploy/migrate.env.example" "$CONF_DIR/migrate.env"
if sudo grep -q CHANGE_ME "$CONF_DIR/library.env" "$CONF_DIR/migrate.env"; then
    echo "Впишите пароли в $CONF_DIR/library.env и $CONF_DIR/migrate.env и запустите скрипт снова" >&2
    exit 1
fi

echo "5. Миграции базы данных"
# Миграции выполняются под владельцем БД (library_owner) из migrate.env
if [ -f "$APP_DIR/alembic.ini" ]; then
    (cd "$APP_DIR" && set -a && . "$CONF_DIR/migrate.env" && set +a && PYTHONDONTWRITEBYTECODE=1 .venv/bin/alembic upgrade head)
else
    echo "alembic.ini не найден — миграции пропущены"
fi

echo "6. Служба systemd"
sudo install -m 644 "$APP_DIR/deploy/library.service" /etc/systemd/system/library.service
sudo systemctl daemon-reload
sudo systemctl enable library
sudo systemctl restart library
sleep 3
systemctl --no-pager status library
echo "Готово. Проверка: curl http://localhost:8000/health"
