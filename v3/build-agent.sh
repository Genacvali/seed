#!/bin/bash
# =============================================================================
# Сборка SEED Agent в standalone бинарник
# =============================================================================

set -e

echo "🚀 Сборка SEED Agent в бинарник"
echo "================================"

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден. Установите Python 3.11+"
    exit 1
fi

# Проверяем версию Python
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if [[ $(echo "$PYTHON_VERSION < 3.10" | bc -l) -eq 1 ]]; then
    echo "❌ Нужен Python 3.10+ (текущая версия: $PYTHON_VERSION)"
    exit 1
fi

# Переходим в директорию проекта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Рабочая директория: $SCRIPT_DIR"

# Создаем виртуальное окружение
echo "🐍 Создание виртуального окружения..."
python3 -m venv venv
source venv/bin/activate

# Обновляем pip
pip install --upgrade pip

# Устанавливаем зависимости
echo "📦 Установка зависимостей..."
pip install -r requirements.txt

# Устанавливаем PyInstaller и зависимости для metadata
echo "⚙️  Установка PyInstaller и дополнительных пакетов..."
pip install pyinstaller==6.3.0
pip install importlib-metadata

# Создаем spec файл для PyInstaller
echo "📝 Создание конфигурации для сборки..."
cat > seed-agent.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['seed-agent.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('fetchers', 'fetchers'),
        ('seed.yaml', '.'),
        ('plugins.py', '.'),
    ],
    hiddenimports=[
        'aio_pika',
        'aio_pika.abc',
        'aio_pika.connection',
        'aio_pika.channel',
        'aio_pika.message',
        'aio_pika.exchange',
        'aio_pika.queue',
        'aio_pika.robust_connection',
        'aio_pika.robust_channel',
        'aiormq',
        'aiormq.abc',
        'asyncio',
        'uvicorn',
        'uvicorn.workers',
        'fastapi',
        'fastapi.responses',
        'redis',
        'redis.asyncio',
        'pymongo',
        'yaml',
        'structlog',
        'prometheus_client',
        'cryptography',
        'cryptography.fernet',
        'httpx',
        'httpx._client',
        'pydantic',
        'pydantic.main',
        'pydantic.fields',
        'dotenv',
        'dateutil',
        'dateutil.parser'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='seed-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
EOF

# Сборка бинарника
echo "🔨 Сборка бинарника (это может занять несколько минут)..."
pyinstaller --clean seed-agent.spec

if [ $? -eq 0 ]; then
    echo "✅ Бинарник собран успешно!"
    echo ""
    echo "📁 Файл: $SCRIPT_DIR/dist/seed-agent"
    
    # Проверяем размер файла
    if [ -f "dist/seed-agent" ]; then
        FILESIZE=$(ls -lh dist/seed-agent | awk '{print $5}')
        echo "📏 Размер: $FILESIZE"
        
        # Делаем исполняемым
        chmod +x dist/seed-agent
        
        echo ""
        echo "🧪 Тестирование бинарника..."
        if ./dist/seed-agent --help > /dev/null 2>&1; then
            echo "✅ Бинарник работает корректно!"
        else
            echo "⚠️  Предупреждение: возможны проблемы с запуском"
        fi
        
        echo ""
        echo "📋 Для установки в систему:"
        echo "   sudo cp dist/seed-agent /usr/local/bin/"
        echo "   sudo chmod +x /usr/local/bin/seed-agent"
        echo ""
        echo "🚀 Для запуска:"
        echo "   ./dist/seed-agent --mode both --host 0.0.0.0 --port 8080"
        
    else
        echo "❌ Файл бинарника не найден!"
        exit 1
    fi
else
    echo "❌ Ошибка при сборке бинарника"
    exit 1
fi

# Деактивируем виртуальное окружение
deactivate

echo ""
echo "✅ Готово! Бинарник: dist/seed-agent"