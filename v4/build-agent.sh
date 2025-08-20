#!/bin/bash
# =============================================================================
# SEED Agent v4 Build Script
# Fixed configuration loading and dependency issues
# =============================================================================

set -e

echo "🚀 Building SEED Agent v4"
echo "========================="

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "📍 Python version: $PYTHON_VERSION"

# Set working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "📂 Working directory: $SCRIPT_DIR"

# Create virtual environment
echo "🐍 Setting up virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Install PyInstaller and metadata support
echo "⚙️  Installing PyInstaller..."
pip install pyinstaller==6.3.0
pip install importlib-metadata

# Create spec file with proper configuration handling
echo "📝 Creating build configuration..."
cat > seed-agent.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

block_cipher = None

# Collect all submodules and metadata
hiddenimports_auto = []
hiddenimports_auto += collect_submodules('aio_pika')
hiddenimports_auto += collect_submodules('aiormq')

# Collect metadata files
datas = []
datas += copy_metadata('aio_pika')
datas += copy_metadata('aiormq')
datas += copy_metadata('fastapi')
datas += copy_metadata('uvicorn')
datas += copy_metadata('pydantic')
datas += copy_metadata('redis')
datas += copy_metadata('pymongo')

a = Analysis(
    ['seed-agent.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('core', 'core'),
        ('fetchers', 'fetchers'),  
        ('seed.yaml', '.'),
        ('plugins.py', '.'),
    ] + datas,
    hiddenimports=[
        # Core dependencies
        'asyncio',
        'uvicorn',
        'uvicorn.workers',
        'fastapi',
        'fastapi.responses',
        'fastapi.middleware',
        'starlette',
        'starlette.responses',
        'starlette.routing',
        'starlette.middleware',
        
        # Data and validation
        'pydantic',
        'pydantic.main',
        'pydantic.fields',
        'pydantic.validators',
        
        # Database clients
        'redis',
        'redis.asyncio',
        'pymongo',
        'pymongo.errors',
        
        # Configuration
        'yaml',
        'dotenv',
        
        # HTTP client
        'httpx',
        'httpx._client',
        'httpx._config',
        'httpx._exceptions',
        
        # Logging and monitoring
        'structlog',
        'prometheus_client',
        
        # Crypto and security
        'cryptography',
        'cryptography.fernet',
        
        # Date/time
        'dateutil',
        'dateutil.parser',
        
        # Standard library
        'json',
        'pathlib',
        'logging.handlers',
        'urllib.parse',
    ] + hiddenimports_auto,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas'
    ],
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

# Build binary
echo "🔨 Building binary (this may take several minutes)..."
pyinstaller --clean seed-agent.spec

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo ""
    
    if [ -f "dist/seed-agent" ]; then
        FILESIZE=$(ls -lh dist/seed-agent | awk '{print $5}')
        echo "📁 Binary: $SCRIPT_DIR/dist/seed-agent"
        echo "📏 Size: $FILESIZE"
        
        # Make executable
        chmod +x dist/seed-agent
        
        echo ""
        echo "🧪 Testing binary..."
        if ./dist/seed-agent --help > /dev/null 2>&1; then
            echo "✅ Binary works correctly!"
        else
            echo "⚠️  Warning: binary test failed"
        fi
        
        echo ""
        echo "📋 Installation commands:"
        echo "   sudo cp dist/seed-agent /usr/local/bin/"
        echo "   sudo chmod +x /usr/local/bin/seed-agent"
        echo ""
        echo "🚀 Usage examples:"
        echo "   ./dist/seed-agent --config seed.yaml"
        echo "   ./dist/seed-agent --host 0.0.0.0 --port 8080"
        echo "   ./dist/seed-agent --debug"
        echo ""
        echo "🔧 Configuration:"
        echo "   Copy seed.yaml to the same directory as the binary"
        echo "   Set environment variables with SEED_ prefix to override config"
        echo "   Example: export SEED_RABBITMQ_HOST=rabbitmq.example.com"
        
    else
        echo "❌ Binary not found!"
        exit 1
    fi
else
    echo "❌ Build failed"
    exit 1
fi

# Deactivate virtual environment
deactivate

echo ""
echo "✅ SEED Agent v4 build complete!"
echo "📦 Binary: dist/seed-agent"
echo ""
echo "🆕 v4 Improvements:"
echo "  • Fixed configuration loading from YAML"
echo "  • Eliminated hardcoded connection strings"
echo "  • Environment variable interpolation support"
echo "  • Proper error handling and validation"
echo "  • Centralized service discovery"