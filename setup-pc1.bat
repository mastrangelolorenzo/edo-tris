@echo off
rem Insegna i punti al robot X (collegato a questo PC). Il PC2 deve essere gia' avviato.
cd /d "%~dp0"
docker compose --profile pc1 build edo-x || goto error
docker compose --profile pc1 run --rm --no-deps -v .:/repo -e CONFIG_FILE=/repo/config.json edo-x python teach.py EDO-X || goto error
docker compose --profile pc1 restart edo-x
echo Setup di EDO-X completato.
pause
exit /b 0
:error
echo Setup non riuscito.
pause
exit /b 1
