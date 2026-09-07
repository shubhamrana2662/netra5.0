#!/usr/bin/env pwsh
<#
.SYNOPSIS
    CyberDrishti AI — Quick Start Script
.DESCRIPTION
    Automated setup and launch for the entire CyberDrishti AI platform.
    Checks dependencies, starts infrastructure, and launches backend + frontend.
#>

$ErrorActionPreference = "Stop"

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 58) -ForegroundColor Cyan
Write-Host "🔍 CyberDrishti AI — Quick Start" -ForegroundColor Cyan
Write-Host ("=" * 60) -ForegroundColor Cyan
Write-Host ""

# ── Check Dependencies ────────────────────────────────────────────────────────
Write-Host "📋 Checking dependencies..." -ForegroundColor Yellow

$missing = @()

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    $missing += "Python 3.10+"
}

if (!(Get-Command node -ErrorAction SilentlyContinue)) {
    $missing += "Node.js 18+"
}

if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    $missing += "Docker"
}

if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    $missing += "Docker Compose"
}

if ($missing.Count -gt 0) {
    Write-Host "❌ Missing dependencies:" -ForegroundColor Red
    foreach ($dep in $missing) {
        Write-Host "   - $dep" -ForegroundColor Red
    }
    Write-Host "`nPlease install missing dependencies and try again.`n" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ All dependencies found`n" -ForegroundColor Green

# ── Start Infrastructure ──────────────────────────────────────────────────────
Write-Host "🐳 Starting infrastructure (Postgres + Redis)..." -ForegroundColor Yellow
docker-compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Docker containers`n" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Infrastructure running`n" -ForegroundColor Green

# ── Backend Setup ─────────────────────────────────────────────────────────────
Write-Host "🔧 Setting up backend..." -ForegroundColor Yellow
Set-Location backend

if (!(Test-Path "venv")) {
    Write-Host "   Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
}

Write-Host "   Activating virtual environment..." -ForegroundColor Cyan
& .\venv\Scripts\Activate.ps1

Write-Host "   Installing dependencies..." -ForegroundColor Cyan
pip install -r requirements.txt -q

if (!(Test-Path ".env")) {
    Write-Host "   Creating .env file..." -ForegroundColor Cyan
    @"
DATABASE_URL=postgresql://cd_user:cd_secure_password@localhost:5432/cyberdrishti
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key-change-in-production
"@ | Out-File -FilePath ".env" -Encoding utf8
}

Write-Host "✅ Backend setup complete`n" -ForegroundColor Green

# ── Frontend Setup ────────────────────────────────────────────────────────────
Write-Host "🔧 Setting up frontend..." -ForegroundColor Yellow
Set-Location ..\frontend

if (!(Test-Path "node_modules")) {
    Write-Host "   Installing npm dependencies..." -ForegroundColor Cyan
    npm install
}

if (!(Test-Path ".env.local")) {
    Write-Host "   Creating .env.local file..." -ForegroundColor Cyan
    "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" | Out-File -FilePath ".env.local" -Encoding utf8
}

Write-Host "✅ Frontend setup complete`n" -ForegroundColor Green

# ── Database Initialization ───────────────────────────────────────────────────
Write-Host "🗄️  Initializing database..." -ForegroundColor Yellow
Set-Location ..\backend
python database\init_db.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Database initialized`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Database initialization failed (may already exist)`n" -ForegroundColor Yellow
}

# ── Launch Prompt ─────────────────────────────────────────────────────────────
Write-Host "=" -NoNewline -ForegroundColor Green
Write-Host ("=" * 58) -ForegroundColor Green
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ("=" * 60) -ForegroundColor Green
Write-Host ""

Write-Host "🚀 Ready to launch CyberDrishti AI`n" -ForegroundColor Cyan

Write-Host "Next steps:`n" -ForegroundColor Yellow
Write-Host "1. Start Backend (Terminal 1):" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "   uvicorn main:app --reload`n" -ForegroundColor Gray

Write-Host "2. Start Frontend (Terminal 2):" -ForegroundColor White
Write-Host "   cd frontend" -ForegroundColor Gray
Write-Host "   npm run dev`n" -ForegroundColor Gray

Write-Host "3. (Optional) Generate Training Data:" -ForegroundColor White
Write-Host "   cd backend" -ForegroundColor Gray
Write-Host "   python nlp/generate_ner_training_data.py --output_dir training_data --n_sentences 8000`n" -ForegroundColor Gray

Write-Host "4. (Optional) Train Models:" -ForegroundColor White
Write-Host "   python train_all.py --synthetic 8000 --epochs 10 --gpu`n" -ForegroundColor Gray

Write-Host "📍 URLs:" -ForegroundColor Yellow
Write-Host "   Frontend:  http://localhost:3000" -ForegroundColor Cyan
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor Cyan
Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "   Adminer:   http://localhost:8080" -ForegroundColor Cyan
Write-Host ""

Write-Host "🔐 Default Login (after creating user via API):" -ForegroundColor Yellow
Write-Host "   Username: admin" -ForegroundColor Gray
Write-Host "   Password: admin123`n" -ForegroundColor Gray

Write-Host "💡 Tip: Open 2 terminals and follow steps 1 & 2 above`n" -ForegroundColor Magenta

Set-Location ..
