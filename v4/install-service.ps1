# SEED Agent v4 - Windows Service Installation Script
param(
    [string]$ServiceName = "SEED Agent v4",
    [string]$InstallPath = "C:\SEED-Agent",
    [string]$NssmPath = "nssm.exe"
)

Write-Host "🔧 Installing SEED Agent v4 as Windows service..." -ForegroundColor Green

# Check admin privileges
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ This script must be run as Administrator" -ForegroundColor Red
    exit 1
}

# Check if NSSM is available
if (!(Get-Command $NssmPath -ErrorAction SilentlyContinue)) {
    Write-Host "❌ NSSM not found. Please install NSSM first:" -ForegroundColor Red
    Write-Host "   Download: https://nssm.cc/download" -ForegroundColor Yellow
    Write-Host "   Or use chocolatey: choco install nssm" -ForegroundColor Yellow
    exit 1
}

# Create installation directory
Write-Host "📁 Creating installation directory: $InstallPath" -ForegroundColor Cyan
New-Item -ItemType Directory -Path $InstallPath -Force | Out-Null

# Copy files
Write-Host "📦 Copying SEED Agent files..." -ForegroundColor Cyan
Copy-Item -Path ".\*" -Destination $InstallPath -Recurse -Force

# Build agent if not exists
$AgentPath = "$InstallPath\dist\seed-agent.exe"
if (!(Test-Path $AgentPath)) {
    Write-Host "🔨 Building SEED Agent..." -ForegroundColor Yellow
    Set-Location $InstallPath
    .\build-agent.sh
    Set-Location -
}

# Install service with NSSM
Write-Host "⚙️ Installing Windows service with NSSM..." -ForegroundColor Cyan

# Remove existing service if exists
& $NssmPath remove $ServiceName confirm 2>$null

# Install service
& $NssmPath install $ServiceName $AgentPath
& $NssmPath set $ServiceName AppDirectory $InstallPath
& $NssmPath set $ServiceName AppParameters "--config seed.yaml"
& $NssmPath set $ServiceName DisplayName $ServiceName
& $NssmPath set $ServiceName Description "SEED Agent v4 - Monitoring and Alerting System"

# Configure service settings
& $NssmPath set $ServiceName Start SERVICE_AUTO_START
& $NssmPath set $ServiceName AppThrottle 1500
& $NssmPath set $ServiceName AppStdout "$InstallPath\seed-agent.log"
& $NssmPath set $ServiceName AppStderr "$InstallPath\seed-agent-error.log"
& $NssmPath set $ServiceName AppRotateFiles 1
& $NssmPath set $ServiceName AppRotateOnline 1
& $NssmPath set $ServiceName AppRotateSeconds 86400
& $NssmPath set $ServiceName AppRotateBytes 10485760

# Set environment variables
& $NssmPath set $ServiceName AppEnvironmentExtra "RABBITMQ_USER=admin" "RABBITMQ_PASS=admin"

Write-Host ""
Write-Host "✅ SEED Agent v4 installed as Windows service!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Service commands:" -ForegroundColor Cyan
Write-Host "   net start `"$ServiceName`"      # Start service" -ForegroundColor White
Write-Host "   net stop `"$ServiceName`"       # Stop service" -ForegroundColor White
Write-Host "   sc query `"$ServiceName`"       # Check status" -ForegroundColor White
Write-Host ""
Write-Host "🏃 Starting service now..." -ForegroundColor Yellow

# Start Docker services first
Write-Host "📦 Starting Docker services..." -ForegroundColor Cyan
docker-compose up -d

Start-Sleep -Seconds 10

# Start SEED Agent service
$startResult = Start-Service -Name $ServiceName -PassThru
if ($startResult.Status -eq "Running") {
    Write-Host "✅ Service started successfully!" -ForegroundColor Green
    
    Start-Sleep -Seconds 10
    
    # Check if agent is responding
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "🎉 SEED Agent v4 is running!" -ForegroundColor Green
            Write-Host "🌐 Access: http://localhost:8080/health" -ForegroundColor Cyan
        }
    } catch {
        Write-Host "⚠️ Service is starting up. Check in a moment." -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ Failed to start service. Check Windows Event Viewer for details." -ForegroundColor Red
}

Write-Host ""
Write-Host "📁 Installation directory: $InstallPath" -ForegroundColor Gray
Write-Host "📜 Logs: $InstallPath\seed-agent.log" -ForegroundColor Gray