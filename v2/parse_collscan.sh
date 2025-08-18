#!/bin/bash

# Парсинг COLLSCAN событий из MongoDB логов для Telegraf

LOG_FILE="/data/logs/mongod.log"

if [[ ! -f "$LOG_FILE" ]]; then
    echo "Log file not found: $LOG_FILE"
    exit 1
fi

# Получаем последние 100 строк, фильтруем COLLSCAN, берем последние 5
tail -n 100 "$LOG_FILE" | grep "COLLSCAN" | tail -n 5 | while IFS= read -r line; do
    # Парсим JSON и извлекаем нужные поля
    ns=$(echo "$line" | jq -r '.attr.ns // "unknown"')
    duration=$(echo "$line" | jq -r '.attr.durationMillis // 0')
    docs_examined=$(echo "$line" | jq -r '.attr.docsExamined // 0')
    keys_examined=$(echo "$line" | jq -r '.attr.keysExamined // 0')
    nreturned=$(echo "$line" | jq -r '.attr.nreturned // 0')
    
    # Проверяем что данные валидны
    if [[ "$ns" != "unknown" && "$ns" != "null" && "$duration" != "null" ]]; then
        # Выводим в InfluxDB line protocol формате
        echo "collscan,namespace=$ns,alert_type=collscan_detected,severity=warning durationMillis=${duration}i,docsExamined=${docs_examined}i,keysExamined=${keys_examined}i,nreturned=${nreturned}i"
    fi
done