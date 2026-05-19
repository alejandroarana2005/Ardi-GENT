Write-Host "Levantando backend..." -ForegroundColor Cyan
docker-compose up -d
Start-Sleep -Seconds 15

Write-Host "Verificando backend..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/health" -ErrorAction SilentlyContinue
if ($health.status -eq "ok") {
    Write-Host "Backend listo en http://localhost:8000" -ForegroundColor Green
} else {
    Write-Host "Backend no responde, abortando" -ForegroundColor Red
    exit 1
}

Write-Host "Abriendo navegador..." -ForegroundColor Cyan
Start-Process "http://localhost:5173"

Write-Host "Levantando frontend (dejar esta ventana abierta)..." -ForegroundColor Cyan
cd frontend
npm run dev