@echo off
setlocal
title Convertidor a Markdown
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\Convertidor\venv"

rem Si el entorno se creo con una version de Python que no sirve, se rehace.
if exist "%VENV%\Scripts\python.exe" (
  "%VENV%\Scripts\python.exe" comprobar_python.py >nul 2>nul
  if errorlevel 1 (
    echo El entorno anterior usa una version de Python no compatible. Se va a rehacer...
    rmdir /s /q "%VENV%"
  )
)

if not exist "%VENV%\Scripts\python.exe" (
  echo Primera vez: preparando la app. Puede tardar unos minutos...
  call :crear_entorno
)

if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo No se encontro una version de Python compatible. La app necesita Python 3.10 a 3.14.
  echo Si tenes instalada la 3.15 o una anterior a la 3.10, no sirve.
  echo.
  echo SOLUCION: abri la consola de Windows y ejecuta este comando:
  echo     winget install Python.Python.3.13
  echo o bajala de https://www.python.org/downloads/windows/ ^(la 3.13, 64-bit^).
  echo Marca "Add python.exe to PATH" al instalar. Despues abri este archivo de nuevo.
  pause
  exit /b 1
)

"%VENV%\Scripts\python.exe" -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo.
  echo No se pudieron instalar los componentes. Revisa la conexion a internet y reintenta.
  echo Si el error habla de conflictos, copiame el mensaje completo.
  pause
  exit /b 1
)

"%VENV%\Scripts\python.exe" server.py
echo.
echo La app se cerro.
pause
exit /b 0

:crear_entorno
rem Prueba primero las versiones de Python que ya estan instaladas y sirven.
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not exist "%VENV%\Scripts\python.exe" py -%%V -m venv "%VENV%" >nul 2>nul
)
if not exist "%VENV%\Scripts\python.exe" (
  python comprobar_python.py >nul 2>nul
  if not errorlevel 1 python -m venv "%VENV%" >nul 2>nul
)
exit /b 0
