#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== SEED v6 stop =="

# Kill by process signature
if pgrep -f "python3.*seed-agent.py" >/dev/null 2>&1; then
  echo -n "Stopping seed-agent.py… "
  pkill -f "python3.*seed-agent.py" || true
  sleep 1
  if pgrep -f "python3.*seed-agent.py" >/dev/null 2>&1; then
    echo -n "force kill… "
    pkill -9 -f "python3.*seed-agent.py" || true
  fi
  echo "OK"
else
  echo "seed-agent.py not running"
fi

# Clean PID files if any exist
rm -f logs/agent.pid logs/rabbit.pid 2>/dev/null || true

echo "== SEED v6 stopped =="