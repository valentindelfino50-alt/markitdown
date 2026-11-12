@echo off
cd /d "%~dp0"
echo Cierra antes la ventana negra de iniciar.bat si la tenes abierta.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_accesos.ps1"
echo.
pause
