#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PID_FILE="logs/agent.pid"
if [[ -f "$PID_FILE" ]]; then
  PID="$(cat "$PID_FILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" 2>/dev/null; then
    echo "Stopping HTTP agent (pid $PID)…"
    kill "$PID" || true
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
      echo "Force kill…"
      kill -9 "$PID" || true
    fi
  fi
  rm -f "$PID_FILE"
else
  # на всякий случаи прибить по подписи
  pkill -f "python3.*seed-agent.py" 2>/dev/null || true
fi

# Останавливать контейнер RabbitMQ — по желанию:
if [[ "${STOP_RABBIT_CONTAINER:-0}" == "1" ]]; then
  NAME="${RABBIT_CONTAINER:-seed-rabbitmq}"
  docker rm -f "$NAME" 2>/dev/null || true
fi

echo "Stopped."