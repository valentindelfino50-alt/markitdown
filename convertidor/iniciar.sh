#!/usr/bin/env bash
# Para Mac / Linux. En Windows usá iniciar.bat
set -e
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/python -m pip install -q -r requirements.txt
exec .venv/bin/python server.py
