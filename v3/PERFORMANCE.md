# SEED Services - Performance Optimization для 2vCPU / 4GB

## 🚀 Применённые оптимизации

### ⚡ Erlang/RabbitMQ
- **Busy-wait отключен**: `+sbwt none +sbwtdcpu none +sbwtdio none`
- **Management в basic mode**: минимум статистики
- **Memory watermark**: 20% от RAM (раннее GC давление)
- **IO/Channel limits**: `io_thread_pool_size=16`, `channel_max=256`
- **Statistics interval**: увеличен до 10s

### 🔴 Redis
- **Memory limit**: 96MB (оптимизировано для throttling)
- **Persistence**: `appendonly=no` (для throttling не критично)
- **Bind**: `0.0.0.0` (доступ из других контейнеров)
- **Eviction**: `allkeys-lru` (автоочистка старых ключей)

## 🔍 Диагностика нагрузки

### Быстрый триаж:
```bash
docker exec seed-services /usr/local/bin/diagnostics.sh
```

### Глубокая диагностика RabbitMQ:
```bash
docker exec seed-services /usr/local/bin/rabbit-diag.sh
```

### Ручные команды:

**CPU топ процессов:**
```bash
docker exec seed-services ps -o pid,comm,%cpu,%mem,rss --sort=-%cpu | head -10
```

**RabbitMQ очереди:**
```bash
docker exec seed-services rabbitmqctl list_queues name messages_ready messages_unacknowledged consumers state
```

**Redis память и эвикции:**
```bash
docker exec seed-services redis-cli INFO memory | grep -E 'used_memory_human|maxmemory_human|mem_fragmentation_ratio'
docker exec seed-services redis-cli INFO stats | grep -E 'evicted_keys|instantaneous_ops_per_sec'
```

## 🚨 Признаки проблем

### RabbitMQ перегружен:
- `beam.smp` потребляет >150% CPU на 2 vCPU
- `messages_unacknowledged` растёт без остановки  
- Высокий `mem_fragmentation_ratio` в memory_breakdown

### Redis перегружен:
- `evicted_keys` постоянно растёт
- `used_memory` = `maxmemory` (постоянные эвикции)
- Высокие `instantaneous_ops_per_sec`

## ⚙️ Дополнительные твики (если проблемы остаются)

### Отключить RabbitMQ Management UI:
```bash
docker exec seed-services rabbitmq-plugins disable rabbitmq_management
# Сэкономит ~50-100MB RAM и 20-30% CPU
```

### Увеличить Redis memory (если много эвикций):
```bash
# В Dockerfile изменить на maxmemory 128mb
```

### Настройки приложения (SEED Agent):
- **Prefetch**: установить `prefetch_count = 20-50`
- **Ack**: подтверждать только после успешной обработки
- **Retry**: использовать exponential backoff (30s → 2m → 10m)
- **Message size**: ограничить до 100KB

## 📊 Ожидаемые метрики после оптимизации

**Нормальное потребление:**
- **beam.smp**: 30-60% CPU (вместо 150-200%)
- **redis-server**: 5-15% CPU  
- **Total RAM**: 200-300MB (вместо 400-500MB)
- **Load Average**: <2.0 на 2 vCPU

**Стабильная работа:**
- Нет перезапусков в `docker logs seed-services`
- `evicted_keys` растёт медленно или не растёт
- `messages_unacknowledged` не накапливается

## 🛠️ Troubleshooting

### Если CPU всё ещё высокий:
1. Проверить размер и частоту сообщений в очередях
2. Убедиться что нет штормов ретраев (DLX loops)
3. Рассмотреть отключение management UI
4. Проверить prefetch_count в коде агента

### Если память заканчивается:
1. Увеличить Redis maxmemory до 128MB
2. Уменьшить TTL ключей throttling  
3. Отключить management UI
4. Проверить утечки в приложении

### Если перезапуски продолжаются:
```bash
# Проверить cgroups limits
docker inspect seed-services | jq '.[0].HostConfig.Memory, .[0].HostConfig.NanoCpus'

# Посмотреть OOM killer в dmesg
dmesg | grep -i "killed process"
```