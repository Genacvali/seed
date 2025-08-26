# Docker Network Migration for SEED Agent

## Проблема
Конфликт сетей Docker с production сетью `172.20.15.0/24`:
- Текущие Docker сети: `172.17.0.0/16`, `172.18.0.0/16` 
- Production сеть: `172.20.15.0/24`
- Требуется изоляция и использование `/data` для данных Docker

## Решение

### 1. Новая сетевая конфигурация
```bash
# Новые сети Docker (без пересечений)
Bridge network: 172.31.255.1/24
Address pools: 172.31.0.0/16 (размер /24)
```

### 2. Настройка прокси
```bash
HTTP_PROXY: proxy.sberdevices.ru:3128
NO_PROXY: *.sberdevices.ru,vcd.sbercloud.ru,172.16.*,api.cloud.gcorelabs.com*,api.gcdn.co*,gitlab.sberdevices.ru:5050
```

### 3. Директория данных
```bash
Docker root: /data/docker
Logs: /data/logs  
Service data: /data/redis, /data/rabbitmq
```

## Инструкции по применению

### На сервере production (RedHat)
```bash
# 1. Скопировать файлы конфигурации
scp docker-daemon.json setup-docker-config.sh user@server:/tmp/

# 2. На сервере выполнить настройку
sudo /tmp/setup-docker-config.sh

# 3. Проверить новые сети
ip route
# Должно показать: 172.31.x.x вместо 172.17.x.x и 172.18.x.x

# 4. Запустить SEED Agent
cd v4/ && ./start.sh
# или  
cd v5/ && ./start.sh
```

### Проверка результата
```bash
# Проверить Docker networks
docker network ls
docker network inspect bridge

# Проверить что нет конфликтов с 172.20.15.0/24
ip route | grep 172

# Проверить директорию данных
ls -la /data/
df -h /data/

# Проверить размеры логов
ls -lh /data/docker/containers/*/container.log
```

## Откат (если что-то пошло не так)

```bash
# Остановить Docker
sudo systemctl stop docker

# Восстановить старую конфигурацию
sudo rm /etc/docker/daemon.json
sudo rm -rf /etc/systemd/system/docker.service.d/override.conf

# Восстановить данные (если были скопированы)
sudo mv /data/docker-backup /var/lib/docker

# Перезапустить
sudo systemctl daemon-reload
sudo systemctl start docker
```

## Результаты после миграции

✅ **Сетевые конфликты устранены**
- Старые сети: `172.17.0.0/16`, `172.18.0.0/16` ❌
- Новые сети: `172.31.0.0/16` ✅
- Production: `172.20.15.0/24` (без конфликтов) ✅

✅ **Директория данных оптимизирована**
- Docker данные: `/data/docker`
- Логи контейнеров: `/data/docker/containers/`
- Service данные: `/data/redis`, `/data/rabbitmq`

✅ **Прокси настроен для корпоративной сети**
- Прокси: `proxy.sberdevices.ru:3128`
- Исключения для внутренних сервисов

## Мониторинг после применения

```bash
# Проверить что SEED Agent работает
curl http://localhost:8080/health

# Проверить использование места
du -sh /data/*

# Проверить логи
tail -f /data/docker/containers/*/container.log | grep ERROR
```