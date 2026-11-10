@echo off
rem Inicia la app PDF a Markdown (Windows). Haz doble clic en este archivo.
rem El entorno de Python se guarda FUERA de la carpeta para que OneDrive no lo sincronice.
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "VENV=%LOCALAPPDATA%\pdf-a-markdown\venv"

if exist "%VENV%\.listo" goto ejecutar

echo Primera vez: preparando el programa. Puede tardar unos minutos...

rem MarkItDown funciona con Python 3.10 a 3.14. Se busca una version compatible
rem aunque tengas instalada otra mas nueva (por ejemplo 3.15).
set "PYCMD="
for %%V in (3.13 3.12 3.11 3.14 3.10) do (
  if not defined PYCMD (
    py -%%V -c "import sys" >nul 2>nul
    if not errorlevel 1 set "PYCMD=py -%%V"
  )
)
if defined PYCMD goto crearvenv

python -c "import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>nul
if errorlevel 1 goto sinpython
set "PYCMD=python"

:crearvenv
echo Usando: %PYCMD%
%PYCMD% -m venv --clear "%VENV%"
if errorlevel 1 goto fallo
"%VENV%\Scripts\python.exe" -m pip install --quiet --upgrade pip
"%VENV%\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 goto fallo
"%VENV%\Scripts\python.exe" -c "import markitdown" >nul 2>nul
if errorlevel 1 goto sinruntime
echo listo> "%VENV%\.listo"

:ejecutar
"%VENV%\Scripts\python.exe" app.py %*
goto fin

:sinpython
echo.
echo No se encontro una version compatible de Python (se necesita de 3.10 a 3.14).
echo Instala Python 3.13 desde https://www.python.org/downloads/windows/ y vuelve a abrir este archivo.
goto fin

:sinruntime
echo.
echo Los componentes se instalaron, pero no pueden iniciar (error de DLL con numpy).
echo Normalmente se arregla instalando "Microsoft Visual C++ Redistributable" x64:
echo https://aka.ms/vs/17/release/vc_redist.x64.exe
echo Instalalo, reinicia la PC y vuelve a abrir este archivo.
goto fin

:fallo
echo.
echo No se pudieron instalar los componentes. Revisa tu conexion a Internet e intentalo de nuevo.

:fin
pause
