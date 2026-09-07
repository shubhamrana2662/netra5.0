$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  CyberDrishti AI - Starting Full Stack..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start PostgreSQL Service
Write-Host "[1/3] Checking PostgreSQL..." -ForegroundColor Yellow

$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService) {
    if ($pgService.Status -ne "Running") {
        Write-Host "      Starting PostgreSQL service..." -ForegroundColor Gray
        try {
            Start-Service $pgService.Name -ErrorAction Stop
            Start-Sleep -Seconds 3
            Write-Host "      PostgreSQL started!" -ForegroundColor Green
        } catch {
            Write-Host "      Could not start PostgreSQL. Try running as Admin." -ForegroundColor Red
        }
    } else {
        Write-Host "      PostgreSQL already running!" -ForegroundColor Green
    }
} else {
    $pgDir = Join-Path $ProjectRoot "backend\pgsql"
    $pgCtl = Join-Path $pgDir "bin\pg_ctl.exe"
    if (Test-Path $pgCtl) {
        Write-Host "      Starting portable PostgreSQL..." -ForegroundColor Gray
        $pgData = Join-Path $pgDir "data"
        $pgLog = Join-Path $pgDir "log.txt"
        & $pgCtl -D $pgData -l $pgLog start
        Start-Sleep -Seconds 3
        Write-Host "      PostgreSQL started!" -ForegroundColor Green
    } else {
        Write-Host "      No PostgreSQL service found. Make sure it is running on port 5432." -ForegroundColor Red
    }
}
Write-Host ""

# Step 2: Start Backend
Write-Host "[2/3] Starting Backend (FastAPI) on port 8000..." -ForegroundColor Yellow

$backendCmd = "Set-Location '$ProjectRoot\backend'; `$env:DATABASE_URL='postgresql://cyberdrishti:cyberdrishti_secret@localhost:5432/cyberdrishti'; `$env:REDIS_URL='redis://localhost:6379/0'; `$env:OLLAMA_BASE_URL='http://localhost:11434'; `$env:ALLOW_CLOUD_AI='false'; uv run --python 3.11 --with-requirements requirements.txt uvicorn main:app --reload --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "      Backend launching in new window..." -ForegroundColor Green
Start-Sleep -Seconds 3
Write-Host ""

# Step 3: Start local model service
Write-Host "[3/4] Starting Ollama model service on port 11434..." -ForegroundColor Yellow
$ollamaReady = Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue
if (-not $ollamaReady) {
    Start-Process ollama.exe -ArgumentList "serve"
    Start-Sleep -Seconds 3
}
Write-Host "      Ollama launching..." -ForegroundColor Green
Write-Host ""

# Step 4: Start Frontend
Write-Host "[4/4] Starting Frontend (Next.js) on port 3100..." -ForegroundColor Yellow

$frontendCmd = "Set-Location '$ProjectRoot\frontend'; npm run dev -- -p 3100"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
Write-Host "      Frontend launching in new window..." -ForegroundColor Green
Start-Sleep -Seconds 5
Write-Host ""

# Done
Write-Host "============================================================" -ForegroundColor Green
Write-Host "  CyberDrishti AI - All Services Launched!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:   http://localhost:3100" -ForegroundColor Cyan
Write-Host "  Backend:    http://localhost:8000" -ForegroundColor Cyan
Write-Host "  API Docs:   http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "  Health:     http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""

Start-Process "http://localhost:3100"
Write-Host "  Browser opened! Wait 10 seconds for servers to fully boot." -ForegroundColor Magenta
Write-Host ""
