#!/usr/bin/env bash
# Inicia la app PDF a Markdown (Mac / Linux).
# Uso:  ./iniciar.sh            -> solo en esta computadora
#       ./iniciar.sh --celular  -> tambien desde el celular (misma Wi-Fi)
set -e
cd "$(dirname "$0")"

# El entorno de Python se guarda FUERA de la carpeta (para que OneDrive no lo sincronice).
VENV="${XDG_DATA_HOME:-$HOME/.local/share}/pdf-a-markdown/venv"

if [ ! -f "$VENV/.listo" ]; then
  echo "Primera vez: preparando el programa (puede tardar unos minutos)..."
  PY=$(command -v python3 || command -v python || true)
  if [ -z "$PY" ]; then
    echo "No se encontro Python 3.10 o superior. Instalalo desde https://www.python.org/downloads/"
    exit 1
  fi
  "$PY" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements.txt
  touch "$VENV/.listo"
fi

exec "$VENV/bin/python" app.py "$@"
