# start-dev.ps1 - Script PowerShell pour démarrer l'environnement complet

Write-Host "Starting JobMatch..." -ForegroundColor Green
Write-Host ""

# Check directory
if (-not (Test-Path "backend/app.py")) {
    Write-Host "Error: Run this script from the project root" -ForegroundColor Red
    exit 1
}

# Start backend
Write-Host "Starting backend (port 5001)..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath .\.venv\Scripts\python.exe -ArgumentList "backend\app.py"
Start-Sleep -Seconds 2

# Start frontend
Write-Host "Starting frontend (port 8080)..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath python -ArgumentList "-m http.server 8080" -WorkingDirectory "frontend"
Start-Sleep -Seconds 1

Write-Host ""
Write-Host "JobMatch is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Access:" -ForegroundColor Yellow
Write-Host "  - Frontend  : http://localhost:8080" -ForegroundColor White
Write-Host "  - Backend   : http://localhost:5001" -ForegroundColor White
Write-Host "  - API Docs  : http://localhost:5001" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop servers" -ForegroundColor Yellow
Write-Host ""

# Garder la fenêtre ouverte
Read-Host "Appuyez sur Entrée pour terminer"
