# PayPilot AI - Start All Services
# Starts the FastAPI backend and Vite frontend in separate windows

$ProjectRoot = $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  PayPilot AI - Starting Services" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host ">> Starting FastAPI backend on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$ProjectRoot\backend'; Write-Host 'Backend starting...' -ForegroundColor Green; .\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload"

Start-Sleep -Seconds 3

# Start Frontend
Write-Host ">> Starting Vite frontend on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "cd '$ProjectRoot\frontend'; Write-Host 'Frontend starting...' -ForegroundColor Green; npm run dev"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Both servers are starting up!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend -> http://localhost:5173" -ForegroundColor White
Write-Host "  Backend  -> http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs -> http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "  Login: demo@paypilot.ai / demo123" -ForegroundColor White
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
