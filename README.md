# 🛡️ AdGuard DHCP — Instant Static IP Manager

A lightweight **Flask (Python)** web dashboard for **Linux / Raspberry Pi** that allows you to assign or change static IP leases in **AdGuard Home's DHCP server** immediately—without lowering your global `lease_duration` and without waiting 12–24 hours for existing dynamic leases to expire.

---

## 🚀 Problem Solved

In home networks with **budget IoT devices** (ESP8266, ESP32, BL602, Sonoff, Tuya, etc.), keeping a long DHCP lease time (e.g., **12 hours / `43200 s`**) is recommended so lightweight `lwIP` stacks and Wi-Fi power-save modes (`DTIM`) are not overwhelmed by frequent DHCP renewals.

However, long DHCP lease times cause two headaches in AdGuard Home when organizing static IPs:
1. **Server-side lock in `leases.json`:** As long as an active dynamic lease or a ghost entry (`00:00:00:00:00:00`) exists in `leases.json`, AdGuard Home holds onto the previous assignment until it expires.
2. **Client-side delay:** Even after updating the DHCP server, a Wi-Fi client will not request its new IP until its lease timer (`T1`) fires or its Wi-Fi link reconnects.

### One-Click Solution (`⚡ Save + Force AP Reconnect`)
1. **Instant Purge in AdGuard Home:** Briefly stops the `adguardhome` container (~1s), removes any conflicting dynamic or ghost (`00:00:00:00:00:00`) entries for that MAC or IP from `leases.json`, writes the new static lease (`"static": true`), and starts the container again.
2. **Clean Access Point Reconnect (TP-Link TL-WR841N):** Authenticates against your Access Point's web administration API and briefly cycles the wireless interface (`LAN_WLAN`) so the client drops its old IP and immediately requests its new static IP via DHCP.
3. **Live Verification (`Ping` + `ARP` Table):** Automatically pings the new static IP and cross-checks the host's live Linux ARP table (`ip -4 neigh show`) to highlight any device still operating on a previous IP.

---

## ✨ Key Features

* **Instant Static IP Assignment & Editing** without waiting for dynamic leases to expire.
* **One-Click Junk Lease Cleanup:** Purges ghost entries (`00:00:00:00:00:00`), expired leases, and duplicate dynamic records from `leases.json`.
* **Live ARP Mismatch Detection:** Shows both the IP configured in AdGuard Home and the actual IP currently active on the LAN.
* **Built-in Settings Panel (`config.json`):** Configure your AdGuard Home URL/credentials, paths, and router/AP credentials directly from the web UI (`config.json` is excluded via `.gitignore`).
* **Quick `lease_duration` Switcher:** Update `lease_duration` in `AdGuardHome.yaml` whenever needed.

---

## 🛠️ Installation (Systemd Service)

1. Clone the repository:
   ```bash
   git clone https://github.com/VictorCV-DAM/adguard-dhcp-static-manager.git /opt/adguard-dhcp-static-manager
   cd /opt/adguard-dhcp-static-manager
   pip3 install -r requirements.txt
   cp config.example.json config.json
   ```

2. Create `/etc/systemd/system/dhcp-panel.service`:
   ```ini
   [Unit]
   Description=AdGuard DHCP Static IP Manager Web Panel
   After=network.target

   [Service]
   User=root
   WorkingDirectory=/opt/adguard-dhcp-static-manager
   ExecStart=/usr/bin/python3 /opt/adguard-dhcp-static-manager/app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now dhcp-panel.service
   ```

4. Open the dashboard in your browser:
   ```text
   http://<SERVER-IP>:5001
   ```
