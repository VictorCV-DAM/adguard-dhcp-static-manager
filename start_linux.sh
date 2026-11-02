#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "$DIR/python_portable/bin/python3" ]; then
    exec "$DIR/python_portable/bin/python3" app.py
elif [ -f "$DIR/python_portable/bin/python" ]; then
    exec "$DIR/python_portable/bin/python" app.py
else
    echo "[ERROR] Portable instance not found in $DIR/python_portable"
    echo "Please run ./install_linux.sh first."
    exit 1
fi
