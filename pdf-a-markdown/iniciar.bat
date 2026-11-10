@echo off
rem Inicia la app PDF a Markdown (Windows). Haz doble clic en este archivo.
rem El entorno de Python se guarda FUERA de la carpeta para que OneDrive no lo sincronice.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\pdf-a-markdown\venv"

if exist "%VENV%\.listo" goto ejecutar

echo Primera vez: preparando el programa. Puede tardar unos minutos...
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m venv "%VENV%"
) else (
  python -m venv "%VENV%"
)
if errorlevel 1 goto sinpython
"%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 goto fallo
echo listo> "%VENV%\.listo"

:ejecutar
"%VENV%\Scripts\python.exe" app.py %*
goto fin

:sinpython
echo.
echo No se encontro Python 3.10 o superior.
echo Instalalo desde https://www.python.org/downloads/ y marca la casilla "Add python.exe to PATH".
goto fin

:fallo
echo.
echo No se pudieron instalar los componentes. Revisa tu conexion a Internet e intentalo de nuevo.

:fin
pause
