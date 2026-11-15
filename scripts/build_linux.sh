#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[build]"
pyinstaller packaging/pyinstaller.spec --noconfirm

echo "Portable build created at $ROOT/dist/KavSSH"
