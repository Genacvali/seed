#!/bin/bash
# SEED Agent v5 - Smoke Test Script
# Проверяет что LLM включен и Mattermost работает

set -euo pipefail

HOST=${1:-$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "localhost")}
PORT=${2:-8080}
BASE_URL="http://${HOST}:${PORT}"

echo "🧪 SEED Agent v5 Smoke Test"
echo "Host: $HOST:$PORT"
echo "=============================="
echo

# 1. Health Check
echo "1️⃣ Checking health..."
HEALTH=$(curl -s "${BASE_URL}/health" | jq -r '.services.llm // false')
if [[ "$HEALTH" == "true" ]]; then
    echo "✅ LLM Service: ENABLED"
else
    echo "❌ LLM Service: DISABLED"
    echo "   Check seed.env file and GigaChat credentials"
fi
echo

# 2. LLM Self-Test
echo "2️⃣ LLM Self-Test..."
SELFTEST=$(curl -s "${BASE_URL}/llm/selftest")
echo "$SELFTEST" | jq .

# Check critical vars
CLIENT_ID_OK=$(echo "$SELFTEST" | jq -r '.env_vars.GIGACHAT_CLIENT_ID.present // false')
CLIENT_SECRET_OK=$(echo "$SELFTEST" | jq -r '.env_vars.GIGACHAT_CLIENT_SECRET.present // false')
OAUTH_URL_OK=$(echo "$SELFTEST" | jq -r '.env_vars.GIGACHAT_OAUTH_URL.present // false')
API_URL_OK=$(echo "$SELFTEST" | jq -r '.env_vars.GIGACHAT_API_URL.present // false')

if [[ "$CLIENT_ID_OK" == "true" && "$CLIENT_SECRET_OK" == "true" && "$OAUTH_URL_OK" == "true" && "$API_URL_OK" == "true" ]]; then
    echo "✅ All critical GigaChat env vars present"
else
    echo "❌ Missing critical GigaChat env vars:"
    echo "   CLIENT_ID: $CLIENT_ID_OK"
    echo "   CLIENT_SECRET: $CLIENT_SECRET_OK" 
    echo "   OAUTH_URL: $OAUTH_URL_OK"
    echo "   API_URL: $API_URL_OK"
fi
echo

# 3. Config Check
echo "3️⃣ Configuration check..."
CONFIG=$(curl -s "${BASE_URL}/config")
MM_ENABLED=$(echo "$CONFIG" | jq -r '.notifications.mattermost_enabled // false')
LLM_ENABLED=$(echo "$CONFIG" | jq -r '.llm.enabled // false')

echo "LLM enabled: $LLM_ENABLED"
echo "Mattermost enabled: $MM_ENABLED"
echo

# 4. Test Alert
echo "4️⃣ Sending test alert..."
ALERT_RESPONSE=$(curl -s -X POST "${BASE_URL}/alert" \
  -H 'Content-Type: application/json' \
  -d "{\"alerts\":[{\"labels\":{\"alertname\":\"SmokeTest\",\"instance\":\"${HOST}\",\"severity\":\"warning\"},\"annotations\":{\"summary\":\"SEED Agent v5 smoke test\"},\"status\":\"firing\"}]}")

echo "Alert response:"
echo "$ALERT_RESPONSE" | jq .
echo

# 5. Log check
echo "5️⃣ Recent logs check..."
if [[ -f "seed-agent.log" ]]; then
    echo "Last 10 lines from seed-agent.log:"
    tail -10 seed-agent.log | grep -E "(📁|✅|❌|📤|🎉)" || echo "No emoji markers found in recent logs"
else
    echo "⚠️ seed-agent.log not found"
fi
echo

echo "🏁 Smoke test completed!"
echo
echo "💡 Tips:"
echo "   - If LLM disabled: check seed.env file has all GIGACHAT_* vars"
echo "   - If MM not working: check webhook URL and verify_ssl settings"
echo "   - Live logs: tail -f seed-agent.log | grep -E '(📁|✅|❌|📤)'"
echo "   - Dashboard: curl ${BASE_URL}/dashboard | jq ."