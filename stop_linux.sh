#!/usr/bin/env bash
# ========================================================================
# Script to stop AdGuard DHCP Panel service / process
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
echo "   Stopping AdGuard DHCP Panel (Linux)..."
echo "=================================================================="

# 1. Check if running as systemd service
if command -v systemctl &>/dev/null; then
    if systemctl is-active --quiet dhcp-panel 2>/dev/null; then
        echo "-> Stopping systemd service 'dhcp-panel'..."
        if [ "$EUID" -eq 0 ]; then
            systemctl stop dhcp-panel
        else
            sudo systemctl stop dhcp-panel
        fi
        STOPPED=$((STOPPED + 1))
        echo "   [OK] systemd service stopped."
    fi
fi

# 2. Check for processes running app.py from this directory
PIDS=$(pgrep -f "$DIR/.*app\.py" || true)
if [ -n "$PIDS" ]; then
    echo "-> Terminating running app.py processes (PIDs: $PIDS)..."
    for pid in $PIDS; do
        kill -9 "$pid" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    done
fi

# 3. Check for processes using python_portable binary
PORTABLE_PIDS=$(pgrep -f "$DIR/python_portable/bin/python" || true)
if [ -n "$PORTABLE_PIDS" ]; then
    echo "-> Terminating python_portable processes (PIDs: $PORTABLE_PIDS)..."
    for pid in $PORTABLE_PIDS; do
        kill -9 "$pid" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    done
fi

# 4. Check if port is still occupied
if command -v fuser &>/dev/null; then
    PORT_PIDS=$(fuser "$PORT/tcp" 2>/dev/null || true)
    if [ -n "$PORT_PIDS" ]; then
        echo "-> Freeing port $PORT (PIDs: $PORT_PIDS)..."
        fuser -k "$PORT/tcp" 2>/dev/null || true
        STOPPED=$((STOPPED + 1))
    fi
fi

echo ""
if [ "$STOPPED" -gt 0 ]; then
    echo "=================================================================="
    echo "   [OK] AdGuard DHCP Panel server stopped successfully."
    echo "=================================================================="
else
    echo "=================================================================="
    echo "   [INFO] No active running instance found."
    echo "   (Port $PORT is free and no active processes)"
    echo "=================================================================="
fi
echo ""
