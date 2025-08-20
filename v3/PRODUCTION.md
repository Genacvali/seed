# 🚀 SEED Agent - Production Deployment

## Подготовка для продакшн

### 1. Создание деплой пакета
```bash
# На dev машине собираем пакет
tar -czf seed-prod-$(date +%Y%m%d).tar.gz \
    v3/ \
    docker_images.tar \
    --exclude=v3/logs/* \
    --exclude=v3/venv
```

### 2. Перенос на продакшн сервер
```bash
# Копирование на prod сервер
scp seed-prod-20241220.tar.gz user@prod-server:/opt/

# На продакшн сервере
cd /opt/
tar -xzf seed-prod-20241220.tar.gz
cd v3/
```

### 3. Настройка для продакшн
```bash
# Создать продакшн конфигурацию
cp seed.yaml seed.yaml.prod

# Отредактировать под продакшн
vim seed.yaml.prod
```

### 4. Развертывание
```bash
# Загрузка образов и запуск
./deploy.sh offline-build
./deploy.sh start

# Проверка
./deploy.sh status
curl http://localhost:8080/health
```

## Продакшн конфигурация

### Системные требования
- CPU: 2 ядра минимум
- RAM: 4GB минимум  
- Disk: 20GB свободного места
- Docker версии 20.10+

### Безопасность
```yaml
# seed.yaml.prod - примеры продакшн настроек
redis:
  password: "strong_redis_password_here"
  
rabbitmq:
  user: "prod_seed_user"
  password: "strong_rabbitmq_password_here"
  
notifications:
  mattermost:
    webhook_url: "https://mattermost.company.com/hooks/..."
```

### Автозапуск (systemd)
```bash
# Создать systemd service
sudo tee /etc/systemd/system/seed-agent.service << 'EOF'
[Unit]
Description=SEED Agent
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/seed/v3
ExecStart=/opt/seed/v3/deploy.sh start
ExecStop=/opt/seed/v3/deploy.sh stop
User=root

[Install]
WantedBy=multi-user.target
EOF

# Включить автозапуск
sudo systemctl enable seed-agent.service
sudo systemctl start seed-agent.service
```

## Мониторинг продакшн

### Логи
```bash
# Логи всех сервисов
./deploy.sh logs

# Логи только SEED Agent
docker logs -f seed-agent

# Логи на диске
tail -f logs/seed-agent.log
```

### Метрики
- Health: http://localhost:8080/health
- Stats: http://localhost:8080/stats  
- RabbitMQ: http://localhost:15672

### Резервное копирование
```bash
# Бэкап конфигурации и данных
tar -czf seed-backup-$(date +%Y%m%d).tar.gz \
    seed.yaml \
    plugins.py \
    logs/ \
    /var/lib/docker/volumes/v3_redis_data/ \
    /var/lib/docker/volumes/v3_rabbitmq_data/
```

## Обновление в продакшн

### 1. Подготовка нового релиза
```bash
# На dev машине
git tag v3.1.0
tar -czf seed-v3.1.0.tar.gz v3/
```

### 2. Обновление на продакшн
```bash
# Бэкап текущей версии
./deploy.sh stop
cp -r v3/ v3.backup.$(date +%Y%m%d)

# Развертывание новой версии
tar -xzf seed-v3.1.0.tar.gz
./deploy.sh offline-build
./deploy.sh start

# Проверка
./deploy.sh status
```

### 3. Откат при проблемах
```bash
# Быстрый откат к предыдущей версии
./deploy.sh stop
rm -rf v3/
mv v3.backup.20241220/ v3/
./deploy.sh start
```