@echo off
rem PC1 (giocatore): WINGRID + EDO-X, poi apre il gioco a schermo intero (Alt+F4 per uscire).
rem Prima: config.json -> broker.host = IP del PC2, edo.EDO-X.ip = IP del robot X.
cd /d "%~dp0"
set PORT=8880
for /f "tokens=2 delims==" %%p in ('findstr /b WINGRID_PORT .env') do set PORT=%%p
docker compose --profile pc1 up -d --build || goto error
echo Attendo il gioco su http://localhost:%PORT% ...
:wait
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://localhost:%PORT% | Out-Null } catch { exit 1 }" || (timeout /t 2 /nobreak >nul & goto wait)
start "" msedge --kiosk http://localhost:%PORT% --edge-kiosk-type=fullscreen --no-first-run --user-data-dir="%TEMP%\tris-kiosk"
exit /b 0
:error
echo Avvio non riuscito: Docker Desktop e' acceso?
pause
exit /b 1
