# Setup completo para demo de defensa
docker-compose up -d
Start-Sleep -Seconds 15
docker exec haia_agent-api-1 python -c "from app.database.session import create_tables; create_tables()"
docker exec haia_agent-api-1 python -m tests.fixtures.sample_data
Write-Host "✓ HAIA listo. Ejecuta: python scripts/demo_defensa.py --auto"