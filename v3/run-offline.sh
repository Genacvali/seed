#!/bin/bash
# =============================================================================
# SEED Agent - Offline Runner
# Запуск SEED Agent без Docker в изолированной среде
# =============================================================================

echo "🚀 Starting SEED Agent in offline mode..."

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+ и попробуйте снова."
    exit 1
fi

# Переходим в директорию со скриптом
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Создаем виртуальное окружение если его нет
if [ ! -d "venv" ]; then
    echo "📦 Создаем виртуальное окружение..."
    python3 -m venv venv
fi

# Активируем виртуальное окружение
echo "🔧 Активируем виртуальное окружение..."
source venv/bin/activate

# Устанавливаем зависимости если файл requirements.txt изменился
if [ requirements.txt -nt venv/pyvenv.cfg ] || [ ! -f venv/.requirements_installed ]; then
    echo "📚 Устанавливаем зависимости..."
    pip install --no-cache-dir -r requirements.txt
    touch venv/.requirements_installed
fi

# Создаем необходимые директории
mkdir -p logs

# Проверяем конфигурацию
if [ ! -f "seed.yaml" ]; then
    echo "⚠️  Файл seed.yaml не найден. Создайте конфигурацию."
    exit 1
fi

# Запускаем SEED Agent
echo "🌱 Запускаем SEED Agent..."
echo "   🌐 Web UI: http://localhost:8080"
echo "   📊 Logs: ./logs/"
echo "   🛑 Остановка: Ctrl+C"
echo ""

export PYTHONPATH=$PWD
export PYTHONUNBUFFERED=1

python seed-agent.py --mode both --host 0.0.0.0 --port 8080