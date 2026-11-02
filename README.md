# 🛡️ AdGuard Home DHCP Panel (Instancia Portable Multiplataforma)

Panel web privado y portable para la gestión integral de concesiones DHCP, asignaciones estáticas, escaneo ARP dinámico de red local y topología visual para AdGuard Home.

---

## 🚀 Instalación Automática Portable (Windows y Linux)

El repositorio incluye auto-instaladores independientes que configuran una **instancia aislada y portable de Python (`python_portable/`)**, garantizando que **no se modifica ni se contamina el Python principal del sistema ni los paquetes globales del PC**.

### 🪟 En Windows
1. Haz doble clic en **`instalar_windows.bat`** (o ejecuta `install_windows.bat`).
   * Descarga y configura automáticamente Python 3.11 Embeddable / Portable en `python_portable\`.
   * Instala las dependencias necesarias (`Flask`, `cryptography`) dentro de esa carpeta.
   * Genera el archivo `config.json` si no existe.
2. **Iniciar:** doble clic en **`iniciar_windows.bat`** (o `start_windows.bat`).
3. **Detener:** doble clic en **`detener_windows.bat`** (o `stop_windows.bat`) para cerrar la aplicación y liberar el puerto.

### 🐧 En Linux / Raspberry Pi
1. Dale permisos de ejecución y ejecuta el instalador:
   ```bash
   chmod +x instalar_linux.sh
   ./instalar_linux.sh
   ```
   * Crea una instancia aislada y portable en `python_portable/`.
   * Instala las dependencias exclusivamente en `python_portable/` (cumpliendo con PEP 668 en Debian Bookworm / Raspberry Pi OS sin tocar el Python del sistema).
   * Genera `config.json` si no existe.
   * Actualiza el servicio `dhcp-panel.service` para apuntar a la instancia portable.
2. **Iniciar manualmente:**
   ```bash
   ./iniciar_linux.sh
   ```
3. **Detener:**
   ```bash
   ./detener_linux.sh
   ```
4. O para activarlo como servicio persistente en segundo plano (systemd):
   ```bash
   sudo cp dhcp-panel.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel
   ```

---

## ⚙️ Configuración y Servicios

* **Panel Gestor DHCP:** `http://<ip-servidor>:5001` (puerto configurable en `config.json`)
* **AdGuard Home:** `http://<ip-adguard>:3000` (o el puerto configurado en tu servidor AdGuard)
  * Rutas o conexión API configurables cómodamente desde el asistente web inicial (`/setup`).

---

## 🔄 Instalación rápida en Linux / Servidores

1. Clonar el repositorio:
   ```bash
   git clone https://github.com/VictorCV-DAM/adguard-dhcp-panel-privado.git /opt/adguard-panel
   ```
2. Ejecutar auto-instalador:
   ```bash
   cd /opt/adguard-panel
   ./instalar_linux.sh
   ```
3. Activar el servicio `systemd`:
   ```bash
   sudo cp /opt/adguard-panel/dhcp-panel.service /etc/systemd/system/dhcp-panel.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel.service
   ```
4. Entrar en `http://<ip-servidor>:5001` e iniciar la configuración guiada.
5. *(Opcional)* Para restaurar un backup de leases en AdGuard Home:
   ```bash
   sudo docker stop adguardhome
   sudo cp ./leases.backup.json /ruta/hacia/adguard/data/leases.json
   sudo docker start adguardhome
   ```
