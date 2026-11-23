@echo off
rem PC2 (AI): broker, BUTLER, TRIS, FRAME, EDO-Y.
rem Prima: config.json -> edo.EDO-Y.ip = IP del robot Y.
cd /d "%~dp0"
docker compose --profile pc2 up -d --build || goto error
echo.
echo PC2 avviato. Indirizzi di questo PC: uno di questi va in config.json del PC1 (broker.host).
ipconfig | findstr /c:"IPv4"
echo.
pause
exit /b 0
:error
echo Avvio non riuscito: Docker Desktop e' acceso?
pause
exit /b 1
