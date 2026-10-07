#!/usr/bin/env bash
# Останавливаем скрипт при любой ошибке, необъявленной переменной или сбое в конвейере
set -euo pipefail

# Роль машины: app или db
ROLE="${1:-}"
# Сеть администраторов (host-only), с которой разрешен SSH
ADMIN_NET="${ADMIN_NET:-192.168.56.0/24}"
# Сеть Tailscale для удаленного SSH; пустое значение отключает правило
TAILSCALE_NET="${TAILSCALE_NET-100.64.0.0/10}"
# Адрес сервера приложения, единственный разрешенный клиент базы данных
APP_IP="${APP_IP:-192.168.56.10}"

# Без корректной роли дальше идти нельзя
if [[ "$ROLE" != "app" && "$ROLE" != "db" ]]; then
  echo "Использование: $0 app|db" >&2
  exit 1
fi

# Если пакет ufw поврежден и нет базовых файлов правил, переустанавливаем его
if [[ ! -f /etc/ufw/before.rules ]]; then
  echo "Восстанавливаю пакет ufw..."
  # Выключаем ufw, ошибку игнорируем: он мог быть не запущен
  sudo ufw disable || true
  sudo apt-get update
  # Параметр force-confmiss возвращает недостающие файлы конфигурации
  sudo apt-get -y install --reinstall -o Dpkg::Options::="--force-confmiss" ufw
fi

# Политика по умолчанию: входящее закрыто, исходящее открыто
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Сначала разрешаем SSH, иначе после включения потеряем доступ
sudo ufw allow from "$ADMIN_NET" to any port 22 proto tcp
# Разрешаем SSH из сети Tailscale, если она задана
if [[ -n "$TAILSCALE_NET" ]]; then
  sudo ufw allow from "$TAILSCALE_NET" to any port 22 proto tcp
fi

# На сервере приложения открываем порт приложения
if [[ "$ROLE" == "app" ]]; then
  sudo ufw allow 8000/tcp
# На сервере БД открываем PostgreSQL только для сервера приложения
else
  sudo ufw allow from "$APP_IP" to any port 5432 proto tcp
fi

# Включаем без вопроса, чтобы не зависеть от раскладки клавиатуры
sudo ufw --force enable
# Показываем итоговые правила
sudo ufw status verbose
