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
  # MarkItDown funciona con Python 3.10 a 3.14: se busca una version compatible.
  PY=""
  for c in python3.13 python3.12 python3.11 python3.14 python3.10 python3 python; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)'; then
      PY=$(command -v "$c"); break
    fi
  done
  if [ -z "$PY" ]; then
    echo "No se encontro una version compatible de Python (de 3.10 a 3.14)."
    echo "Instala Python 3.13 desde https://www.python.org/downloads/"
    exit 1
  fi
  "$PY" -m venv --clear "$VENV"
  "$VENV/bin/python" -m pip install --quiet --upgrade pip
  "$VENV/bin/python" -m pip install --quiet -r requirements.txt
  touch "$VENV/.listo"
fi

exec "$VENV/bin/python" app.py "$@"
