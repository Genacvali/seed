#!/bin/bash
# =============================================================================
# SEED Agent - Test Alerts
# Тестовые алерты для проверки LLM и Mattermost
# =============================================================================

SEED_URL="http://localhost:8080"
ALERTMANAGER_URL="$SEED_URL/alert"

echo "🧪 Отправка тестовых алертов в SEED Agent"
echo "URL: $ALERTMANAGER_URL"
echo ""

# =============================================================================
# 1. Критическая ошибка MongoDB - высокая нагрузка
# =============================================================================
echo "🔥 1. MongoDB High CPU Usage"
curl -X POST "$ALERTMANAGER_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "MongoDBHighCPU",
          "instance": "mongodb-prod-01:27017",
          "job": "mongodb",
          "severity": "critical",
          "service": "mongodb",
          "environment": "production",
          "datacenter": "msk-dc1"
        },
        "annotations": {
          "summary": "MongoDB CPU usage is critically high",
          "description": "MongoDB instance mongodb-prod-01:27017 has been using >90% CPU for more than 5 minutes. Current usage: 95.2%",
          "runbook_url": "https://wiki.company.com/mongodb/high-cpu",
          "dashboard_url": "https://grafana.company.com/d/mongodb/mongodb-overview?var-instance=mongodb-prod-01"
        },
        "startsAt": "'$(date -Iseconds)'",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "https://prometheus.company.com/graph?g0.expr=rate(mongodb_sys_cpu_user_ms%5B5m%5D)%20%2B%20rate(mongodb_sys_cpu_kernel_ms%5B5m%5D)%20%3E%200.9",
        "fingerprint": "mongodb-high-cpu-prod-01"
      }
    ],
    "groupKey": "mongodb-performance",
    "receiver": "seed-webhook",
    "status": "firing",
    "externalURL": "https://alertmanager.company.com",
    "version": "4",
    "groupLabels": {
      "service": "mongodb"
    }
  }'

echo -e "\n\n"
sleep 2

# =============================================================================
# 2. Дисковое пространство заканчивается
# =============================================================================
echo "💾 2. Disk Space Low Warning"
curl -X POST "$ALERTMANAGER_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "DiskSpaceLow",
          "instance": "app-server-03",
          "job": "node-exporter",
          "severity": "warning",
          "device": "/dev/sda1",
          "mountpoint": "/var/lib/mongodb",
          "environment": "production",
          "team": "infrastructure"
        },
        "annotations": {
          "summary": "Disk space is running low on app-server-03",
          "description": "Filesystem /var/lib/mongodb on app-server-03 has only 12.3% space remaining (8.2GB free of 67GB total). Consider cleanup or disk expansion.",
          "impact": "MongoDB may stop working if disk becomes full",
          "suggested_action": "Clean up old logs, compact collections, or add more disk space"
        },
        "startsAt": "'$(date -Iseconds)'",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "https://prometheus.company.com/graph?g0.expr=(1%20-%20node_filesystem_free_bytes%2Fnode_filesystem_size_bytes)%20%3E%200.85",
        "fingerprint": "disk-space-low-app-server-03"
      }
    ],
    "groupKey": "disk-space",
    "receiver": "seed-webhook", 
    "status": "firing",
    "externalURL": "https://alertmanager.company.com",
    "version": "4"
  }'

echo -e "\n\n"
sleep 2

# =============================================================================
# 3. Высокое количество медленных запросов
# =============================================================================
echo "🐌 3. MongoDB Slow Queries"
curl -X POST "$ALERTMANAGER_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "MongoDBSlowQueries",
          "instance": "mongodb-prod-02:27017",
          "job": "mongodb",
          "severity": "warning",
          "database": "application_db",
          "collection": "user_sessions",
          "environment": "production"
        },
        "annotations": {
          "summary": "High number of slow queries detected on MongoDB",
          "description": "MongoDB instance mongodb-prod-02:27017 is experiencing 47 slow queries per minute (>1000ms). Collection user_sessions shows most activity.",
          "query_example": "db.user_sessions.find({created_at: {$gte: ISODate()}}).sort({created_at: -1})",
          "recommendation": "Consider adding index on created_at field or optimize query patterns",
          "ops_impact": "Response times may be degraded for user authentication"
        },
        "startsAt": "'$(date -Iseconds)'",
        "endsAt": "0001-01-01T00:00:00Z", 
        "generatorURL": "https://prometheus.company.com/graph?g0.expr=rate(mongodb_op_counters_query_total%5B5m%5D)%20%3E%2040",
        "fingerprint": "mongodb-slow-queries-prod-02"
      }
    ],
    "groupKey": "mongodb-performance",
    "receiver": "seed-webhook",
    "status": "firing",
    "externalURL": "https://alertmanager.company.com",
    "version": "4"
  }'

echo -e "\n\n"
sleep 2

# =============================================================================
# 4. Сервис недоступен (resolved alert)
# =============================================================================
echo "✅ 4. Service Recovery (Resolved)"
curl -X POST "$ALERTMANAGER_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "resolved",
        "labels": {
          "alertname": "ServiceDown",
          "instance": "api-gateway-01:8080",
          "job": "api-gateway",
          "severity": "critical",
          "service": "api-gateway",
          "environment": "production",
          "team": "backend"
        },
        "annotations": {
          "summary": "API Gateway service has recovered",
          "description": "API Gateway api-gateway-01:8080 was down for 3 minutes but has now recovered and is responding normally.",
          "downtime_duration": "3m 24s",
          "recovery_time": "'$(date)'",
          "root_cause": "Memory exhaustion due to connection leak - fixed by service restart"
        },
        "startsAt": "'$(date -d '5 minutes ago' -Iseconds)'",
        "endsAt": "'$(date -Iseconds)'",
        "generatorURL": "https://prometheus.company.com/graph?g0.expr=up%7Bjob%3D%22api-gateway%22%7D%20%3D%3D%200",
        "fingerprint": "service-down-api-gateway-01"
      }
    ],
    "groupKey": "service-availability",
    "receiver": "seed-webhook",
    "status": "resolved", 
    "externalURL": "https://alertmanager.company.com",
    "version": "4"
  }'

echo -e "\n\n"
sleep 2

# =============================================================================
# 5. Высокая нагрузка на Redis
# =============================================================================
echo "🔴 5. Redis High Memory Usage"
curl -X POST "$ALERTMANAGER_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [
      {
        "status": "firing",
        "labels": {
          "alertname": "RedisHighMemory",
          "instance": "redis-cache-01:6379",
          "job": "redis",
          "severity": "warning", 
          "service": "redis",
          "redis_role": "master",
          "environment": "production",
          "cluster": "cache-cluster-1"
        },
        "annotations": {
          "summary": "Redis memory usage is high",
          "description": "Redis instance redis-cache-01:6379 is using 89.4% of available memory (7.15GB of 8GB). Memory usage has been growing steadily over past 2 hours.",
          "current_memory": "7.15GB",
          "max_memory": "8.00GB", 
          "memory_policy": "allkeys-lru",
          "keys_count": "2,847,392",
          "evicted_keys_rate": "127/sec",
          "suggested_action": "Consider scaling up memory or reviewing key TTL policies"
        },
        "startsAt": "'$(date -Iseconds)'",
        "endsAt": "0001-01-01T00:00:00Z",
        "generatorURL": "https://prometheus.company.com/graph?g0.expr=redis_memory_used_bytes%2Fredis_memory_max_bytes%20%3E%200.85",
        "fingerprint": "redis-high-memory-cache-01"
      }
    ],
    "groupKey": "redis-performance",
    "receiver": "seed-webhook",
    "status": "firing",
    "externalURL": "https://alertmanager.company.com", 
    "version": "4"
  }'

echo -e "\n\n"
sleep 2

echo "✅ Все тестовые алерты отправлены!"
echo ""
echo "📊 Проверьте:"
echo "   curl http://localhost:8080/stats"
echo "   ./deploy.sh logs"
echo "   Mattermost канал для уведомлений"