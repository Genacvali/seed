#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== SEED v6 start =="

# --- env ---
if [[ ! -f "configs/seed.env" ]]; then
  echo "⚠️  configs/seed.env not found. Creating from example…"
  # починить CRLF, если есть
  [[ -f "configs/seed.env.example" ]] && sed -i 's/\r$//' configs/seed.env.example || true
  cp -f configs/seed.env.example configs/seed.env
  echo "➡️  Edit configs/seed.env and re-run."
  exit 1
fi

# убрать CRLF на всякий случай
sed -i 's/\r$//' configs/seed.env || true
set -a; . configs/seed.env; set +a

HOSTNAME_CMD="$(hostname -f 2>/dev/null || hostname || echo localhost)"
BASE_URL="http://$HOSTNAME_CMD:${LISTEN_PORT:-8080}"

# --- optional: autostart RabbitMQ in Docker (как в v5) ---
if [[ "${RABBIT_ENABLE:-0}" == "1" && "${RABBIT_AUTOSTART:-0}" == "1" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "❌ Docker not found, set RABBIT_AUTOSTART=0 or install docker"
    exit 1
  fi
  NAME="${RABBIT_CONTAINER:-seed-rabbitmq}"
  IMG="${RABBIT_IMAGE:-rabbitmq:3.13-management}"
  AMQP_PORT="${RABBIT_PORT_AMQP:-5672}"
  UI_PORT="${RABBIT_PORT_UI:-15672}"

  if ! docker ps --format '{{.Names}}' | grep -q "^${NAME}$"; then
    echo "🐰 Starting RabbitMQ container ${NAME}…"
    docker run -d --restart unless-stopped \
      --name "$NAME" \
      -e RABBITMQ_DEFAULT_USER="${RABBIT_USER:-seed}" \
      -e RABBITMQ_DEFAULT_PASS="${RABBIT_PASS:-seedpass}" \
      -p "${AMQP_PORT}:5672" -p "${UI_PORT}:15672" \
      "$IMG" >/dev/null
  else
    echo "🐰 RabbitMQ container already running"
  fi

  echo -n "⏳ Waiting RabbitMQ UI on http://localhost:${UI_PORT} "
  for i in {1..60}; do
    if curl -fsS "http://localhost:${UI_PORT}" >/dev/null 2>&1; then echo "✅"; break; fi
    [[ $i -eq 60 ]] && { echo "❌ timeout"; exit 1; }
    sleep 2; echo -n "."
  done
elif [[ "${RABBIT_ENABLE:-0}" == "1" ]]; then
  echo "🐰 RabbitMQ consumer enabled (external): ${RABBIT_USER:-seed}@${RABBIT_HOST:-localhost}:${RABBIT_PORT:-5672}/${RABBIT_VHOST:-/} q=${RABBIT_QUEUE:-seed-inbox}"
else
  echo "🐰 RabbitMQ consumer disabled (RABBIT_ENABLE=0)"
fi

# --- start HTTP agent ---
mkdir -p logs
if pgrep -f "python3.*seed-agent.py" >/dev/null; then
  echo "ℹ️  HTTP already running"
else
  nohup python3 seed-agent.py > logs/agent.log 2>&1 &
  echo $! > logs/agent.pid
fi

# --- wait HTTP ready ---
echo -n "⏳ Waiting HTTP ${BASE_URL}/health "
for i in {1..30}; do
  if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then echo "✅"; break; fi
  [[ $i -eq 30 ]] && { echo "❌ timeout (see logs/agent.log)"; exit 1; }
  sleep 1; echo -n "."
done

echo "== OK =="
echo "Health:      ${BASE_URL}/health"
echo "Test (POST): ${BASE_URL}/test"
echo "Alert hook:  ${BASE_URL}/alertmanager"
if [[ "${RABBIT_ENABLE:-0}" == "1" ]]; then
  if [[ "${RABBIT_AUTOSTART:-0}" == "1" ]]; then
    echo "Rabbit UI:   http://$HOSTNAME_CMD:${RABBIT_PORT_UI:-15672}  (user: ${RABBIT_USER:-seed})"
  else
    echo "Rabbit:      ${RABBIT_HOST:-localhost}:${RABBIT_PORT:-5672} vhost=${RABBIT_VHOST:-/} q=${RABBIT_QUEUE:-seed-inbox}"
  fi
fi

echo ""
echo "Quick cmds:"
echo "  curl ${BASE_URL}/health | jq ."
echo "  curl -X POST ${BASE_URL}/test -H 'Content-Type: application/json' -d '{\"alertname\":\"Test\", \"instance\":\"${HOSTNAME_CMD}\"}'"
