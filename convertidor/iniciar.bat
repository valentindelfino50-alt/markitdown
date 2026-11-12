@echo off
setlocal
title Convertidor a Markdown
cd /d "%~dp0"
set "BASEDIR=%LOCALAPPDATA%\Convertidor"
set "VENV=%BASEDIR%\venv"
set "LOG=%BASEDIR%\instalacion.log"
if not exist "%BASEDIR%" mkdir "%BASEDIR%"

call :validar
if not exist "%VENV%\Scripts\python.exe" (
  echo Primera vez: preparando la app. Puede tardar unos minutos...
  call :crear_entorno
  call :validar
)

if not exist "%VENV%\Scripts\python.exe" (
  echo.
  echo No se encontro una Python compatible. La app necesita Python 3.10 a 3.14 de 64 bits.
  echo Las Python que tenes instaladas son:
  py -0p
  echo.
  echo SOLUCION: instala la 3.13 de 64 bits. Abri la consola de Windows y ejecuta:
  echo     winget install Python.Python.3.13
  echo o bajala de https://www.python.org/downloads/windows/ ^(Windows installer 64-bit^).
  echo Marca "Add python.exe to PATH" al instalar. Despues abri este archivo de nuevo.
  pause
  exit /b 1
)

echo Verificando componentes. La primera vez puede tardar varios minutos...
"%VENV%\Scripts\python.exe" -m pip install -r requirements.txt > "%LOG%" 2>&1
if errorlevel 1 (
  echo.
  echo No se pudieron instalar los componentes. Este es el detalle:
  echo ------------------------------------------------------------
  type "%LOG%"
  echo ------------------------------------------------------------
  "%VENV%\Scripts\python.exe" comprobar_python.py
  echo.
  echo Copia todo este texto y mandamelo. Tambien quedo guardado en:
  echo %LOG%
  pause
  exit /b 1
)

"%VENV%\Scripts\python.exe" server.py
echo.
echo La app se cerro.
pause
exit /b 0

:validar
rem Si el entorno existe pero usa una Python que no sirve, se descarta.
if exist "%VENV%\Scripts\python.exe" (
  "%VENV%\Scripts\python.exe" comprobar_python.py
  if errorlevel 1 (
    echo Se descarta ese entorno y se va a rehacer.
    rmdir /s /q "%VENV%"
  )
)
exit /b 0

:crear_entorno
rem Prueba las versiones instaladas que sirven, siempre de 64 bits.
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not exist "%VENV%\Scripts\python.exe" py -%%V-64 -m venv "%VENV%" >nul 2>nul
)
if not exist "%VENV%\Scripts\python.exe" (
  python comprobar_python.py >nul 2>nul
  if not errorlevel 1 python -m venv "%VENV%" >nul 2>nul
)
exit /b 0
