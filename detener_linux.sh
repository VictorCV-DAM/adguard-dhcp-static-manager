#!/usr/bin/env bash
# ========================================================================
# Script para detener el servicio / proceso de AdGuard DHCP Panel
# ========================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORT=5001
if [ -f "$DIR/config.json" ]; then
    CFG_PORT=$(grep -o '"port"[^,]*' "$DIR/config.json" | grep -o '[0-9]*' | head -n 1)
    if [ -n "$CFG_PORT" ]; then
        PORT=$CFG_PORT
    fi
fi

STOPPED=0

echo "=================================================================="
echo "   Deteniendo AdGuard DHCP Panel Privado (Linux)..."
echo "=================================================================="

# 1. Comprobar si se está ejecutando como servicio systemd
if command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet dhcp-panel 2>/dev/null; then
        echo "-> Deteniendo servicio systemd 'dhcp-panel'..."
        if [ "$EUID" -eq 0 ]; then
            systemctl stop dhcp-panel
        else
            sudo systemctl stop dhcp-panel
        fi
        STOPPED=$((STOPPED + 1))
        echo "   [OK] Servicio systemd detenido."
    fi
fi

# 2. Comprobar si hay procesos independientes ejecutando app.py desde este directorio
PIDS=$(pgrep -f "$DIR/.*app\.py" || true)
if [ -n "$PIDS" ]; then
    echo "-> Terminando procesos en ejecución de app.py (PIDs: $PIDS)..."
    for pid in $PIDS; do
        kill -9 "$pid" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    done
fi

# 3. Comprobar procesos usando el binario de python_portable
PORTABLE_PIDS=$(pgrep -f "$DIR/python_portable/bin/python" || true)
if [ -n "$PORTABLE_PIDS" ]; then
    echo "-> Terminando procesos de python_portable (PIDs: $PORTABLE_PIDS)..."
    for pid in $PORTABLE_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    done
fi

# 4. Comprobar si queda algún proceso ocupando el puerto configurado
if command -v fuser &>/dev/null; then
    PORT_PIDS=$(fuser "$PORT/tcp" 2>/dev/null || true)
    if [ -n "$PORT_PIDS" ]; then
        echo "-> Liberando puerto $PORT (PIDs: $PORT_PIDS)..."
        fuser -k "$PORT/tcp" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    fi
fi

echo ""
if [ "$STOPPED" -gt 0 ]; then
    echo "=================================================================="
    echo "   [OK] Servidor AdGuard DHCP Panel detenido con éxito."
    echo "=================================================================="
else
    echo "=================================================================="
    echo "   [INFO] No se encontró ninguna instancia activa en ejecución."
    echo "   (Puerto $PORT libre y sin procesos activos)"
    echo "=================================================================="
fi
echo ""
