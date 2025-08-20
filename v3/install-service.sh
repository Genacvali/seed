#!/bin/bash
# =============================================================================
# Установка SEED Agent как systemd сервис
# =============================================================================

set -e

echo "🔧 Установка SEED Agent как systemd сервис"
echo "=========================================="

# Проверяем права root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт от имени root: sudo $0"
    exit 1
fi

# Проверяем systemd
if ! command -v systemctl &> /dev/null; then
    echo "❌ systemd не найден. Этот скрипт работает только в системах с systemd."
    exit 1
fi

# Переходим в директорию проекта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Проверяем наличие бинарника
if [ ! -f "dist/seed-agent" ]; then
    echo "❌ Бинарник не найден! Сначала соберите агент: ./build-agent.sh"
    exit 1
fi

# Создаем пользователя для сервиса
echo "👤 Создание пользователя seed..."
if ! id "seed" &>/dev/null; then
    useradd -r -s /bin/false -d /opt/seed seed
    echo "✅ Пользователь seed создан"
else
    echo "ℹ️  Пользователь seed уже существует"
fi

# Создаем директории
echo "📁 Создание директорий..."
mkdir -p /opt/seed
mkdir -p /etc/seed
mkdir -p /var/log/seed
mkdir -p /var/lib/seed

# Копируем файлы
echo "📋 Копирование файлов..."
cp dist/seed-agent /opt/seed/
cp seed.yaml /etc/seed/
cp plugins.py /etc/seed/
chmod +x /opt/seed/seed-agent

# Настраиваем права доступа
chown -R seed:seed /opt/seed
chown -R seed:seed /var/log/seed
chown -R seed:seed /var/lib/seed
chown -R root:seed /etc/seed
chmod 750 /etc/seed

echo "📝 Создание systemd service файла..."

# Создаем systemd service файл
cat > /etc/systemd/system/seed-agent.service << 'EOF'
[Unit]
Description=SEED Agent - Monitoring and Alerting System
After=network.target
Wants=network.target

[Service]
Type=exec
User=seed
Group=seed
WorkingDirectory=/opt/seed
ExecStart=/opt/seed/seed-agent --mode both --host 0.0.0.0 --port 8080 --config /etc/seed/seed.yaml --plugins /etc/seed/plugins.py
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
TimeoutStopSec=30
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=/var/log/seed /var/lib/seed
ProtectHome=yes
ProtectKernelTunables=yes
ProtectControlGroups=yes
RestrictSUIDSGID=yes

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=seed-agent

# Environment
Environment=PYTHONPATH=/opt/seed
Environment=REDIS_URL=redis://127.0.0.1:6379/0
Environment=RABBITMQ_URL=amqp://seed:seed_password@127.0.0.1:5672//

[Install]
WantedBy=multi-user.target
EOF

# Перезагружаем systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# Включаем автозапуск
echo "⚙️  Включение автозапуска..."
systemctl enable seed-agent.service

echo "✅ SEED Agent установлен как systemd сервис!"
echo ""
echo "📋 Управление сервисом:"
echo "   sudo systemctl start seed-agent     # Запустить"
echo "   sudo systemctl stop seed-agent      # Остановить"  
echo "   sudo systemctl restart seed-agent   # Перезапустить"
echo "   sudo systemctl status seed-agent    # Статус"
echo "   sudo systemctl enable seed-agent    # Автозапуск (уже включен)"
echo "   sudo systemctl disable seed-agent   # Отключить автозапуск"
echo ""
echo "📊 Логи:"
echo "   sudo journalctl -u seed-agent -f    # Просмотр логов в реальном времени"
echo "   sudo journalctl -u seed-agent       # Все логи сервиса"
echo ""
echo "📂 Файлы:"
echo "   Бинарник:      /opt/seed/seed-agent"
echo "   Конфигурация:  /etc/seed/seed.yaml"
echo "   Плагины:       /etc/seed/plugins.py"  
echo "   Логи:          /var/log/seed/"
echo "   Данные:        /var/lib/seed/"
echo ""
echo "🚀 Для запуска сервиса выполните:"
echo "   sudo systemctl start seed-agent"