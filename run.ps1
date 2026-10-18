$ErrorActionPreference = "Stop"

# Always run from this project's folder, wherever the folder is located.
Set-Location -LiteralPath $PSScriptRoot

Write-Host ""
Write-Host "Starting the AI Digital Forensics project..." -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\backend\app\main.py")) {
    Write-Host "ERROR: Could not find backend\app\main.py." -ForegroundColor Red
    Write-Host "Move run.ps1 into the main project folder (the folder containing the backend folder)."
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path ".\work\pydeps")) {
    Write-Host "ERROR: Could not find work\pydeps." -ForegroundColor Red
    Write-Host "This launcher expects the dependencies to be in work\pydeps, as in your original setup."
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Python was not found. Check that Python is installed and available in PATH." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

New-Item -ItemType Directory -Force -Path ".\data", ".\data\evidence" | Out-Null

$env:PYTHONPATH = (Resolve-Path ".\work\pydeps").Path + ";" + (Resolve-Path ".").Path
$env:APP_ENV = "development"
$env:DEMO_MODE = "true"
$env:DATABASE_URL = "sqlite:///./data/forensics_dev.db"
$env:EVIDENCE_STORAGE_DIR = "./data/evidence"
$env:SESSION_COOKIE_SECURE = "false"

Write-Host "API docs:   http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "Prototype:  http://127.0.0.1:8000/prototype/indexers.html" -ForegroundColor Green
Write-Host ""
Write-Host "Keep this window open while using the app. Press Ctrl+C to stop it." -ForegroundColor Yellow
Write-Host ""

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "The server stopped with an error. If port 8000 is already in use, close the other server window first." -ForegroundColor Red
    Read-Host "Press Enter to close"
}
