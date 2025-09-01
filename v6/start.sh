#!/usr/bin/env bash
# == SEED v6 start ==
set -Eeuo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

CFG_DIR="$BASE_DIR/configs"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$CFG_DIR" "$LOG_DIR"

ENV_MAIN="$CFG_DIR/seed.env"
ENV_SECR="$CFG_DIR/secrets.env"

touch "$ENV_SECR" && chmod 600 "$ENV_SECR"

load_env() {
  set -a
  [[ -f "$ENV_MAIN" ]] && source "$ENV_MAIN"
  [[ -f "$ENV_SECR" ]] && source "$ENV_SECR"
  set +a
}

save_secret() {
  # save_secret VAR value
  local var="$1" val="$2"
  # do not echo secrets to stdout
  grep -qE "^${var}=" "$ENV_SECR" 2>/dev/null \
    && sed -i "s|^${var}=.*$|${var}=${val//|/\\|}|" "$ENV_SECR" \
    || echo "${var}=${val}" >> "$ENV_SECR"
}

prompt_secret() {
  # prompt_secret VAR "Prompt" [silent]
  local var="$1" prompt="$2" silent="${3:-}"
  local curr="${!var:-}"
  if [[ -z "$curr" ]]; then
    if [[ -n "$silent" ]]; then
      read -r -s -p "$prompt: " curr; echo
    else
      read -r -p "$prompt: " curr
    fi
  fi
  export "$var"="$curr"
  [[ "${WRITE_SECRETS:-0}" == "1" ]] && save_secret "$var" "$curr"
}

echo "== SEED v6 start =="

# 0) Первичная env
if [[ ! -f "$ENV_MAIN" ]]; then
  echo "⚠️  $ENV_MAIN not found, create it from seed.env.example and edit."
fi
load_env

# 1) HTTP
export LISTEN_HOST="${LISTEN_HOST:-0.0.0.0}"
export LISTEN_PORT="${LISTEN_PORT:-8080}"

# 2) RabbitMQ (optional)
export RABBIT_ENABLE="${RABBIT_ENABLE:-0}"
if [[ "$RABBIT_ENABLE" == "1" ]]; then
  export RABBIT_HOST="${RABBIT_HOST:-localhost}"
  export RABBIT_PORT="${RABBIT_PORT:-5672}"
  export RABBIT_SSL="${RABBIT_SSL:-0}"
  prompt_secret RABBIT_USER "RabbitMQ Username [seed]"; [[ -z "$RABBIT_USER" ]] && RABBIT_USER="seed"
  prompt_secret RABBIT_PASS "RabbitMQ Password" silent
  export RABBIT_VHOST="${RABBIT_VHOST:-/}"
  export RABBIT_QUEUE="${RABBIT_QUEUE:-seed-inbox}"
  echo "🐰 RabbitMQ consumer enabled: ${RABBIT_USER}@${RABBIT_HOST}:${RABBIT_PORT}${RABBIT_VHOST} q=${RABBIT_QUEUE}"
else
  echo "RabbitMQ agent disabled (RABBIT_ENABLE=0)"
fi

# 3) Mattermost
prompt_secret MM_WEBHOOK "Mattermost webhook URL (leave empty to skip)"
export MM_VERIFY_SSL="${MM_VERIFY_SSL:-0}"

# 4) LLM (optional)
export USE_LLM="${USE_LLM:-0}"
if [[ "$USE_LLM" == "1" ]]; then
  prompt_secret GIGACHAT_CLIENT_ID "GigaChat CLIENT_ID"
  prompt_secret GIGACHAT_CLIENT_SECRET "GigaChat CLIENT_SECRET" silent
  export GIGACHAT_SCOPE="${GIGACHAT_SCOPE:-GIGACHAT_API_PERS}"
  export GIGACHAT_OAUTH_URL="${GIGACHAT_OAUTH_URL:-https://ngw.devices.sberbank.ru:9443/api/v2/oauth}"
  export GIGACHAT_API_URL="${GIGACHAT_API_URL:-https://gigachat.devices.sberbank.ru/api/v1/chat/completions}"
  export GIGACHAT_MODEL="${GIGACHAT_MODEL:-GigaChat-2}"
  export GIGACHAT_VERIFY_SSL="${GIGACHAT_VERIFY_SSL:-0}"
  export GIGACHAT_TOKEN_CACHE="${GIGACHAT_TOKEN_CACHE:-/tmp/gigachat_token.json}"
fi

# 5) Запуск HTTP-агента
HTTP_LOG="$LOG_DIR/agent.log"
: > "$HTTP_LOG"

if pgrep -f "python3 seed-http.py" >/dev/null 2>&1; then
  echo "ℹ️  HTTP already running"
else
  nohup python3 "$BASE_DIR/seed-http.py" >>"$HTTP_LOG" 2>&1 &
  HTTP_PID=$!
  echo "HTTP started: PID $HTTP_PID"
fi

# 6) Запуск Rabbit consumer (если включен)
if [[ "$RABBIT_ENABLE" == "1" ]]; then
  RAB_LOG="$LOG_DIR/rabbit.log"
  : > "$RAB_LOG"
  if pgrep -f "python3 seed-rabbit.py" >/dev/null 2>&1; then
    echo "ℹ️  Rabbit consumer already running"
  else
    nohup python3 "$BASE_DIR/seed-rabbit.py" >>"$RAB_LOG" 2>&1 &
    RAB_PID=$!
    echo "Rabbit started: PID $RAB_PID"
  fi
fi

# 7) Ожидание health
HEALTH_URL="http://$(hostname -f 2>/dev/null || echo localhost):${LISTEN_PORT}/health"
echo -n "⏳ Waiting HTTP $HEALTH_URL "
for _ in {1..30}; do
  if curl -sS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "✅"
    break
  fi
  echo -n "."
  sleep 1
done

echo "== OK =="
echo "Health:      $HEALTH_URL"
echo "Test (POST): http://$(hostname -f):${LISTEN_PORT}/test"
echo "Webhook:     http://$(hostname -f):${LISTEN_PORT}/alertmanager"
