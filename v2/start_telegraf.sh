#!/bin/bash

# Загружаем переменные окружения из seed.env
set -a
source seed.env
set +a

# Запускаем Telegraf с конфигом COLLSCAN мониторинга
exec telegraf --config telegraf_mongodb_collscan.conf