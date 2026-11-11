@echo off
title Convertidor a Markdown
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\Convertidor\venv"

if not exist "%VENV%\Scripts\python.exe" (
  echo Primera vez: preparando la app. Puede tardar unos minutos...
  where py >nul 2>nul && py -3 -m venv "%VENV%" || python -m venv "%VENV%"
)
if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo y marca la casilla "Add python.exe to PATH". Despues abri este archivo de nuevo.
  pause
  exit /b 1
)

"%VENV%\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo No se pudieron instalar los componentes. Revisa la conexion a internet y reintenta.
  pause
  exit /b 1
)

"%VENV%\Scripts\python.exe" server.py
echo.
echo La app se cerro.
pause
