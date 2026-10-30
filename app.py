from flask import Flask, render_template, request, jsonify, Response
import subprocess
import threading
import random
import hashlib
import json
import os
import re
import time
import base64
import urllib.request
import urllib.parse
import urllib.error
import http.cookiejar
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get('DHCP_MANAGER_CONFIG', os.path.join(BASE_DIR, 'config.json'))
HALO_CACHE_FILE = '/tmp/halo_topology_cache.json'

DEFAULT_CONFIG = {
    "leases_path": "/opt/adguardhome/work/data/leases.json",
    "yaml_path": "/opt/adguardhome/conf/AdGuardHome.yaml",
    "docker_container": "adguardhome",
    "adguard_url": "http://127.0.0.1:8080",
    "adguard_user": "admin",
    "adguard_pass": "",
    "routers": [
        {
            "id": "primary-ap",
            "name": "Primary TP-Link AP",
            "type": "tplink_wr841n",
            "ip": "192.168.0.2",
            "user": "admin",
            "password": "",
            "enabled": True
        },
        {
            "id": "mesh-ap",
            "name": "Mesh Wi-Fi System",
            "type": "mercusys_halo",
            "ip": "192.168.0.3, 192.168.0.4, 192.168.0.5",
            "user": "admin",
            "password": "",
            "enabled": True
        }
    ]
}

OUI_DATABASE = {
    "b8:27:eb": ("Raspberry Pi Foundation", "Server / SBC", "🍓"),
    "dc:a6:32": ("Raspberry Pi Foundation", "Server / SBC", "🍓"),
    "e4:5f:01": ("Raspberry Pi Foundation", "Server / SBC", "🍓"),
    "28:cd:c1": ("Raspberry Pi Foundation", "Server / SBC", "🍓"),
    "00:50:56": ("VMware Virtual NIC", "Virtual Machine / Server", "🖥️"),
    "00:0c:29": ("VMware Virtual NIC", "Virtual Machine / Server", "🖥️"),
    "ac:84:c6": ("TP-Link Technologies", "Router / Access Point", "🖧"),
    "e0:d3:62": ("TP-Link Technologies", "Router / Access Point", "🖧"),
    "30:16:9d": ("Mercusys / TP-Link", "Mesh Wi-Fi Node", "🖧"),
    "dc:4f:22": ("Espressif Systems (ESP8266)", "Microcontroller / IoT", "🎛️"),
    "60:01:94": ("Espressif Systems (ESP8266)", "Microcontroller / IoT", "🎛️"),
    "7c:87:ce": ("Espressif Systems (ESP32/8266)", "Microcontroller / IoT", "🎛️"),
    "e0:72:a1": ("Espressif Systems (ESP32)", "ESP Smart Lighting / Sensor", "🎛️"),
    "7c:b9:4c": ("Bouffalo Lab (BL602 Sonoff/eWeLink)", "Smart Plug / Relay IoT", "🔌"),
    "a8:80:55": ("Tuya / eWeLink Smart IoT", "Smart Plug / IoT Device", "🔌"),
    "80:64:7c": ("Sonoff / Tuya Smart", "Smart Lighting / Home IoT", "💡"),
    "08:65:f0": ("Leedarson / Tuya Smart", "Smart Bulb", "💡"),
    "3c:0b:59": ("Tuya / Smart Lighting", "Smart LED Strip / Bar", "💡"),
    "48:e1:e9": ("Meross Technology", "Smart Switch / Plug", "🔌"),
    "34:29:8f": ("Meross Technology", "Smart Switch / Plug", "🔌"),
    "c4:82:e1": ("IoT Smart Device", "Smart Home Sensor / Relay", "🔌"),
    "78:0f:77": ("BroadLink", "Universal IR / RF Hub", "📡"),
    "20:df:b9": ("Google Inc.", "Smart Speaker (Google Home)", "🔊"),
    "d4:f5:47": ("Google Inc.", "Smart Speaker (Google Nest)", "🔊"),
    "d8:8c:79": ("Google Inc.", "Smart Speaker (Nest Audio)", "🔊"),
    "dc:e5:5b": ("Google Inc.", "Smart Display (Nest Hub)", "🖥️"),
    "00:f6:20": ("Google Inc.", "Streaming Player (Chromecast)", "📺"),
    "64:9a:63": ("Ring LLC (Amazon)", "Smart Doorbell / Intercom", "🔔"),
    "78:8b:2a": ("Xiaomi / Chuangmi", "IP Security Camera", "📷"),
    "a4:f0:0f": ("IP Camera", "IP Security Camera", "📷"),
    "c4:dd:57": ("EZVIZ / Hikvision Smart", "Smart IP Camera", "📷"),
    "b4:60:ed": ("Xiaomi / Careli", "Smart Kitchen Appliance", "🍳"),
    "28:f5:2b": ("Smart Home Appliance", "Robot Vacuum", "🧹"),
    "4c:6b:b8": ("Smart TV / Media", "Smart Television", "📺"),
    "00:e0:4c": ("Realtek Semiconductor", "Ethernet Adapter / MiniPC", "🖥️"),
    "1c:bf:ce": ("2.5GbE Network Adapter", "2.5G NIC / Workstation", "🖥️"),
    "84:47:09": ("Intel / MiniPC Ethernet", "MiniPC / Home Server", "🖥️"),
    "84:9e:56": ("MiniPC Wireless", "MiniPC / Home Server", "🖥️"),
    "e8:80:88": ("Realtek / PC Ethernet", "Desktop / Gaming Laptop", "💻"),
    "d4:ab:61": ("Intel Wi-Fi", "Desktop / Gaming Laptop", "💻"),
    "48:65:ee": ("Intel Wi-Fi", "Desktop / Gaming Laptop", "💻"),
    "5c:ba:ef": ("Intel Wi-Fi", "Laptop / Notebook", "💻"),
    "ec:b5:0a": ("Mediatek Mobile", "Smartphone / Mobile Device", "📱"),
    "e8:3d:c1": ("Smart Button / BLE Gateway", "IoT Smart Button", "🔘"),
    "10:00:20": ("Apple Inc.", "iPhone / iPad", "📱"),
    "80:8a:bd": ("Samsung Electronics", "Samsung Smartphone", "📱")
}

HALO_NICKNAME_MAP = {
    "study": "Study",
    "hallway": "Hallway",
    "living_room": "Living Room",
    "livingroom": "Living Room",
    "bedroom": "Bedroom",
    "master_bedroom": "Master Bedroom",
    "kitchen": "Kitchen",
    "office": "Office",
    "garage": "Garage",
    "garden": "Garden"
}

FAVICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8"/>
      <stop offset="50%" stop-color="#0284c7"/>
      <stop offset="100%" stop-color="#1d4ed8"/>
    </linearGradient>
  </defs>
  <path d="M32 4 L56 14 V30 C56 46.5 45.8 56.8 32 61 C18.2 56.8 8 46.5 8 30 V14 Z"
        fill="url(#bg)" stroke="#7dd3fc" stroke-width="2"/>
  <path d="M32 9 L51 17.2 V30 C51 43.5 42.6 52.1 32 55.8 C21.4 52.1 13 43.5 13 30 V17.2 Z"
        fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="1.5"/>
  <path d="M22 32.5 L29 39.5 L43 24.5"
        fill="none" stroke="#ffffff" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>
</svg>"""


# =====================================================================
# RSA + AES-CBC Client for Mercusys Halo / TP-Link Mesh LuCI API
# =====================================================================
def _rsa_encrypt_pkcs1(text, n_hex, e_hex):
    n_int = int(n_hex, 16)
    e_int = int(e_hex, 16)
    k = (n_int.bit_length() + 7) // 8
    msg_bytes = text.encode('utf-8')
    ps_len = k - len(msg_bytes) - 3
    for _ in range(32):
        ps = bytes([random.randint(1, 255) for _ in range(ps_len)])
        padded = b'\x00\x02' + ps + b'\x00' + msg_bytes
        m_int = int.from_bytes(padded, 'big')
        c_int = pow(m_int, e_int, n_int)
        hex_str = format(c_int, 'x')
        if len(hex_str) % 2 == 1:
            hex_str = '0' + hex_str
        if len(hex_str) == len(n_hex):
            return hex_str
    return format(c_int, f'0{len(n_hex)}x')


def _aes_encrypt_cbc(plaintext, key_str, iv_str):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext.encode('utf-8')) + padder.finalize()
    cipher = Cipher(algorithms.AES(key_str.encode('utf-8')), modes.CBC(iv_str.encode('utf-8')))
    encryptor = cipher.encryptor()
    ct = encryptor.update(padded_data) + encryptor.finalize()
    return base64.b64encode(ct).decode('ascii')


def _aes_decrypt_cbc(b64_ct, key_str, iv_str):
    ct = base64.b64decode(b64_ct)
    cipher = Cipher(algorithms.AES(key_str.encode('utf-8')), modes.CBC(iv_str.encode('utf-8')))
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ct) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    pt = unpadder.update(padded_data) + unpadder.finalize()
    return pt.decode('utf-8')


class MercusysHaloSession:
    def __init__(self, ip, password):
        self.ip = ip
        self.password = password
        self._reset_crypto()

    def _reset_crypto(self):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))
        self.stok = ""
        self.aes_key = (str(int(time.time() * 1000)) + str(int(random.random() * 1e9)))[:16].ljust(16, '0')
        self.aes_iv = (str(int(time.time() * 1000)) + str(int(random.random() * 1e9)))[:16].ljust(16, '0')
        self.aes_key_str = f"k={self.aes_key}&i={self.aes_iv}"
        self.hash = hashlib.md5(("admin" + self.password).encode('utf-8')).hexdigest()
        self.rsa_n = None
        self.rsa_e = None
        self.seq = 0

    def _post_plain(self, path, payload, timeout=10):
        url = f"http://{self.ip}/cgi-bin/luci/;stok={self.stok}{path}"
        body = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=body, headers={
            "Referer": f"http://{self.ip}/webpages/index.html",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        })
        with self.opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))

    def _get_signature(self, seq_val, is_login=False):
        if is_login:
            s = f"{self.aes_key_str}&h={self.hash}&s={seq_val}"
        else:
            s = f"h={self.hash}&s={seq_val}"
        if len(s) > 53:
            return _rsa_encrypt_pkcs1(s[:53], self.rsa_n, self.rsa_e) + _rsa_encrypt_pkcs1(s[53:], self.rsa_n, self.rsa_e)
        return _rsa_encrypt_pkcs1(s, self.rsa_n, self.rsa_e)

    def _post_encrypted(self, path, payload, is_login=False, timeout=12):
        url = f"http://{self.ip}/cgi-bin/luci/;stok={self.stok}{path}"
        plaintext = json.dumps(payload, separators=(',', ':'))
        enc_data = _aes_encrypt_cbc(plaintext, self.aes_key, self.aes_iv)
        sign = self._get_signature(self.seq + len(enc_data), is_login=is_login)
        form_body = urllib.parse.urlencode({"sign": sign, "data": enc_data}).encode('utf-8')
        req = urllib.request.Request(url, data=form_body, headers={
            "Referer": f"http://{self.ip}/webpages/index.html",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0"
        })
        with self.opener.open(req, timeout=timeout) as r:
            raw = r.read().decode('utf-8')
        resp = json.loads(raw)
        if "data" in resp and isinstance(resp["data"], str):
            dec = _aes_decrypt_cbc(resp["data"], self.aes_key, self.aes_iv)
            return json.loads(dec)
        return resp

    def login(self):
        self._reset_crypto()
        r_keys = self._post_plain("/login?form=keys", {"operation": "read"})
        pwd_n, pwd_e = r_keys["result"]["password"]
        enc_pwd = _rsa_encrypt_pkcs1(self.password, pwd_n, pwd_e)

        r_auth = self._post_plain("/login?form=auth", {"operation": "read"})
        self.rsa_n, self.rsa_e = r_auth["result"]["key"]
        self.seq = int(r_auth["result"]["seq"])

        r_login = self._post_encrypted("/login?form=login", {
            "params": {"password": enc_pwd},
            "operation": "login"
        }, is_login=True)
        self.stok = (r_login.get("result") or r_login.get("data") or {}).get("stok", "")
        return bool(self.stok)

    def fetch_mesh_topology(self, configured_ips, ip_to_mac_hint=None):
        if not self.stok:
            if not self.login():
                return {}, {}

        ip_to_mac_hint = ip_to_mac_hint or {}
        nodes = []
        for idx, cip in enumerate(configured_ips):
            cip = cip.strip()
            if not cip:
                continue
            mac_colon = ip_to_mac_hint.get(cip, "")
            if mac_colon:
                nodes.append({
                    "device_ip": cip,
                    "mac": mac_colon.upper().replace(":", "-"),
                    "role": "master" if idx == 0 else "slave",
                    "nickname": f"Node {idx + 1}"
                })

        # 1. Always query device_list first to initialize internal mesh topology in Halo firmware
        nodes = []
        try:
            devs = self._post_encrypted("/admin/device?form=device_list", {"operation": "read"}, timeout=10)
            dev_list = (devs.get("result") or devs.get("data") or {}).get("device_list", [])
            if dev_list:
                nodes = dev_list
        except Exception:
            pass

        # 2. Fallback to configured IPs if device_list failed
        if not nodes:
            for idx, cip in enumerate(configured_ips):
                cip = cip.strip()
                if not cip:
                    continue
                mac_colon = ip_to_mac_hint.get(cip, "")
                if mac_colon:
                    nodes.append({
                        "device_ip": cip,
                        "mac": mac_colon.upper().replace(":", "-"),
                        "role": "master" if idx == 0 else "slave",
                        "nickname": f"Node {idx + 1}"
                    })

        if not nodes:
            return {}, {}

        ip_index_map = {ip.strip(): idx + 1 for idx, ip in enumerate(configured_ips) if ip.strip()}
        nodes_sorted = sorted(
            nodes,
            key=lambda d: (ip_index_map.get(d.get("device_ip", ""), 99), 0 if d.get("role") == "master" else 1)
        )

        node_info_by_ip = {}
        client_map = {}

        master_label = "Halo 1"
        for idx, d in enumerate(nodes_sorted):
            dip = d.get("device_ip", "")
            raw_nick = (d.get("nickname") or "").strip()
            nick = HALO_NICKNAME_MAP.get(raw_nick.lower(), raw_nick)
            num = ip_index_map.get(dip, idx + 1)
            short_name = f"Halo {num}" + (f" ({nick})" if nick and nick != f"Node {num}" else "")
            if d.get("role") == "master":
                master_label = short_name

        for idx, d in enumerate(nodes_sorted):
            dmac = d.get("mac", "")
            dip = d.get("device_ip", "")
            role = d.get("role", "slave")
            raw_nick = (d.get("nickname") or "").strip()
            nick = HALO_NICKNAME_MAP.get(raw_nick.lower(), raw_nick)
            num = ip_index_map.get(dip, idx + 1)
            node_label = f"Halo {num}" + (f" ({nick})" if nick and nick != f"Node {num}" else "")

            if role == "master":
                node_info_by_ip[dip] = {
                    "label": f"{node_label} · Master Node",
                    "tooltip": f"Mesh Master Node ({dip}) · MAC {dmac}"
                }
            else:
                node_info_by_ip[dip] = {
                    "label": f"{node_label} · Mesh → {master_label}",
                    "tooltip": f"Mesh Satellite Node ({dip}) connected to {master_label} · MAC {dmac}"
                }

            try:
                c_resp = self._post_encrypted(
                    "/admin/client?form=client_list",
                    {"operation": "read", "params": {"device_mac": dmac}},
                    timeout=15
                )
                if c_resp.get("error_code") in ("timeout", -5001):
                    if self.login():
                        c_resp = self._post_encrypted(
                            "/admin/client?form=client_list",
                            {"operation": "read", "params": {"device_mac": dmac}},
                            timeout=15
                        )
                clist = (c_resp.get("result") or c_resp.get("data") or {}).get("client_list", [])
                for c in clist:
                    cmac = (c.get("mac") or "").strip().lower().replace("-", ":")
                    if not cmac:
                        continue
                    conn_type = (c.get("connection_type") or "").lower()
                    if conn_type in ("band5", "band5_2"):
                        band_str, band_full = "5G", "Wi-Fi 5 GHz"
                        medium, medium_label = "wifi", "Wi-Fi 5 GHz"
                    elif conn_type == "band2_4":
                        band_str, band_full = "2.4G", "Wi-Fi 2.4 GHz"
                        medium, medium_label = "wifi", "Wi-Fi 2.4 GHz"
                    elif conn_type == "wired":
                        band_str, band_full = "LAN", "Wired Ethernet"
                        medium, medium_label = "cable", "Wired Ethernet"
                    else:
                        band_str, band_full = conn_type, conn_type
                        medium, medium_label = "wifi", "Wi-Fi"

                    try:
                        cname = base64.b64decode(c.get("name", "")).decode("utf-8", errors="ignore").strip()
                    except Exception:
                        cname = (c.get("name") or "").strip()
                    if cname.upper() == "UNKNOWN":
                        cname = ""

                    display_label = f"{node_label} · {band_str}" if band_str else node_label
                    tooltip = f"Connected to {node_label} ({dip}) via {band_full}"
                    if cname:
                        tooltip += f" | Mesh Name: {cname}"

                    client_map[cmac] = {
                        "node_label": display_label,
                        "node_short": node_label,
                        "node_ip": dip,
                        "band": band_str,
                        "halo_name": cname,
                        "client_type": (c.get("client_type") or "").lower(),
                        "online": bool(c.get("online", True)),
                        "medium": medium,
                        "medium_label": medium_label,
                        "tooltip": tooltip
                    }
            except Exception:
                pass

        return client_map, node_info_by_ip


_HALO_SESSIONS = {}
_HALO_CACHE = {
    "timestamp": 0.0,
    "client_map": {},
    "node_info_by_ip": {},
    "refreshing": False
}
_HALO_LOCK = threading.Lock()


def _load_halo_disk_cache():
    if _HALO_CACHE["client_map"]:
        return
    if os.path.exists(HALO_CACHE_FILE):
        try:
            with open(HALO_CACHE_FILE, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                _HALO_CACHE["client_map"] = saved.get("client_map", {})
                _HALO_CACHE["node_info_by_ip"] = saved.get("node_info_by_ip", {})
                _HALO_CACHE["timestamp"] = float(saved.get("timestamp", 0.0))
        except Exception:
            pass


def _refresh_halo_cache_sync(router, ip_to_mac_hint=None):
    ips = [x.strip() for x in (router.get("ip") or "").split(",") if x.strip()]
    if not ips or not router.get("password"):
        _HALO_CACHE["refreshing"] = False
        return
    master_ip = ips[0]
    pwd = router.get("password").strip()
    key = f"{master_ip}:{pwd}"

    try:
        with _HALO_LOCK:
            session = _HALO_SESSIONS.get(key)
            if not session:
                session = MercusysHaloSession(master_ip, pwd)
                _HALO_SESSIONS[key] = session
            cmap, ninfo = session.fetch_mesh_topology(ips, ip_to_mac_hint)
            if cmap or ninfo:
                now_ts = time.time()
                if cmap:
                    _HALO_CACHE["client_map"] = cmap
                if ninfo:
                    _HALO_CACHE["node_info_by_ip"] = ninfo
                _HALO_CACHE["timestamp"] = now_ts
                try:
                    with open(HALO_CACHE_FILE, 'w', encoding='utf-8') as f:
                        json.dump({
                            "timestamp": now_ts,
                            "client_map": _HALO_CACHE["client_map"],
                            "node_info_by_ip": _HALO_CACHE["node_info_by_ip"]
                        }, f)
                except Exception:
                    pass
    finally:
        _HALO_CACHE["refreshing"] = False


def get_mercusys_halo_data(router, ip_to_mac_hint=None, wait_if_empty=False):
    _load_halo_disk_cache()
    now = time.time()
    age = now - _HALO_CACHE["timestamp"]

    if not _HALO_CACHE["client_map"]:
        _HALO_CACHE["refreshing"] = True
        _refresh_halo_cache_sync(router, ip_to_mac_hint)
    elif age > 25.0 and not _HALO_CACHE["refreshing"]:
        _HALO_CACHE["refreshing"] = True
        t = threading.Thread(target=_refresh_halo_cache_sync, args=(router, ip_to_mac_hint), daemon=True)
        t.start()

    return _HALO_CACHE["client_map"], _HALO_CACHE["node_info_by_ip"]


def is_locally_administered_mac(mac):
    try:
        first_byte = int(mac.split(':')[0], 16)
        return bool(first_byte & 0b00000010)
    except Exception:
        return False


def predict_device_info(hostname, mac, halo_info=None):
    halo_name = (halo_info or {}).get("halo_name", "")
    halo_type = (halo_info or {}).get("client_type", "")
    h = f"{hostname or ''} {halo_name}".lower()
    m = (mac or '').lower()
    oui = m[:8]

    vendor_info = OUI_DATABASE.get(oui)
    vendor_name = vendor_info[0] if vendor_info else None
    if halo_name and halo_name.lower() not in (hostname or '').lower():
        vendor_name = f"{vendor_name} · {halo_name}" if vendor_name else f"Mesh: {halo_name}"

    if any(k in h for k in ['mercusys', 'halo', 'tplink', 'mikrotik', 'router', 'tp-link', 'ap-']):
        return "Router / Access Point", vendor_name or "Network Infrastructure", "🖧", "infra"
    if any(k in h for k in ['enchufe', 'switch', 'plug', 'meross']):
        return "Smart Plug / Switch", vendor_name or "Wi-Fi Smart Relay", "🔌", "iot"
    if any(k in h for k in ['bulb', 'tira-led', 'barra-de-luz', 'luces', 'ambilight', 'ambiligth', 'led']):
        return "Smart Lighting", vendor_name or "Wi-Fi Smart LED", "💡", "iot"
    if any(k in h for k in ['pulsador', 'button', 'sensor']):
        return "Smart Button / Sensor", vendor_name or "IoT Sensor", "🔘", "iot"
    if any(k in h for k in ['camera', 'cam', 'ipcam', 'ipc0', 'ipc1', 'ring', 't30-', 'chuangmi', 'ezviz']) or re.search(r'(^|[\-_ ])ipc', h):
        return "IP Camera / Doorbell", vendor_name or "IP Security", "📷", "security"
    if any(k in h for k in ['pi-server', 'raspberry']):
        return "Server / Raspberry Pi", vendor_name or "Raspberry Pi", "🍓", "server"
    if any(k in h for k in ['ha-vm', 'homeassistant', 'vm']):
        return "Server / Virtual Machine", vendor_name or "Hypervisor VM", "🖥️", "server"
    if any(k in h for k in ['minipc', 'server', 'gmktec']):
        return "MiniPC / Local Server", vendor_name or "Home Server", "🖥️", "server"
    if any(k in h for k in ['legion', 'laptop', 'desktop', 'adapt-2.5g']) or re.search(r'(^|[\-_ ])pc([\-_ ]|$)', h):
        return "PC / Laptop", vendor_name or "Personal Computer", "💻", "pc"
    if any(k in h for k in ['brli', 'broadlink', 'ir-rf', 'rmpro']):
        return "Universal IR/RF Remote", vendor_name or "BroadLink", "📡", "iot"
    if any(k in h for k in ['esp-', 'esp_', 'esp32', 'esp8266', 'lwip', 'bl602', 'bouffalo']):
        return "IoT Microcontroller", vendor_name or "ESP / BL602 Chip", "🎛️", "iot"
    if any(k in h for k in ['google-home', 'nest-mini', 'nest-audio']):
        return "Smart Speaker", vendor_name or "Google Nest", "🔊", "media"
    if any(k in h for k in ['nest-hub', 'echo-show']):
        return "Smart Display", vendor_name or "Google Nest Hub", "🖥️", "media"
    if any(k in h for k in ['chromecast', 'tv-del-', 'smart-tv', 'box']):
        return "Smart TV / Streaming", vendor_name or "Media Player", "📺", "media"
    if any(k in h for k in ['fryer', 'sweeper', 'vacuum', 'careli', 'autopack']):
        return "Smart Home Appliance", vendor_name or "Smart Appliance", "🏠", "iot"
    if any(k in h for k in ['tab-', 'galaxy-tab', 'ipad']):
        return "Tablet", vendor_name or "Android / iOS Tablet", "📱", "mobile"
    if any(k in h for k in ['iphone', 'galaxy', 's10', 'a40', 'a50', 'sm-', 'realme', 'oppo', 'oneplus', 'honor', 'oukitel', 'samsung']):
        return "Smartphone", vendor_name or "Android / iOS Phone", "📱", "mobile"

    if vendor_info:
        return vendor_info[1], vendor_name, vendor_info[2], "iot"

    if halo_type == "iot_device":
        return "Smart IoT Device", vendor_name or f"OUI {oui.upper()}", "🔌", "iot"
    if halo_type == "phone":
        return "Smartphone", vendor_name or "Mobile Device", "📱", "mobile"

    if is_locally_administered_mac(m):
        return "Smartphone / Tablet (Private MAC)", vendor_name or "Randomized MAC (iOS / Android)", "📱", "mobile"

    return "Network / IoT Device", vendor_name or f"OUI {oui.upper()}", "❓", "other"


def is_wireless_only_device(dev_class, dev_cat, hostname, mac):
    """Determines whether a device lacks an Ethernet port by physical hardware design."""
    wireless_classes = {
        "Smart Speaker",
        "Smart Display",
        "Smart Lighting",
        "Smart Plug / Switch",
        "Smart Button / Sensor",
        "Universal IR/RF Remote",
        "IoT Microcontroller",
        "Smart Home Appliance",
        "Smartphone",
        "Tablet",
        "Smartphone / Tablet (Private MAC)",
        "Smart IoT Device",
        "IP Camera / Doorbell",
        "Smart TV / Streaming"
    }
    if dev_class in wireless_classes:
        return True
    if dev_cat in ("iot", "mobile"):
        return True
    h = (hostname or "").lower()
    if any(k in h for k in [
        "wifi", "wlan", "nest", "google", "meross", "tuya", "sonoff", "bulb",
        "esp-", "esp_", "esp32", "esp8266", "ring", "tab-", "chuangmi",
        "bl602", "lwip", "t30-", "smart"
    ]):
        return True
    if is_locally_administered_mac(mac):
        return True
    return False


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                saved = json.load(f)
                if 'routers' not in saved:
                    routers = []
                    if saved.get('tplink_ip') or saved.get('tplink_pass'):
                        routers.append({
                            "id": "primary-ap",
                            "name": "Primary TP-Link AP",
                            "type": "tplink_wr841n",
                            "ip": saved.get('tplink_ip', '192.168.0.2'),
                            "user": saved.get('tplink_user', 'admin'),
                            "password": saved.get('tplink_pass', ''),
                            "enabled": bool(saved.get('tplink_enabled', True))
                        })
                    if saved.get('halo_ip') or saved.get('halo_pass'):
                        routers.append({
                            "id": "mesh-ap",
                            "name": "Mesh Wi-Fi System",
                            "type": "mercusys_halo",
                            "ip": saved.get('halo_ip', '192.168.0.3, 192.168.0.4, 192.168.0.5'),
                            "user": "admin",
                            "password": saved.get('halo_pass', ''),
                            "enabled": True
                        })
                    saved['routers'] = routers or DEFAULT_CONFIG['routers']
                cfg.update(saved)
        except Exception:
            pass
    return cfg


def save_config(new_cfg):
    cfg = load_config()
    for k in ('leases_path', 'yaml_path', 'docker_container', 'adguard_url', 'adguard_user', 'adguard_pass'):
        if k in new_cfg:
            cfg[k] = new_cfg[k]
    if 'routers' in new_cfg and isinstance(new_cfg['routers'], list):
        cfg['routers'] = new_cfg['routers']
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    _HALO_CACHE["timestamp"] = 0.0
    return cfg


def run_sudo(cmd_list):
    return subprocess.run(['sudo'] + cmd_list, capture_output=True, text=True, timeout=30)


def read_leases():
    cfg = load_config()
    res = run_sudo(['cat', cfg['leases_path']])
    if res.returncode != 0 or not res.stdout.strip():
        return {"version": 1, "leases": []}
    return json.loads(res.stdout)


def write_leases(data):
    cfg = load_config()
    payload = json.dumps(data, separators=(',', ':'))
    proc = subprocess.run(
        ['sudo', 'tee', cfg['leases_path']],
        input=payload,
        capture_output=True,
        text=True,
        timeout=15
    )
    return proc.returncode == 0


def get_lease_duration():
    cfg = load_config()
    res = run_sudo(['cat', cfg['yaml_path']])
    if res.returncode != 0:
        return 43200
    m = re.search(r'dhcpv4:.*?lease_duration:\s*(\d+)', res.stdout, re.DOTALL)
    return int(m.group(1)) if m else 43200


def set_lease_duration_yaml(seconds):
    cfg = load_config()
    res = run_sudo(['cat', cfg['yaml_path']])
    if res.returncode != 0:
        return False
    content = res.stdout
    new_content = re.sub(
        r'(dhcpv4:.*?lease_duration:\s*)\d+',
        rf'\g<1>{int(seconds)}',
        content,
        count=1,
        flags=re.DOTALL
    )
    proc = subprocess.run(
        ['sudo', 'tee', cfg['yaml_path']],
        input=new_content,
        capture_output=True,
        text=True,
        timeout=15
    )
    return proc.returncode == 0


def get_arp_table():
    arp = {}
    res = subprocess.run(['ip', '-4', 'neigh', 'show'], capture_output=True, text=True)
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            parts = line.split()
            if 'lladdr' in parts and 'FAILED' not in parts:
                ip = parts[0]
                idx = parts.index('lladdr')
                if idx + 1 < len(parts):
                    mac = parts[idx + 1].lower()
                    arp.setdefault(mac, []).append(ip)
    return arp


def query_router_associated_macs(router):
    rtype = router.get('type', 'tplink_wr841n')
    first_ip = (router.get('ip') or '').split(',')[0].strip()
    user = (router.get('user') or 'admin').strip()
    pwd = (router.get('password') or '').strip()

    if rtype == 'tplink_wr841n' and first_ip and pwd:
        token = base64.b64encode(f"{user}:{pwd}".encode('utf-8')).decode('ascii')
        headers = {
            'Cookie': f'Authorization=Basic {token}',
            'Referer': f'http://{first_ip}/',
            'Content-Type': 'text/plain'
        }
        try:
            req = urllib.request.Request(
                f'http://{first_ip}/cgi?5',
                data=b'[LAN_WLAN_ASSOC_DEV#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n',
                headers=headers,
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                body = resp.read().decode('utf-8', errors='ignore')
                macs = set()
                for line in body.splitlines():
                    if line.startswith('associatedDeviceMACAddress='):
                        mac = line.split('=', 1)[1].strip().lower()
                        if mac:
                            macs.add(mac)
                return macs
        except Exception:
            return set()
    return set()


def trigger_router_reconnect(router, mac):
    rtype = router.get('type', 'tplink_wr841n')
    name = router.get('name', 'AP')
    first_ip = (router.get('ip') or '').split(',')[0].strip()
    user = (router.get('user') or 'admin').strip()
    pwd = (router.get('password') or '').strip()

    if rtype == 'tplink_wr841n':
        if not pwd:
            return False, f"Password for {name} is not configured."
        token = base64.b64encode(f"{user}:{pwd}".encode('utf-8')).decode('ascii')
        headers = {
            'Cookie': f'Authorization=Basic {token}',
            'Referer': f'http://{first_ip}/',
            'Content-Type': 'text/plain'
        }
        try:
            try:
                req_off = urllib.request.Request(
                    f'http://{first_ip}/cgi?2',
                    data=b'[LAN_WLAN#1,1,0,0,0,0#0,0,0,0,0,0]0,1\r\nenable=0\r\n',
                    headers=headers,
                    method='POST'
                )
                urllib.request.urlopen(req_off, timeout=6).read()
            except Exception:
                pass

            time.sleep(2)

            for _ in range(3):
                try:
                    req_on = urllib.request.Request(
                        f'http://{first_ip}/cgi?2',
                        data=b'[LAN_WLAN#1,1,0,0,0,0#0,0,0,0,0,0]0,1\r\nenable=1\r\n',
                        headers=headers,
                        method='POST'
                    )
                    urllib.request.urlopen(req_on, timeout=6).read()
                    break
                except Exception:
                    time.sleep(1)
            return True, f"Wi-Fi reconnect triggered on {name}."
        except Exception:
            return True, f"Wi-Fi restart command sent to {name}."

    return False, f"Router {name} ({rtype}) is registered for topology only."


def ping_ip(ip):
    res = subprocess.run(['ping', '-c', '1', '-W', '1', ip], capture_output=True, text=True)
    return res.returncode == 0


def test_adguard_credentials(cfg):
    url = (cfg.get('adguard_url') or 'http://127.0.0.1:8080').rstrip('/')
    user = (cfg.get('adguard_user') or '').strip()
    pwd = (cfg.get('adguard_pass') or '').strip()
    if not user or not pwd:
        return False, "AdGuard Home username or password is empty."
    try:
        cj = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        payload = json.dumps({'name': user, 'password': pwd}).encode('utf-8')
        req = urllib.request.Request(
            f"{url}/control/login",
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with opener.open(req, timeout=5) as resp:
            if resp.status == 200:
                return True, "AdGuard Home API authentication successful."
    except Exception as e:
        return False, f"AdGuard Home login error: {str(e)}"
    return False, "Could not authenticate with AdGuard Home."


def ip_sort_key(ip_str):
    try:
        return [int(x) for x in ip_str.split('.')]
    except Exception:
        return [999, 999, 999, 999]


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/favicon.svg')
@app.route('/favicon.ico')
def favicon():
    return Response(FAVICON_SVG, mimetype='image/svg+xml')


@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'GET':
        return jsonify({'status': 'success', 'config': load_config()})
    new_cfg = request.json or {}
    saved = save_config(new_cfg)
    msgs = [f"Configuration saved ({len(saved.get('routers', []))} router(s) configured)."]
    if saved.get('adguard_pass'):
        _, msg_ag = test_adguard_credentials(saved)
        msgs.append(msg_ag)
    return jsonify({'status': 'success', 'message': ' | '.join(msgs), 'config': saved})


@app.route('/api/state', methods=['GET'])
def api_state():
    cfg = load_config()
    routers = cfg.get('routers', [])
    data = read_leases()
    leases = data.get('leases', [])
    arp = get_arp_table()
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    router_mac_map = {}
    halo_client_map = {}
    halo_node_info = {}
    infra_ips = set()
    fallback_lan_name = 'Main Router / LAN'

    ip_to_mac_hint = {}
    for m_arp, ips_arp in arp.items():
        for ip_a in ips_arp:
            ip_to_mac_hint[ip_a] = m_arp
    for l in leases:
        if l.get('ip') and l.get('mac') and l.get('mac') != '00:00:00:00:00:00':
            ip_to_mac_hint[l['ip']] = l['mac'].lower()

    for r in routers:
        if not r.get('enabled', True):
            continue
        rname = r.get('name') or 'Router'
        rtype = r.get('type')
        for rip in (r.get('ip') or '').split(','):
            if rip.strip():
                infra_ips.add(rip.strip())

        if rtype == 'tplink_wr841n':
            assoc_macs = query_router_associated_macs(r)
            for m in assoc_macs:
                router_mac_map[m] = {
                    "label": rname,
                    "type": "tplink",
                    "tooltip": f"Connected via Wi-Fi to {rname} ({r.get('ip')})"
                }
        elif rtype == 'mercusys_halo':
            cmap, ninfo = get_mercusys_halo_data(r, ip_to_mac_hint=ip_to_mac_hint, wait_if_empty=False)
            halo_client_map.update(cmap)
            halo_node_info.update(ninfo)

    ghost_count = 0
    expired_count = 0
    devices = []
    seen_leases = set()

    for l in leases:
        mac = (l.get('mac') or '').lower()
        ip = l.get('ip') or ''
        is_static = bool(l.get('static'))
        expires = l.get('expires') or ''
        hostname = l.get('hostname') or ''

        if mac == '00:00:00:00:00:00':
            ghost_count += 1
            continue
        if ':' in ip:
            continue

        # Prevent duplicate rows if AdGuard Home stored duplicate leases with the same (MAC, IP)
        lease_key = (mac, ip)
        if lease_key in seen_leases:
            continue
        seen_leases.add(lease_key)

        is_expired = False
        if not is_static and expires and expires != '0001-01-01T00:00:00Z':
            if expires < now_iso:
                is_expired = True
                expired_count += 1

        live_ips = list(arp.get(mac, []))
        halo_info = halo_client_map.get(mac)
        if halo_info and halo_info.get("online") and ip and ip not in live_ips:
            live_ips.append(ip)

        mismatch_ip = None
        for lip in live_ips:
            if lip != ip:
                mismatch_ip = lip

        dev_class, dev_vendor, dev_icon, dev_cat = predict_device_info(hostname, mac, halo_info)
        is_wireless = is_wireless_only_device(dev_class, dev_cat, hostname, mac)

        router_tooltip = ""
        conn_medium = "offline"
        conn_medium_label = "Offline"

        if ip in halo_node_info:
            router_node = halo_node_info[ip]["label"]
            router_tooltip = halo_node_info[ip]["tooltip"]
            router_type = 'infra'
            conn_medium = 'cable'
            conn_medium_label = 'Wired Ethernet'
        elif ip in infra_ips or 'mercusys-halo' in hostname.lower() or 'tplink' in hostname.lower():
            router_node = 'Router / AP Node'
            router_tooltip = f'Network infrastructure device ({ip})'
            router_type = 'infra'
            conn_medium = 'cable'
            conn_medium_label = 'Wired Ethernet'
        elif mac in router_mac_map:
            router_node = router_mac_map[mac]["label"]
            router_tooltip = router_mac_map[mac]["tooltip"]
            router_type = router_mac_map[mac]["type"]
            conn_medium = 'wifi'
            conn_medium_label = 'Wi-Fi 2.4 GHz'
        elif halo_info:
            router_node = halo_info["node_label"]
            router_tooltip = halo_info["tooltip"]
            router_type = 'halo'
            conn_medium = halo_info.get("medium", "wifi")
            conn_medium_label = halo_info.get("medium_label", "Wi-Fi")
        elif live_ips:
            if is_wireless:
                router_node = 'Wi-Fi Access Point'
                router_tooltip = 'Active wireless network device (Wi-Fi)'
                router_type = 'wifi'
                conn_medium = 'wifi'
                conn_medium_label = 'Wi-Fi'
            else:
                router_node = fallback_lan_name
                router_tooltip = 'Connected via wired Ethernet / Switch'
                router_type = 'lan'
                conn_medium = 'cable'
                conn_medium_label = 'Wired Ethernet'
        else:
            router_node = 'Offline'
            router_tooltip = 'No recent activity in ARP or Wi-Fi nodes'
            router_type = 'offline'
            conn_medium = 'offline'
            conn_medium_label = 'Offline'

        devices.append({
            'hostname': hostname or '(Unnamed)',
            'mac': mac,
            'ip': ip,
            'static': is_static,
            'expires': expires,
            'expired': is_expired,
            'live_ips': live_ips,
            'mismatch_ip': mismatch_ip,
            'router_node': router_node,
            'router_tooltip': router_tooltip,
            'router_type': router_type,
            'conn_medium': conn_medium,
            'conn_medium_label': conn_medium_label,
            'dev_class': dev_class,
            'dev_vendor': dev_vendor,
            'dev_icon': dev_icon,
            'dev_cat': dev_cat
        })

    devices.sort(key=lambda d: (not d['static'], ip_sort_key(d['ip'])))

    return jsonify({
        'status': 'success',
        'lease_duration': get_lease_duration(),
        'ghost_count': ghost_count,
        'expired_count': expired_count,
        'devices': devices
    })


@app.route('/api/assign-static', methods=['POST'])
def api_assign_static():
    req = request.json or {}
    mac = (req.get('mac') or '').strip().lower()
    ip = (req.get('ip') or '').strip()
    hostname = (req.get('hostname') or '').strip()
    force_reconnect = bool(req.get('force_reconnect', False))

    if not mac or not ip or not hostname:
        return jsonify({'status': 'error', 'message': 'MAC, IP, and Hostname are required.'})

    cfg = load_config()
    container = cfg.get('docker_container', 'adguardhome')

    run_sudo(['docker', 'stop', container])
    removed = 0
    try:
        data = read_leases()
        old_leases = data.get('leases', [])
        new_leases = []

        for l in old_leases:
            l_mac = (l.get('mac') or '').lower()
            l_ip = (l.get('ip') or '').strip()
            if l_mac == mac or l_ip == ip:
                removed += 1
                continue
            new_leases.append(l)

        new_leases.append({
            'expires': '',
            'ip': ip,
            'hostname': hostname,
            'mac': mac,
            'static': True
        })

        data['leases'] = new_leases
        write_leases(data)
    finally:
        run_sudo(['docker', 'start', container])

    msg = f'Static IP {ip} assigned to {hostname} ({mac}). ({removed} conflicting lease(s) purged).'

    if force_reconnect:
        reconnected = False
        for r in cfg.get('routers', []):
            if r.get('enabled', True) and r.get('type') == 'tplink_wr841n' and r.get('password'):
                ok, ap_msg = trigger_router_reconnect(r, mac)
                msg += f' | {ap_msg}'
                if ok:
                    reconnected = True
        if reconnected:
            time.sleep(4)
            if ping_ip(ip):
                msg += f' | Ping to {ip} OK!'
            else:
                msg += f' | Waiting for ping reply on {ip}...'

    return jsonify({'status': 'success', 'message': msg})


@app.route('/api/ping', methods=['POST'])
def api_ping():
    req = request.json or {}
    ip = (req.get('ip') or '').strip()
    alive = ping_ip(ip)
    return jsonify({
        'status': 'success',
        'alive': alive,
        'message': f'Ping to {ip} succeeded! Device is active on this IP.' if alive else f'No ping reply from {ip} yet.'
    })


@app.route('/api/delete-lease', methods=['POST'])
def api_delete_lease():
    req = request.json or {}
    mac = (req.get('mac') or '').strip().lower()
    ip = (req.get('ip') or '').strip()

    cfg = load_config()
    container = cfg.get('docker_container', 'adguardhome')

    run_sudo(['docker', 'stop', container])
    try:
        data = read_leases()
        old_leases = data.get('leases', [])
        new_leases = [
            l for l in old_leases
            if not ((l.get('mac') or '').lower() == mac and (l.get('ip') or '') == ip)
        ]
        data['leases'] = new_leases
        write_leases(data)
    finally:
        run_sudo(['docker', 'start', container])

    return jsonify({'status': 'success', 'message': f'Lease {ip} ({mac}) removed successfully.'})


@app.route('/api/clean-junk', methods=['POST'])
def api_clean_junk():
    now_iso = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    cfg = load_config()
    container = cfg.get('docker_container', 'adguardhome')

    run_sudo(['docker', 'stop', container])
    removed_count = 0
    try:
        data = read_leases()
        old_leases = data.get('leases', [])
        static_macs = {
            (l.get('mac') or '').lower()
            for l in old_leases
            if l.get('static')
        }
        static_ips = {
            (l.get('ip') or '').strip()
            for l in old_leases
            if l.get('static')
        }

        clean_leases = []
        seen_dynamic_macs = set()

        for l in old_leases:
            mac = (l.get('mac') or '').lower()
            ip = (l.get('ip') or '').strip()
            is_static = bool(l.get('static'))
            expires = l.get('expires') or ''

            if is_static:
                clean_leases.append(l)
                continue

            if mac == '00:00:00:00:00:00':
                removed_count += 1
                continue

            if mac in static_macs or ip in static_ips:
                removed_count += 1
                continue

            if expires and expires != '0001-01-01T00:00:00Z' and expires < now_iso:
                removed_count += 1
                continue

            if mac in seen_dynamic_macs:
                removed_count += 1
                continue

            seen_dynamic_macs.add(mac)
            clean_leases.append(l)

        data['leases'] = clean_leases
        write_leases(data)
    finally:
        run_sudo(['docker', 'start', container])

    return jsonify({
        'status': 'success',
        'message': f'Cleanup complete: removed {removed_count} ghost, expired, or duplicate lease(s).'
    })


@app.route('/api/set-duration', methods=['POST'])
def api_set_duration():
    req = request.json or {}
    seconds = int(req.get('seconds', 43200))
    cfg = load_config()
    container = cfg.get('docker_container', 'adguardhome')

    run_sudo(['docker', 'stop', container])
    try:
        set_lease_duration_yaml(seconds)
    finally:
        run_sudo(['docker', 'start', container])
    return jsonify({
        'status': 'success',
        'message': f'DHCP lease duration updated to {seconds} seconds ({seconds // 60} min).'
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
