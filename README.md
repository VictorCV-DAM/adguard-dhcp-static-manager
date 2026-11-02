# 🛡️ Panel Privado — Gestor DHCP AdGuard Home (PI-Server `192.168.1.249`)

Repositorio privado con la configuración real de red doméstica (`192.168.1.0/24`), rutas de `PI-Server` (`/home/yo/dhcp-panel` y `/home/yo/servicios/...`) y copia de seguridad de las concesiones DHCP e IPs estáticas (`leases.backup.json`), **sin contraseñas almacenadas**.

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

## 📍 Datos de red y servicios en `PI-Server`

* **Raspberry Pi (`PI-Server`):** `192.168.1.249` (usuario: `yo`)
* **Panel Gestor DHCP:** `http://192.168.1.249:5001` (`/home/yo/dhcp-panel`)
* **Panel Wi-Fi original:** `http://192.168.1.249:5000` (`/home/yo/wifi-panel`)
* **AdGuard Home:** `http://192.168.1.249:8080` (usuario: `victorlike`)
  * `leases.json`: `/home/yo/servicios/adguard-work/data/leases.json`
  * `AdGuardHome.yaml`: `/home/yo/servicios/adguard-conf/AdGuardHome.yaml`
* **Router / AP TP-Link TL-WR841N:** `http://192.168.1.10` (usuario: `admin`)
* **Mercusys Halo H80X:** `192.168.1.11`, `192.168.1.12`, `192.168.1.13`

---

## 🔄 Restauración rápida en la Raspberry Pi

1. Clonar en `/home/yo/dhcp-panel`:
   ```bash
   git clone https://github.com/VictorCV-DAM/adguard-dhcp-panel-privado.git /home/yo/dhcp-panel
   ```
2. Ejecutar auto-instalador:
   ```bash
   cd /home/yo/dhcp-panel
   ./instalar_linux.sh
   ```
3. Activar el servicio `systemd`:
   ```bash
   sudo cp /home/yo/dhcp-panel/dhcp-panel.service /etc/systemd/system/dhcp-panel.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel.service
   ```
4. Entrar en `http://192.168.1.249:5001` → **⚙️ Configuraciones** e introducir las contraseñas de AdGuard Home y de los routers.
5. *(Opcional)* Para restaurar el backup de IPs estáticas en AdGuard Home:
   ```bash
   sudo docker stop adguardhome
   sudo cp /home/yo/dhcp-panel/leases.backup.json /home/yo/servicios/adguard-work/data/leases.json
   sudo docker start adguardhome
   ```
