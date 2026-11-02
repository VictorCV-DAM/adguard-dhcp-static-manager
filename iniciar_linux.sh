#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "$DIR/python_portable/bin/python3" ]; then
    exec "$DIR/python_portable/bin/python3" app.py
elif [ -f "$DIR/python_portable/bin/python" ]; then
    exec "$DIR/python_portable/bin/python" app.py
else
    echo "[!] No se encontró la instancia portable en $DIR/python_portable"
    echo "Ejecuta ./instalar_linux.sh primero para configurarla automáticamente."
    exit 1
fi
