#!/usr/bin/env bash
# Останавливаем скрипт при любой ошибке, необъявленной переменной или сбое в конвейере
set -euo pipefail

# Файл с настройками усиления SSH
CONF=/etc/ssh/sshd_config.d/10-hardening.conf
# Пользователи, которым разрешен вход по SSH
ALLOWED_USERS="lera yulya ira"

# Проверяем каждого разрешенного пользователя до изменения настроек
for u in $ALLOWED_USERS; do
  # Пользователь должен существовать в системе
  if ! id "$u" >/dev/null 2>&1; then
    echo "ОШИБКА: пользователь $u не существует — сначала создайте администраторов" >&2
    exit 1
  fi
  # У пользователя должен быть публичный ключ, иначе после запрета паролей он потеряет доступ
  if ! sudo test -s "/home/$u/.ssh/authorized_keys"; then
    echo "ОШИБКА: у $u нет /home/$u/.ssh/authorized_keys — сначала добавьте его публичный ключ, иначе он потеряет доступ" >&2
    exit 1
  fi
done

# Записываем конфигурацию: без root, без паролей, только по ключам, только перечисленные пользователи
sudo tee "$CONF" >/dev/null <<CONFIG
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
AllowUsers $ALLOWED_USERS
CONFIG

# Проверяем синтаксис конфигурации до перезапуска службы
sudo sshd -t
# Применяем новые настройки
sudo systemctl restart ssh

# Подсказка для проверки в новом окне, не закрывая текущую сессию
echo "Готово. Проверьте в НОВОМ окне:"
echo "  ssh root@<адрес>   -> отказ"
echo "  ssh lera@<адрес>   -> вход без пароля"
# Показываем действующие параметры sshd
echo "Текущие параметры:"
sudo sshd -T | grep -E "^(permitrootlogin|passwordauthentication|pubkeyauthentication|allowusers)"
