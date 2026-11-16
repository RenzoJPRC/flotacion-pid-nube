#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
printf '\nAbra http://127.0.0.1:5000\n'
exec .venv/bin/python app.py
