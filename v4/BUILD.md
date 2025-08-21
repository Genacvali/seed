# SEED Agent v4 - Сборка и Развертывание

## Быстрый старт

```bash
cd v4/
./start.sh    # Запуск всего стека
./stop.sh     # Остановка всего стека
```

## Сборка в бинарник

### Автоматическая сборка
```bash
./build-agent.sh
```

### Ручная сборка
```bash
pip3 install -r requirements.txt pyinstaller
pyinstaller --onefile --name=seed-agent \
    --add-data="seed.yaml:." \
    --add-data="core:core" \
    --add-data="fetchers:fetchers" \
    --add-data="plugins.py:." \
    seed-agent.py
```

Результат: `dist/seed-agent`

## Установка как системный сервис

### Linux (systemd)

1. Создать сервис:
```bash
sudo tee /etc/systemd/system/seed-agent.service << EOF
[Unit]
Description=SEED Agent v4 - Monitoring System
After=network.target docker.service
Requires=docker.service

[Service]
Type=forking
User=seed
Group=seed
WorkingDirectory=/opt/seed-agent
ExecStart=/opt/seed-agent/start.sh
ExecStop=/opt/seed-agent/stop.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

2. Установить:
```bash
sudo mkdir -p /opt/seed-agent
sudo cp -r v4/* /opt/seed-agent/
sudo useradd -r seed
sudo chown -R seed:seed /opt/seed-agent
sudo systemctl enable seed-agent
sudo systemctl start seed-agent
```

### Windows (service)

1. Установить как службу с nssm:
```cmd
nssm install "SEED Agent v4" "C:\seed-agent\dist\seed-agent.exe"
nssm set "SEED Agent v4" AppDirectory "C:\seed-agent"
nssm set "SEED Agent v4" AppParameters "--config seed.yaml"
nssm start "SEED Agent v4"
```

## Docker образы для оффлайн развертывания

### Экспорт образов
```bash
./export-images.sh  # Создает tar архивы
```

### Импорт образов
```bash
./load-images.sh    # Загружает tar архивы
```

### Ручной экспорт/импорт
```bash
# Экспорт
docker save redis:7.2-alpine > redis-7.2-alpine.tar
docker save rabbitmq:3.13-management > rabbitmq-3.13-management.tar

# Импорт
docker load < redis-7.2-alpine.tar  
docker load < rabbitmq-3.13-management.tar
```

## Структура развертывания

```
seed-agent/
├── dist/seed-agent        # Бинарный файл
├── seed.yaml             # Конфигурация
├── docker-compose.yml    # Инфраструктура
├── start.sh             # Скрипт запуска
├── stop.sh              # Скрипт остановки
└── *.tar                # Docker образы
```

## Проверка работы

```bash
# Статус сервисов
curl http://localhost:8080/health

# Тест алерта
curl -X POST http://localhost:8080/alert \
  -H 'Content-Type: application/json' \
  -d '{"alertname": "Test", "instance": "localhost"}'

# RabbitMQ UI
# http://localhost:15672 (admin/admin)
```

## Производительность

- **RAM**: ~100MB (агент) + 450MB (Redis+RabbitMQ)
- **CPU**: <1% в idle
- **Disk**: ~50MB (бинарник) + 200MB (образы)
- **Пропускная способность**: >1000 алертов/сек

## Конфигурация

Все настройки в `seed.yaml`. Основные параметры:

```yaml
system:
  agent:
    bind_host: "0.0.0.0"
    bind_port: 8080

infrastructure:
  rabbitmq:
    host: "127.0.0.1"
    username: "admin" 
    password: "admin"
    
  redis:
    host: "127.0.0.1"
    port: 6379

notifications:
  mattermost:
    enabled: true
    webhook_url: "https://your-mattermost/hooks/..."
```

## Мониторинг

- **Health**: GET /health
- **Metrics**: GET /metrics (Prometheus format)  
- **Config**: GET /config
- **Logs**: tail -f seed-agent.log