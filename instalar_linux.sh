#!/usr/bin/env bash
# ========================================================================
# Auto-instalador de AdGuard DHCP Panel Privado para Linux / Raspberry Pi
# Instala una instancia PORTABLE y aislada de Python (sin tocar tu sistema)
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
echo -e "${CYAN}   Instalador Portable - AdGuard DHCP Panel Privado (Linux)       ${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo "Directorio del proyecto: $DIR"
echo "Destino de Python portable: $PORTABLE_DIR"
echo ""

# 1. Verificar si python3 está en el sistema
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] python3 no está instalado en este sistema.${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Intentando instalar python3 con apt...${NC}"
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    else
        echo "Por favor instala python3 y vuelve a ejecutar este instalador."
        exit 1
    fi
fi

# 2. Verificar soporte para módulos virtuales (venv)
if ! python3 -m venv --help &>/dev/null; then
    echo -e "${YELLOW}[!] El módulo venv de Python no está instalado.${NC}"
    if command -v apt-get &>/dev/null; then
        echo -e "${YELLOW}Instalando python3-venv mediante apt...${NC}"
        sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
    else
        echo -e "${RED}Por favor instala el paquete python3-venv en tu distribución.${NC}"
        exit 1
    fi
fi

# 3. Crear entorno portable aislado
echo -e "${YELLOW}[1/4] Creando instancia aislada de Python en python_portable/...${NC}"
if [ -d "$PORTABLE_DIR" ] && [ -f "$PORTABLE_DIR/bin/python3" ]; then
    echo -e "${GREEN}[OK] Instancia portable existente detectada en python_portable/.${NC}"
else
    python3 -m venv "$PORTABLE_DIR"
    echo -e "${GREEN}[OK] Instancia portable creada con éxito.${NC}"
fi

# 4. Actualizar pip e instalar dependencias dentro de python_portable
echo ""
echo -e "${YELLOW}[2/4] Instalando dependencias exclusivamente en la instancia portable...${NC}"
echo -e "${CYAN}      (El Python y paquetes globales de tu Linux NO serán modificados)${NC}"

"$PORTABLE_DIR/bin/python3" -m pip install --upgrade pip

if [ -f "$REQ_FILE" ]; then
    "$PORTABLE_DIR/bin/pip" install -r "$REQ_FILE"
else
    "$PORTABLE_DIR/bin/pip" install flask cryptography
fi

# Verificar importación
if "$PORTABLE_DIR/bin/python3" -c "import flask, cryptography; print('OK')" &>/dev/null; then
    echo -e "${GREEN}[OK] Dependencias verificadas correctamente en python_portable.${NC}"
else
    echo -e "${RED}[ERROR] Error al verificar las dependencias en la instancia portable.${NC}"
    exit 1
fi

# 5. Comprobar o generar config.json
echo ""
echo -e "${YELLOW}[3/4] Comprobando archivo config.json...${NC}"
if [ ! -f "$CONFIG_FILE" ]; then
    SECRET_HEX=$(python3 -c "import secrets; print(secrets.token_hex(16))" 2>/dev/null || echo "secret_dhcp_panel_default")
    cat <<EOF > "$CONFIG_FILE"
{
  "adguard_url": "http://192.168.1.2:80",
  "adguard_user": "admin",
  "adguard_pass": "admin",
  "port": 5001,
  "debug": false,
  "home_assistant_instances": [],
  "session_secret": "$SECRET_HEX"
}
EOF
    echo -e "${GREEN}[OK] Se ha generado config.json con valores por defecto.${NC}"
else
    echo -e "${GREEN}[OK] config.json ya existe.${NC}"
fi

# 6. Crear scripts de inicio
echo ""
echo -e "${YELLOW}[4/4] Creando lanzadores de inicio...${NC}"

cat <<'EOF' > "$DIR/iniciar_linux.sh"
#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "$DIR/python_portable/bin/python3" ]; then
    exec "$DIR/python_portable/bin/python3" app.py
elif [ -f "$DIR/python_portable/bin/python" ]; then
    exec "$DIR/python_portable/bin/python" app.py
else
    echo "[ERROR] No se encontró la instancia portable en $DIR/python_portable"
    echo "Ejecuta ./instalar_linux.sh primero."
    exit 1
fi
EOF

chmod +x "$DIR/iniciar_linux.sh"
cp -f "$DIR/iniciar_linux.sh" "$DIR/start_linux.sh"
chmod +x "$DIR/start_linux.sh"

# 7. Actualizar dhcp-panel.service para usar python_portable
cat <<EOF > "$DIR/dhcp-panel.service"
[Unit]
Description=AdGuard Home DHCP Panel Privado (Instancia Portable)
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

echo -e "${GREEN}[OK] dhcp-panel.service actualizado con la ruta de la instancia portable:${NC}"
echo "     ExecStart=$DIR/python_portable/bin/python3 $DIR/app.py"

echo ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}   ¡Instalación completada con éxito!                             ${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "Instancia portable en: ${CYAN}$PORTABLE_DIR${NC}"
echo -e "Para iniciar manualmente: ${CYAN}./iniciar_linux.sh${NC} (o ./start_linux.sh)"
echo ""
echo -e "Para instalar o actualizar como servicio de inicio automático (systemd):"
echo -e "  ${YELLOW}sudo cp $DIR/dhcp-panel.service /etc/systemd/system/${NC}"
echo -e "  ${YELLOW}sudo systemctl daemon-reload${NC}"
echo -e "  ${YELLOW}sudo systemctl restart dhcp-panel${NC}"
echo ""
