#!/bin/bash
# Установка SEED v2 как systemd сервис

set -e

SEED_DIR="/data/seed/v2"
SERVICE_DIR="/etc/systemd/system"

echo "🚀 Установка SEED v2 как systemd сервис..."

# Проверяем что мы в правильной директории
if [ ! -f "app.py" ] || [ ! -f "worker.py" ]; then
    echo "❌ Запустите скрипт из директории v2 проекта"
    exit 1
fi

# Копируем service файлы
echo "📁 Копируем service файлы..."
sudo cp seed-api.service $SERVICE_DIR/
sudo cp seed-worker.service $SERVICE_DIR/

# Обновляем systemd
echo "🔄 Перезагружаем systemd daemon..."
sudo systemctl daemon-reload

# Включаем сервисы
echo "✅ Включаем сервисы..."
sudo systemctl enable seed-api.service
sudo systemctl enable seed-worker.service

# Запускаем сервисы
echo "🎯 Запускаем сервисы..."
sudo systemctl start seed-api.service
sudo systemctl start seed-worker.service

# Проверяем статус
echo "📊 Проверяем статус сервисов..."
sudo systemctl status seed-api.service --no-pager
echo ""
sudo systemctl status seed-worker.service --no-pager

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Полезные команды:"
echo "   sudo systemctl status seed-api"
echo "   sudo systemctl status seed-worker"
echo "   sudo systemctl restart seed-api"
echo "   sudo systemctl restart seed-worker"
echo "   sudo journalctl -u seed-api -f"
echo "   sudo journalctl -u seed-worker -f"
echo ""
echo "🌐 API доступен на: http://localhost:8000/health"