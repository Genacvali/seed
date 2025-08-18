#!/bin/bash
# Установка Redis и RabbitMQ без Docker для закрытых сред

set -e

echo "🚀 Установка Redis и RabbitMQ нативно..."

# Определяем ОС
if [ -f /etc/redhat-release ]; then
    OS="centos"
elif [ -f /etc/debian_version ]; then
    OS="ubuntu"
else
    echo "❌ Неподдерживаемая ОС"
    exit 1
fi

# Установка Redis
echo "📦 Устанавливаем Redis..."
if [ "$OS" = "centos" ]; then
    sudo yum install -y epel-release
    sudo yum install -y redis
    sudo systemctl enable redis
    sudo systemctl start redis
elif [ "$OS" = "ubuntu" ]; then
    sudo apt update
    sudo apt install -y redis-server
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
fi

# Установка RabbitMQ
echo "🐰 Устанавливаем RabbitMQ..."
if [ "$OS" = "centos" ]; then
    # Добавляем репозиторий RabbitMQ
    curl -s https://packagecloud.io/install/repositories/rabbitmq/rabbitmq-server/script.rpm.sh | sudo bash
    sudo yum install -y rabbitmq-server
elif [ "$OS" = "ubuntu" ]; then
    sudo apt install -y rabbitmq-server
fi

# Настройка RabbitMQ
echo "⚙️ Настраиваем RabbitMQ..."
sudo systemctl enable rabbitmq-server
sudo systemctl start rabbitmq-server

# Создаем пользователя для SEED
sudo rabbitmqctl add_user seed seed_password
sudo rabbitmqctl set_user_tags seed administrator
sudo rabbitmqctl set_permissions -p / seed ".*" ".*" ".*"

# Включаем management plugin
sudo rabbitmq-plugins enable rabbitmq_management

# Проверяем статус
echo "✅ Проверяем статус сервисов..."
sudo systemctl status redis --no-pager
echo ""
sudo systemctl status rabbitmq-server --no-pager

echo ""
echo "✅ Установка завершена!"
echo ""
echo "📝 Информация о сервисах:"
echo "   Redis: localhost:6379"
echo "   RabbitMQ: localhost:5672"
echo "   RabbitMQ Management: http://localhost:15672 (seed/seed_password)"
echo ""
echo "🔧 Полезные команды:"
echo "   sudo systemctl status redis"
echo "   sudo systemctl status rabbitmq-server"
echo "   sudo rabbitmqctl status"
echo "   redis-cli ping"