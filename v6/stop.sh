#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

stop_pidfile () {
  local f="$1"
  if [[ -f "$f" ]]; then
    local pid
    pid=$(cat "$f" || true)
    if [[ -n "${pid:-}" ]] && kill -0 "$pid" 2>/dev/null; then
      kill "$pid" || true
      sleep 1
      if kill -0 "$pid" 2>/dev/null; then kill -9 "$pid" || true; fi
      echo "Stopped $f (PID $pid)"
    fi
    rm -f "$f"
  fi
}

stop_pidfile app.pid
stop_pidfile agent.pid
echo "== SEED v6 stopped =="