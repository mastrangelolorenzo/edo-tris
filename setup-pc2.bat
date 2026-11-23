@echo off
rem Insegna i punti al robot Y (collegato a questo PC). Lancia prima avvia-pc2.bat.
cd /d "%~dp0"
docker compose --profile pc2 build edo-y || goto error
docker compose --profile pc2 run --rm --no-deps -v .:/repo -e CONFIG_FILE=/repo/config.json edo-y python teach.py EDO-Y || goto error
docker compose --profile pc2 restart edo-y
echo Setup di EDO-Y completato.
pause
exit /b 0
:error
echo Setup non riuscito.
pause
exit /b 1
