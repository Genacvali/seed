#!/usr/bin/env bash
set -euo pipefail

# Простая сборка одного бинарника seed-agent на базе PyInstaller.
# Требования: установлен Python 3 и зависимости из requirements.txt.
#
# Использование:
#   cd v6
#   ./build_binary.sh
#   # готовый бинарь будет в dist/seed-agent
#
# На целевом сервере достаточно:
#   - скопировать бинарь dist/seed-agent
#   - рядом положить каталоги configs/ и static/
#   - запустить: ./seed-agent

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v pyinstaller >/dev/null 2>&1; then
  echo "[i] Устанавливаю PyInstaller (в пользовательский сайт‑пакет)..."
  # Пробуем через python3 -m pip, без нестандартных флагов.
  python3 -m pip install --user pyinstaller || python3 -m pip install pyinstaller
fi

echo "[i] Собираю seed-agent (onefile)..."
# Вызываем через модуль, чтобы не зависеть от PATH (~/.local/bin).
python3 -m PyInstaller \
  --clean \
  --onefile \
  --name seed-agent \
  run_seed_agent.py

echo
echo "[✓] Готово. Бинарник: $ROOT_DIR/dist/seed-agent"
echo "    Скопируй его на сервер вместе с папками configs/ и static/."

