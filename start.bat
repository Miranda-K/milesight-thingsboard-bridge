@echo off
:: Exit on error script behavior
echo === [1/3] Setting up ThingsBoard for the first time... ===
docker compose --profile install run --rm thingsboard-installer
if %errorlevel% neq 0 ( echo Installation failed! & pause & exit /b %errorlevel% )

echo === [2/3] Starting the full stack... ===
docker compose up -d
if %errorlevel% neq 0 ( echo Failed to start containers! & pause & exit /b %errorlevel% )

echo === Waiting for database & backend services to initialize (15s)... ===
timeout /t 15 /nobreak > nul

echo === [3/3] Importing rule chains & dashboards... ===
docker compose --profile provision run --rm tb-provision
if %errorlevel% neq 0 ( echo Provisioning failed! & pause & exit /b %errorlevel% )

echo === Setup complete! Access ThingsBoard at http://localhost:8080 ===
pause
