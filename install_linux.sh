#!/usr/bin/env bash
# ========================================================================
# Portable Auto-Installer for AdGuard DHCP Panel (Linux / Raspberry Pi)
# Installs an isolated PORTABLE Python instance (zero system modification)
# ========================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

PORTABLE_DIR="$DIR/python_portable"
REQ_FILE="$DIR/requirements.txt"
CONFIG_FILE="$DIR/config.json"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}   Portable Installer - AdGuard DHCP Panel (Linux)                ${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo "Project directory: $DIR"
echo "Portable Python target: $PORTABLE_DIR"
echo ""

# 1. Verify python3 is installed
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 is not installed on this system.${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Attempting to install python3 via apt...${NC}"
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    else
        echo "Please install python3 and re-run this installer."
        exit 1
    fi
fi

# 2. Verify venv module
if ! python3 -m venv --help &>/dev/null; then
    echo -e "${YELLOW}[!] Python venv module is not installed.${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Installing python3-venv via apt...${NC}"
        sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
    else
        echo -e "${RED}Please install the python3-venv package for your distribution.${NC}"
        exit 1
    fi
fi

# 3. Create isolated portable environment
echo -e "${YELLOW}[1/4] Creating isolated Python instance in python_portable/...${NC}"
if [ -d "$PORTABLE_DIR" ] && [ -f "$PORTABLE_DIR/bin/python3" ]; then
    echo -e "${GREEN}[OK] Existing portable instance detected in python_portable/.${NC}"
else
    python3 -m venv "$PORTABLE_DIR"
    echo -e "${GREEN}[OK] Portable instance created successfully.${NC}"
fi

# 4. Upgrade pip and install dependencies in python_portable
echo ""
echo -e "${YELLOW}[2/4] Installing dependencies exclusively in portable instance...${NC}"
echo -e "${CYAN}      (Your system-wide Python will NOT be modified)${NC}"

"$PORTABLE_DIR/bin/python3" -m pip install --upgrade pip

if [ -f "$REQ_FILE" ]; then
    "$PORTABLE_DIR/bin/pip" install -r "$REQ_FILE"
else
    "$PORTABLE_DIR/bin/pip" install flask cryptography
fi

# Verify imports
if "$PORTABLE_DIR/bin/python3" -c "import flask, cryptography; print('OK')" &>/dev/null; then
    echo -e "${GREEN}[OK] Dependencies verified successfully in python_portable.${NC}"
else
    echo -e "${RED}[ERROR] Failed to verify dependencies in portable instance.${NC}"
    exit 1
fi

# 5. Check or generate config.json
echo ""
echo -e "${YELLOW}[3/4] Checking config.json...${NC}"
if [ ! -f "$CONFIG_FILE" ]; then
    SECRET_HEX=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || echo "secret_dhcp_panel_default")
    cat <<EOF > "$CONFIG_FILE"
{
  "adguard_url": "",
  "adguard_user": "",
  "adguard_pass": "",
  "port": 5001,
  "debug": false,
  "home_assistant_instances": [],
  "routers": [],
  "session_secret": "$SECRET_HEX"
}
EOF
    echo -e "${GREEN}[OK] Created default config.json.${NC}"
else
    echo -e "${GREEN}[OK] config.json already exists.${NC}"
fi

# 6. Set launcher permissions
echo ""
echo -e "${YELLOW}[4/4] Setting execution permissions...${NC}"
chmod +x "$DIR/start_linux.sh" "$DIR/stop_linux.sh" 2>/dev/null || true

# 7. Update dhcp-panel.service for python_portable
cat <<EOF > "$DIR/dhcp-panel.service"
[Unit]
Description=AdGuard Home DHCP Panel (Portable Instance)
After=network.target

[Service]
Type=simple
User=$(id -un)
WorkingDirectory=$DIR
ExecStart=$DIR/python_portable/bin/python3 $DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}[OK] dhcp-panel.service updated with portable instance path:${NC}"
echo "     ExecStart=$DIR/python_portable/bin/python3 $DIR/app.py"

echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}   Installation completed successfully!                           ${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "Portable instance ready at: ${CYAN}$PORTABLE_DIR${NC}"
echo -e "To start manually: ${CYAN}./start_linux.sh${NC}"
echo -e "To stop: ${CYAN}./stop_linux.sh${NC}"
echo ""
echo -e "To enable as background systemd service:"
echo -e "  ${YELLOW}sudo cp $DIR/dhcp-panel.service /etc/systemd/system/${NC}"
echo -e "  ${YELLOW}sudo systemctl daemon-reload${NC}"
echo -e "  ${YELLOW}sudo systemctl enable --now dhcp-panel${NC}"
echo ""
