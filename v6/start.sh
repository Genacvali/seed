#!/usr/bin/env bash
# == SEED v6.1 start ==
set -Eeuo pipefail

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

CFG_DIR="$BASE_DIR/configs"
LOG_DIR="$BASE_DIR/logs"
mkdir -p "$CFG_DIR" "$LOG_DIR"

ENV_MAIN="$CFG_DIR/seed.env"
ENV_SECR="$CFG_DIR/secrets.env"
HTTP_LOG="$LOG_DIR/agent.log"

# ---------- helpers ----------
color() { # $1=code $2..=text
  printf "\033[%sm%s\033[0m" "$1" "${*:2}"
}
ok()   { color "32;1" "OK"; }
warn() { color "33;1" "WARN"; }
err()  { color "31;1" "ERROR"; }
info() { color "36;1" "$*"; echo; }

load_env() {
  set -a
  [[ -f "$ENV_MAIN" ]] && source "$ENV_MAIN"
  [[ -f "$ENV_SECR" ]] && source "$ENV_SECR"
  set +a
}

save_secret() { # save_secret VAR value
  local var="$1" val="$2"
  touch "$ENV_SECR" && chmod 600 "$ENV_SECR"
  if grep -qE "^${var}=" "$ENV_SECR" 2>/dev/null; then
    sed -i "s|^${var}=.*$|${var}=${val//|/\\|}|" "$ENV_SECR"
  else
    echo "${var}=${val}" >> "$ENV_SECR"
  fi
}

prompt_secret() { # prompt_secret VAR "Prompt" [silent]
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

need_cmd() { command -v "$1" >/dev/null 2>&1 || { echo "$(err) missing: $1"; exit 1; }; }

# ---------- banner ----------
echo "🌌 ================================"
echo "🌌 SEED Agent v6.1 - Starting..."
echo "🌌 ================================"
echo

# ---------- sanity / CRLF fix ----------
for envfile in "$ENV_MAIN" "$ENV_SECR"; do
  if [[ -f "$envfile" ]] && grep -q $'\r' "$envfile" 2>/dev/null; then
    echo "$(warn) $envfile has CRLF. Fixing..."
    sed -i 's/\r$//' "$envfile"
  fi
done

# ---------- load env ----------
if [[ ! -f "$ENV_MAIN" ]]; then
  echo "$(warn) $ENV_MAIN not found. Copying example → seed.env"
  if [[ -f "$CFG_DIR/seed.env.example" ]]; then
    cp -f "$CFG_DIR/seed.env.example" "$ENV_MAIN"
    sed -i 's/\r$//' "$ENV_MAIN" || true
    echo "  Edit $ENV_MAIN and re-run, or continue to be prompted for secrets."
  else
    echo "$(err) configs/seed.env.example is missing. Create configs/seed.env manually."
  fi
fi

load_env

# ---------- http config ----------
export LISTEN_HOST="${LISTEN_HOST:-0.0.0.0}"
export LISTEN_PORT="${LISTEN_PORT:-8080}"
HOSTNAME_FQDN="$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo localhost)"
HEALTH_URL="http://${HOSTNAME_FQDN}:${LISTEN_PORT}/health"

# ---------- config summary ----------
echo "📋 Configuration:"
echo "   Listen: ${LISTEN_HOST}:${LISTEN_PORT}"

# ---------- rabbit (optional) ----------
export RABBIT_ENABLE="${RABBIT_ENABLE:-0}"
if [[ "$RABBIT_ENABLE" == "1" ]]; then
  export RABBIT_HOST="${RABBIT_HOST:-localhost}"
  export RABBIT_PORT="${RABBIT_PORT:-5672}"
  export RABBIT_SSL="${RABBIT_SSL:-0}"
  prompt_secret RABBIT_USER "RabbitMQ user [seed]"; [[ -z "${RABBIT_USER}" ]] && RABBIT_USER="seed"
  prompt_secret RABBIT_PASS "RabbitMQ password" silent
  export RABBIT_VHOST="${RABBIT_VHOST:-/}"
  export RABBIT_QUEUE="${RABBIT_QUEUE:-seed-inbox}"
  echo "   RabbitMQ: ✅ ${RABBIT_USER}@${RABBIT_HOST}:${RABBIT_PORT}${RABBIT_VHOST} q=${RABBIT_QUEUE}"
else
  echo "   RabbitMQ: ⏸️  disabled"
fi

# ---------- LLM (optional) ----------
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
  echo "   LLM: ✅ GigaChat (${GIGACHAT_MODEL})"
else
  echo "   LLM: ⏸️  disabled"
fi

# ---------- Mattermost ----------
if [[ -z "${MM_WEBHOOK:-}" ]]; then
  prompt_secret MM_WEBHOOK "Mattermost webhook URL (empty to skip)"
fi
export MM_VERIFY_SSL="${MM_VERIFY_SSL:-0}"
echo "   Mattermost: $( [[ -n "${MM_WEBHOOK:-}" ]] && echo "✅ webhook configured" || echo "❌ not configured" )"

# ---------- deps check ----------
need_cmd python3
need_cmd curl

echo
echo "🚀 Starting services..."

# ---------- start agent ----------
: > "$HTTP_LOG"
if pgrep -f "python3.*seed-agent.py" >/dev/null 2>&1; then
  echo "   📤 HTTP server: already running"
else
  echo -n "   📤 HTTP server: starting... "
  nohup python3 "$BASE_DIR/seed-agent.py" >>"$HTTP_LOG" 2>&1 &
  sleep 1
  echo "✅"
fi

# ---------- wait health ----------
echo -n "   🏥 Health check: ${HEALTH_URL} "
for i in {1..30}; do
  if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
    echo "✅"
    break
  fi
  echo -n "."
  sleep 0.5
  if (( i == 30 )); then
    echo " ❌ timeout"
    echo
    echo "❌ Failed to start. Last 15 lines of $HTTP_LOG:"
    tail -n 15 "$HTTP_LOG" 2>/dev/null || echo "No log file"
    exit 1
  fi
done

# ---------- success banner ----------
echo
echo "🎉 ================================"
echo "🎉 SEED Agent v6.1 - Ready!"
echo "🎉 ================================"
echo
echo "📡 API Endpoints:"
echo "   Health:     $HEALTH_URL"
echo "   Webhook:    http://${HOSTNAME_FQDN}:${LISTEN_PORT}/alertmanager"
echo "   Test:       http://${HOSTNAME_FQDN}:${LISTEN_PORT}/test"
echo
echo "📋 Logs & Management:"
echo "   Agent log:  tail -f $HTTP_LOG"
echo "   Stop:       ./stop.sh"
echo "   Restart:    ./stop.sh && ./start.sh"
echo
echo "🔧 Quick test commands:"
echo "   curl $HEALTH_URL | jq ."
echo "   curl -X POST $HEALTH_URL/../test"
echo
