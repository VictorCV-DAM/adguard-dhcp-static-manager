# 🛡️ AdGuard Home DHCP Panel (Cross-Platform Portable Instance)

Private, portable web management panel for AdGuard Home DHCP static leases, dynamic ARP network scanning, and interactive visual topology.

---

## 🚀 Portable Automatic Installation (Windows & Linux)

The repository provides standalone auto-installers that create an **isolated, portable Python environment (`python_portable/`)**, ensuring that **your system's primary Python installation and global packages remain completely untouched**.

### 🪟 Windows
1. Double-click **`install_windows.bat`**.
   * Automatically downloads and configures Python 3.11 Portable inside `python_portable\`.
   * Installs required dependencies (`Flask`, `cryptography`) in the portable folder.
   * Generates a clean `config.json` file if it does not already exist.
2. **Start:** Double-click **`start_windows.bat`**.
3. **Stop:** Double-click **`stop_windows.bat`** to shut down the server and release the port.

### 🐧 Linux / Raspberry Pi
1. Grant execution permissions and run the installer:
   ```bash
   chmod +x install_linux.sh
   ./install_linux.sh
   ```
   * Creates an isolated portable instance in `python_portable/`.
   * Installs dependencies exclusively inside `python_portable/` (PEP 668 compliant on Debian / Raspberry Pi OS without modifying system Python).
   * Generates `config.json` if it does not already exist.
   * Configures `dhcp-panel.service` with the portable instance path.
2. **Start manually:**
   ```bash
   ./start_linux.sh
   ```
3. **Stop:**
   ```bash
   ./stop_linux.sh
   ```
4. **Enable as persistent background service (systemd):**
   ```bash
   sudo cp dhcp-panel.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel
   ```

---

## ⚙️ Configuration & Access

* **DHCP Panel Web Interface:** `http://<server-ip>:5001` (port configurable in `config.json`)
* **AdGuard Home:** `http://<adguard-ip>:3000` (or your configured AdGuard port)
  * Set up API connection or local path easily from the initial web setup wizard (`/setup`).

---

## 🔄 Quick Server Deployment (Linux)

1. Clone repository:
   ```bash
   git clone https://github.com/VictorCV-DAM/adguard-dhcp-static-manager.git /opt/adguard-panel
   ```
2. Run installer:
   ```bash
   cd /opt/adguard-panel
   chmod +x install_linux.sh start_linux.sh stop_linux.sh
   ./install_linux.sh
   ```
3. Enable systemd service:
   ```bash
   sudo cp /opt/adguard-panel/dhcp-panel.service /etc/systemd/system/dhcp-panel.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel.service
   ```
4. Navigate to `http://<server-ip>:5001` and follow the guided setup.
