#!/bin/bash
# =============================================================================
# SEED Agent Startup Script
# =============================================================================

echo "🌱 Starting SEED Agent..."

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден"
    exit 1
fi

# Создаем виртуальное окружение если нужно
if [ ! -d "venv" ]; then
    echo "📦 Создаем виртуальное окружение..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем зависимости
if [ requirements.txt -nt venv/pyvenv.cfg ] || [ ! -f venv/.deps_installed ]; then
    echo "📚 Устанавливаем зависимости..."
    pip install --no-cache-dir -r requirements.txt
    touch venv/.deps_installed
fi

# Создаем директории
mkdir -p logs

# Проверяем конфигурацию
if [ ! -f "seed.yaml" ]; then
    echo "❌ Файл seed.yaml не найден"
    exit 1
fi

# Запускаем
echo "🚀 Запускаем SEED Agent на http://localhost:8080"
export PYTHONPATH=$PWD
python seed-agent.py --mode both --host 0.0.0.0 --port 8080