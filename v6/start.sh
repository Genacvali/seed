#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== SEED v6 start =="

# env
if [[ -f "configs/seed.env" ]]; then
  set -a; source configs/seed.env; set +a
elif [[ -f "configs/seed.env.example" ]]; then
  echo "⚠️  configs/seed.env not found, using example (edit then restart)"
  set -a; source configs/seed.env.example; set +a
fi

# venv
if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
  . .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  . .venv/bin/activate
fi

# logs
mkdir -p logs

# app (HTTP)
if pgrep -f "uvicorn app:app" >/dev/null; then
  echo "HTTP already running"
else
  nohup uvicorn app:app --host "${LISTEN_HOST:-0.0.0.0}" --port "${LISTEN_PORT:-8080}" \
    > logs/http.log 2>&1 & echo $! > app.pid
  echo "HTTP started: PID $(cat app.pid)"
fi

# agent (RabbitMQ) — опционально
if [[ "${RABBIT_ENABLE:-0}" == "1" ]]; then
  if pgrep -f "python3 agent.py" >/dev/null; then
    echo "Agent already running"
  else
    nohup python3 agent.py > logs/agent.log 2>&1 & echo $! > agent.pid
    echo "Agent started: PID $(cat agent.pid)"
  fi
else
  echo "RabbitMQ agent disabled (RABBIT_ENABLE=0)"
fi

echo "== OK =="
echo "Health:      http://localhost:${LISTEN_PORT:-8080}/health"
echo "Test (POST): http://localhost:${LISTEN_PORT:-8080}/test"
echo "Webhook:     http://localhost:${LISTEN_PORT:-8080}/alertmanager"