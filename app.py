from flask import Flask, render_template, request, jsonify, Response, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from datetime import timedelta
import extras
import subprocess
import threading
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor
import socket
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
    "custom_service_names": {},
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
    "00:14:5c": ("Eminent / Intronics (EM4590)", "Repeater / Access Point", "📶"),
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
    "80:8a:bd": ("Samsung Electronics", "Samsung Smartphone", "📱"),
    "bc:35:1e": ("Tuya Smart Inc.", "Smart Plug / Switch", "🔌"),
    "fc:3c:d7": ("Tuya Smart Inc.", "Smart Plug / Switch", "🔌"),
    "d4:ad:fc": ("Shenzhen Intellirocks (Govee)", "Smart Lighting", "💡"),
    "d8:c8:0c": ("Tuya Smart Inc.", "Smart Light Bulb", "💡"),
    "c0:f8:53": ("Tuya Smart Inc.", "Smart Home IoT", "🔌"),
    "f8:17:2d": ("Tuya / Espressif", "Smart Home IoT", "🔌"),
    "3c:8d:20": ("Google Inc.", "Google Nest Device", "🔊")
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
    try:
        unpadder = padding.PKCS7(128).unpadder()
        pt = unpadder.update(padded_data) + unpadder.finalize()
        return pt.decode('utf-8')
    except Exception:
        last_brace = padded_data.rfind(b'}')
        if last_brace != -1:
            try:
                return padded_data[:last_brace + 1].decode('utf-8', errors='ignore')
            except Exception:
                pass
        return padded_data.rstrip(b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10').decode('utf-8', errors='ignore')


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

    def trigger_wifi_reconnect(self):
        """Dispara una recarga/reconexión Wi-Fi en el nodo maestro Halo guardando la configuración WLAN."""
        try:
            if not self.stok:
                if not self.login():
                    return False, "Error de autenticación en Mercusys Halo"
            wlan_data = self._post_encrypted("/admin/wireless?form=wlan", {"operation": "read"})
            res = wlan_data.get('result', {})
            if not res:
                return False, "No se pudo leer la configuración WLAN de Halo"
            write_res = self._post_encrypted("/admin/wireless?form=wlan", {
                "operation": "write",
                "params": res
            })
            if write_res.get('error_code') == 0:
                return True, "Reconexión Wi-Fi recargada en Mercusys Halo."
            return False, f"Respuesta Halo: {write_res.get('msg', 'error')}"
        except Exception as e:
            return False, f"Excepción en Halo: {e}"

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

        # 2. Fallback to configured IPs if device_list failed or incomplete
        known_halo_fallback = [
            {"device_ip": "192.168.1.11", "mac": "30-16-9D-2B-61-54", "role": "master", "nickname": "Halo 1"},
            {"device_ip": "192.168.1.12", "mac": "30-16-9D-2B-62-60", "role": "slave", "nickname": "Halo 2"},
            {"device_ip": "192.168.1.13", "mac": "30-16-9D-2B-5F-F0", "role": "slave", "nickname": "Halo 3"}
        ]
        if not nodes or len(nodes) < len(known_halo_fallback):
            for idx, cip in enumerate(configured_ips):
                cip = cip.strip()
                if not cip:
                    continue
                if any(n.get("device_ip") == cip for n in nodes):
                    continue
                mac_colon = ip_to_mac_hint.get(cip, "")
                if not mac_colon:
                    matched_k = next((k for k in known_halo_fallback if k["device_ip"] == cip), None)
                    if matched_k:
                        mac_colon = matched_k["mac"].lower().replace("-", ":")
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
                    "node_short": node_label,
                    "role": "master",
                    "tooltip": f"Mesh Master Node ({dip}) · MAC {dmac}"
                }
            else:
                node_info_by_ip[dip] = {
                    "label": f"{node_label} · Mesh → {master_label}",
                    "node_short": node_label,
                    "role": "slave",
                    "parent_node": master_label,
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

                    display_label = node_label
                    tooltip = f"Connected to {node_label} ({dip}) via {band_full}"
                    if cname:
                        tooltip += f" | Mesh Name: {cname}"

                    client_map[cmac] = {
                        "node_label": display_label,
                        "node_short": node_label,
                        "node_full": f"{node_label} · {band_str}" if band_str else node_label,
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
                    _HALO_CACHE["client_map"].update(cmap)
                if ninfo:
                    _HALO_CACHE["node_info_by_ip"].update(ninfo)
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
        _HALO_CACHE["timestamp"] = time.time()
        _HALO_CACHE["refreshing"] = False


def get_mercusys_halo_data(router, ip_to_mac_hint=None, wait_if_empty=False):
    _load_halo_disk_cache()
    now = time.time()
    age = now - _HALO_CACHE["timestamp"]

    if not _HALO_CACHE["client_map"]:
        _HALO_CACHE["refreshing"] = True
        _refresh_halo_cache_sync(router, ip_to_mac_hint)
    elif age > 90.0 and not _HALO_CACHE["refreshing"]:
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
        "Smart TV / Streaming",
        "Robot Vacuum"
    }
    if dev_class in wireless_classes:
        return True
    if dev_cat in ("iot", "mobile", "media"):
        return True
    if dev_class in ("Network / IoT Device", "Smart IoT Device", "Smart Home IoT"):
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


import ssl

SSL_UNVERIFIED_CTX = ssl.create_default_context()
SSL_UNVERIFIED_CTX.check_hostname = False
SSL_UNVERIFIED_CTX.verify_mode = ssl.CERT_NONE

_SERVICE_SCAN_CACHE = {}  # {ip: (timestamp, [verified_service_dicts])}

CANDIDATE_WEB_PORTS = [
    80, 81, 443, 1984, 2283, 2342, 3000, 3001, 32400, 4040, 4200, 4357, 4533, 5000, 5001, 5050, 5055,
    5173, 5678, 6052, 6789, 7000, 7001, 7878, 8000, 8006, 8080, 8081, 8082, 8085, 8086,
    8087, 8088, 8090, 8096, 8099, 8123, 8325, 8384, 8443, 8581, 8686, 8880, 8888, 8889,
    8989, 9000, 9090, 9091, 9443, 9584, 10000, 19999
]

def probe_http_service(ip, port):
    """Verifies whether a port on a host is a real, accessible HTTP/HTTPS web service."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.08)
        r = s.connect_ex((ip, port))
        s.close()
        if r != 0:
            return None
    except Exception:
        return None

    # Probe real HTTP or HTTPS
    protos = ['https', 'http'] if port in (443, 8006, 8443, 9443) else ['http', 'https']
    for proto in protos:
        url = f"{proto}://{ip}:{port}/" if port not in (80, 443) else f"{proto}://{ip}/"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=0.45, context=SSL_UNVERIFIED_CTX if proto == 'https' else None) as resp:
                code = resp.getcode()
                content = resp.read(4096).decode('utf-8', errors='ignore')
                title_m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                title = title_m.group(1).strip() if title_m else ""
                server = resp.headers.get('Server', '')
                return {'port': port, 'proto': proto, 'url': url, 'code': code, 'title': title, 'server': server, 'body': content}
        except urllib.error.HTTPError as e:
            # Only allow auth challenges or genuine web redirects (exclude 404 to skip headless API endpoints)
            if e.code in (401, 403, 301, 302, 307, 308):
                content = e.read(2048).decode('utf-8', errors='ignore') if e.fp else ""
                title_m = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                title = title_m.group(1).strip() if title_m else ""
                return {'port': port, 'proto': proto, 'url': url, 'code': e.code, 'title': title, 'server': e.headers.get('Server', ''), 'body': content}
        except Exception:
            continue
    return None


def scan_device_verified_services(ip):
    """Scans candidate ports concurrently and returns only verified web services."""
    ip = (ip or '').strip()
    if not ip or ip in ('0.0.0.0', '127.0.0.1') or ':' in ip:
        return []
    with ThreadPoolExecutor(max_workers=min(25, len(CANDIDATE_WEB_PORTS))) as pool:
        results = [r for r in pool.map(lambda p: probe_http_service(ip, p), CANDIDATE_WEB_PORTS) if r]
    return results


def get_device_web_links(ip, hostname="", dev_class="", dev_cat="", routers=None, halo_node_info=None, is_active=True, custom_service_names=None):
    """Returns strictly real and verified web management links."""
    ip = (ip or '').strip()
    if not ip or ip in ('0.0.0.0', '127.0.0.1') or ':' in ip or not is_active:
        return []

    h_lower = (hostname or '').lower()
    c_lower = (dev_class or '').lower()
    routers = routers or []
    halo_node_info = halo_node_info or {}
    custom_names = custom_service_names or {}

    is_router_cfg = False
    router_name = ""
    for r in routers:
        r_ips = [x.strip() for x in (r.get('ip') or '').split(',') if x.strip()]
        if ip in r_ips:
            is_router_cfg = True
            router_name = r.get('name') or 'Router'
            break

    is_router = (ip in ('192.168.1.1', '192.168.0.1') or is_router_cfg or 'router' in c_lower or 'mercusys-halo' in h_lower or ip in halo_node_info or dev_cat == 'infra')

    now = time.time()
    cached = _SERVICE_SCAN_CACHE.get(ip)
    if cached and (now - cached[0]) < 180:
        verified_services = cached[1]
    else:
        verified_services = scan_device_verified_services(ip)
        _SERVICE_SCAN_CACHE[ip] = (now, verified_services)

    links = []
    seen_urls = set()

    def add_link(label, url, port=None):
        if url not in seen_urls:
            seen_urls.add(url)
            clean_u = url.rstrip('/')
            custom = custom_names.get(url) or custom_names.get(clean_u) or (custom_names.get(f"{ip}:{port}") if port else None)
            is_custom = False
            default_label = label
            if custom:
                label = custom
                is_custom = True
            item = {'label': label, 'url': url, 'default_label': default_label, 'is_custom': is_custom}
            if port is not None:
                item['port'] = int(port)
            links.append(item)

    for item in verified_services:
        port = item['port']
        proto = item['proto']
        url = item['url']
        title = item.get('title', '').strip()
        body = item.get('body', '')
        t_low = title.lower()
        b_low = body.lower()

        # Intelligent SPA detection and known services recognition
        if 'immich' in b_low or 'immich' in t_low or port == 2283:
            label = f"Immich (:{port})"
        elif port == 32400 or 'plex' in b_low or 'plex' in t_low:
            url = f"http://{ip}:32400/web"
            label = "Plex Media Server (:32400)"
        elif 'quota monitor' in t_low or 'quota monitor' in b_low or (port == 5050 and 'quota' in b_low):
            label = "Antigravity Quota Monitor (:5050)"
        elif port == 81 or 'nginx proxy manager' in t_low:
            label = "Nginx Proxy Manager (:81)"
        elif port == 8082 and ('nginx proxy manager' in b_low or 'congratulations' in b_low or 'default site' in t_low):
            label = "NPM Test / Default Site (:8082)"
        elif 'home assistant observer' in t_low or 'observer' in b_low or port == 4357:
            label = "HA Observer (:4357)"
        elif 'home assistant' in t_low or port == 8123:
            label = "Home Assistant (:8123)"
        elif 'broadlink' in t_low or 'broadlink' in b_low or port == 8099:
            label = "Broadlink Manager v2 (:8099)"
        elif 'ewelink' in t_low or 'ewelink' in b_low or port == 8325:
            label = "eWeLink Smart Home (:8325)"
        elif 'go2rtc' in t_low or 'go2rtc' in b_low or port == 1984:
            label = "go2rtc WebRTC (:1984)"
        elif ip == '192.168.1.249' and port == 8080:
            label = "AdGuard Home (:8080)"
        elif ip == '192.168.1.249' and port == 5001:
            label = "DHCP Panel (:5001)"
        elif ip == '192.168.1.249' and port == 5000:
            label = "Wi-Fi Panel (:5000)"
        elif ip in ('192.168.1.1', '192.168.0.1'):
            label = f"Gateway Router ({proto.upper()})"
        elif ip == '192.168.1.9' or 'em4590' in h_lower:
            label = f"Wi-Fi Repeater EM4590 ({proto.upper()})"
        elif ip in ('192.168.1.10', '192.168.0.2') or 'wr841n' in h_lower:
            label = f"TP-Link WR841N ({proto.upper()})"
        elif ip in halo_node_info or 'mercusys-halo' in h_lower:
            lbl = halo_node_info.get(ip, {}).get('label', f'Halo Node ({ip})')
            label = f"{lbl} ({proto.upper()})"
        elif is_router_cfg:
            label = f"{router_name} ({proto.upper()})"
        elif 'proxmox' in b_low or 'proxmox' in t_low or port == 8006:
            label = "Proxmox VE (:8006)"
        elif 'portainer' in b_low or 'portainer' in t_low or port in (9000, 9443):
            label = f"Portainer ({proto.upper()} :{port})"
        elif 'jellyfin' in b_low or 'jellyfin' in t_low or port == 8096:
            label = f"Jellyfin (:{port})"
        elif 'vaultwarden' in b_low or 'bitwarden' in b_low:
            label = f"Vaultwarden (:{port})"
        elif 'syncthing' in b_low or port == 8384:
            label = f"Syncthing (:{port})"
        elif 'uptime kuma' in b_low or port == 3001:
            label = f"Uptime Kuma (:{port})"
        elif 'grafana' in b_low or (port == 3000 and 'grafana' in t_low):
            label = "Grafana (:3000)"
        elif title and len(title) < 40 and not any(k in t_low for k in ['http 40', '404', 'error', 'default site', 'unauthorized']):
            label = f"{title} (:{port})"
        elif is_router:
            label = f"Router Web UI ({proto.upper()})"
        else:
            label = f"Web ({proto.upper()})" if port in (80, 443) else f"Web Service (:{port})"

        add_link(label, url, port=port)

    return links


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


def save_config_raw(cfg):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    _HALO_CACHE["timestamp"] = 0.0
    return cfg


def save_config(new_cfg):
    cfg = load_config()
    for k in ('leases_path', 'yaml_path', 'docker_container', 'adguard_url', 'adguard_user', 'adguard_pass'):
        if k in new_cfg:
            cfg[k] = new_cfg[k]
    if 'custom_service_names' in new_cfg and isinstance(new_cfg['custom_service_names'], dict):
        cfg['custom_service_names'] = new_cfg['custom_service_names']
    if 'routers' in new_cfg and isinstance(new_cfg['routers'], list):
        cfg['routers'] = new_cfg['routers']
    return save_config_raw(cfg)


def run_sudo(cmd_list):
    return subprocess.run(['sudo'] + cmd_list, capture_output=True, text=True, timeout=30)


def check_adguard_available():
    """Comprueba si AdGuard Home está configurado y accesible (vía archivo local o API)."""
    try:
        if os.path.exists(LEASES_PATH) or os.path.exists(YAML_PATH):
            return True
        cfg = load_config()
        url = (cfg.get('adguard_url') or '').strip()
        user = (cfg.get('adguard_user') or '').strip()
        pwd = (cfg.get('adguard_pass') or '').strip()
        if not url:
            return False
        req = urllib.request.Request(f"{url.rstrip('/')}/control/status", headers={'User-Agent': 'DHCP-Panel'})
        if user and pwd:
            b64 = base64.b64encode(f"{user}:{pwd}".encode()).decode()
            req.add_header('Authorization', f'Basic {b64}')
        with urllib.request.urlopen(req, timeout=1.8) as r:
            return r.status == 200
    except Exception:
        return False


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
    """Ejecuta la orden de reconexión Wi-Fi en el router indicado."""
    rtype = router.get('type', 'tplink_wr841n')
    name = router.get('name', 'AP')
    first_ip = (router.get('ip') or '').split(',')[0].strip()
    user = (router.get('user') or 'admin').strip()
    pwd = (router.get('password') or '').strip()

    if rtype == 'mercusys_halo':
        if not pwd:
            return False, f"Contraseña de {name} no configurada."
        session = MercusysHaloSession(first_ip, pwd)
        return session.trigger_wifi_reconnect()

    if rtype == 'tplink_wr841n':
        if not pwd:
            return False, f"Contraseña de {name} no configurada."
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
            return True, f"Reconexión Wi-Fi aplicada en {name}."
        except Exception:
            return True, f"Orden de reinicio Wi-Fi enviada a {name}."

    return False, f"El router {name} ({rtype}) está registrado para topología pero no soporta reconexión directa."


def ping_ip(ip):
    res = subprocess.run(['ping', '-c', '1', '-W', '1', ip], capture_output=True, text=True)
    return res.returncode == 0


def verify_ip_l2(ip, target_mac=None, iface="eth0", timeout=2):
    """Verifica si una IP responde en Layer 2 (ARP) y si coincide con la MAC objetivo."""
    if not ip:
        return False, None
    try:
        res = subprocess.run(
            ['sudo', 'arping', '-c', '2', '-w', str(timeout), '-I', iface, ip],
            capture_output=True, text=True, timeout=timeout + 2
        )
        output = res.stdout or ''
        if 'Received 0 response' in output or res.returncode != 0:
            arp_table = get_arp_table()
            if target_mac and target_mac.lower() in arp_table:
                if ip in arp_table[target_mac.lower()]:
                    return True, target_mac.lower()
            return False, None

        found_macs = re.findall(r'\[([0-9a-fA-F:]{17})\]', output)
        reply_mac = found_macs[0].lower() if found_macs else None

        if target_mac and reply_mac:
            clean_target = target_mac.lower().replace('-', ':')
            if reply_mac == clean_target:
                return True, reply_mac
            else:
                return False, reply_mac
        return True, reply_mac
    except Exception:
        alive = ping_ip(ip)
        return alive, None

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
    return render_template('index.html', auth_user=session.get('user', ''))


# ==========================================================================
#  AUTHENTICATION (login, "keep me signed in", password change, revocation)
# ==========================================================================
AUTH_PATH = os.environ.get('DHCP_PANEL_AUTH_PATH') or os.path.join(os.path.dirname(CONFIG_PATH), 'auth.json')
_AUTH_LOCK = threading.Lock()
_LOGIN_ATTEMPTS = {}  # {ip: [failed attempt timestamps]}
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_SEC = 300
REMEMBER_DAYS = 365


def load_auth():
    data = {}
    if os.path.exists(AUTH_PATH):
        try:
            with open(AUTH_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
        except Exception:
            data = {}
    changed = False
    if not data.get('secret_key'):
        data['secret_key'] = secrets.token_hex(32)
        changed = True
    if 'session_version' not in data:
        data['session_version'] = 1
        changed = True
    if changed:
        save_auth(data)
    return data


def save_auth(data):
    with _AUTH_LOCK:
        tmp = AUTH_PATH + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, AUTH_PATH)
        try:
            os.chmod(AUTH_PATH, 0o600)
        except Exception:
            pass


_AUTH_BOOT = load_auth()
app.secret_key = _AUTH_BOOT['secret_key']
app.config.update(
    SESSION_COOKIE_NAME='dhcp_panel_session',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    PERMANENT_SESSION_LIFETIME=timedelta(days=REMEMBER_DAYS),
)


def auth_configured():
    a = load_auth()
    return bool(a.get('username') and a.get('password_hash'))


def is_logged_in():
    if not session.get('user'):
        return False
    a = load_auth()
    return session.get('user') == a.get('username') and session.get('sv') == a.get('session_version')


def _client_ip():
    return request.remote_addr or 'unknown'


def _too_many_attempts(ip):
    now = time.time()
    for k in list(_LOGIN_ATTEMPTS.keys()):
        _LOGIN_ATTEMPTS[k] = [t for t in _LOGIN_ATTEMPTS[k] if now - t < LOGIN_WINDOW_SEC]
        if not _LOGIN_ATTEMPTS[k]:
            _LOGIN_ATTEMPTS.pop(k, None)
    total = sum(len(v) for v in _LOGIN_ATTEMPTS.values())
    return len(_LOGIN_ATTEMPTS.get(ip, [])) >= LOGIN_MAX_ATTEMPTS or total >= LOGIN_MAX_ATTEMPTS * 6


PUBLIC_ENDPOINTS = {'login', 'logout', 'setup', 'favicon', 'static'}


@app.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not auth_configured():
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'auth_required': True, 'message': 'Create an admin user first.'}), 401
        return redirect(url_for('setup'))
    if is_logged_in():
        return None
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'auth_required': True, 'message': 'Session expired. Please sign in again.'}), 401
    return redirect(url_for('login', next=request.path))


def _start_session(username, remember):
    a = load_auth()
    session.clear()
    session['user'] = username
    session['sv'] = a.get('session_version', 1)
    session.permanent = bool(remember)


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if auth_configured():
        return redirect(url_for('login'))
    error = ''
    if request.method == 'POST':
        user = (request.form.get('username') or '').strip()
        pw = request.form.get('password') or ''
        pw2 = request.form.get('password2') or ''
        if len(user) < 3:
            error = 'Username must be at least 3 characters.'
        elif len(pw) < 6:
            error = 'Password must be at least 6 characters.'
        elif pw != pw2:
            error = 'Passwords do not match.'
        else:
            a = load_auth()
            a['username'] = user
            a['password_hash'] = generate_password_hash(pw)
            save_auth(a)
            _start_session(user, request.form.get('remember') == 'on')
            return redirect(url_for('index'))
    return render_template('login.html', mode='setup', error=error)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if not auth_configured():
        return redirect(url_for('setup'))
    if is_logged_in():
        return redirect(url_for('index'))
    error = ''
    ip = _client_ip()
    if request.method == 'POST':
        if _too_many_attempts(ip):
            error = f'Too many failed attempts. Please wait {LOGIN_WINDOW_SEC // 60} minutes.'
        else:
            user = (request.form.get('username') or '').strip()
            pw = request.form.get('password') or ''
            a = load_auth()
            if user == a.get('username') and check_password_hash(a.get('password_hash', ''), pw):
                _LOGIN_ATTEMPTS.pop(ip, None)
                _start_session(user, request.form.get('remember') == 'on')
                nxt = request.args.get('next') or '/'
                if not nxt.startswith('/') or nxt.startswith('//'):
                    nxt = '/'
                return redirect(nxt)
            _LOGIN_ATTEMPTS.setdefault(ip, []).append(time.time())
            left = LOGIN_MAX_ATTEMPTS - len(_LOGIN_ATTEMPTS[ip])
            error = 'Invalid username or password.' + (f' {left} attempt(s) remaining.' if left > 0 else '')
    return render_template('login.html', mode='login', error=error)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/auth/change-password', methods=['POST'])
def api_change_password():
    req = request.json or {}
    current = req.get('current') or ''
    new_pw = req.get('new') or ''
    new_user = (req.get('username') or '').strip()
    a = load_auth()
    if not check_password_hash(a.get('password_hash', ''), current):
        return jsonify({'status': 'error', 'message': 'Current password is incorrect.'})
    if new_user and len(new_user) < 3:
        return jsonify({'status': 'error', 'message': 'Username must be at least 3 characters.'})
    if new_pw and len(new_pw) < 6:
        return jsonify({'status': 'error', 'message': 'New password must be at least 6 characters.'})
    if new_user:
        a['username'] = new_user
    if new_pw:
        a['password_hash'] = generate_password_hash(new_pw)
    a['session_version'] = int(a.get('session_version', 1)) + 1
    save_auth(a)
    _start_session(a['username'], session.permanent)
    return jsonify({'status': 'success', 'message': 'Credentials updated. All other open sessions have been signed out.'})


@app.route('/api/auth/logout-all', methods=['POST'])
def api_logout_all():
    a = load_auth()
    a['session_version'] = int(a.get('session_version', 1)) + 1
    save_auth(a)
    _start_session(a['username'], session.permanent)
    return jsonify({'status': 'success', 'message': 'All other sessions on other devices have been signed out.'})


@app.route('/api/auth/me', methods=['GET'])
def api_auth_me():
    return jsonify({'status': 'success', 'user': session.get('user'), 'remember': bool(session.permanent)})


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


def probe_router_http(ip):
    """Probes an IP on port 80 searching for signatures of known router/AP web interfaces."""
    url = f"http://{ip}/"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            status = resp.status
            final_url = resp.geturl()
            raw_body = resp.read()
            text = raw_body.decode("utf-8", errors="ignore")
            headers = dict(resp.headers)

            # Detect HTML meta-refresh (e.g. Mercusys redirecting to /webpages/index.html)
            m_refresh = re.search(r'<meta[^>]+http-equiv=["\']refresh["\'][^>]+content=["\'][^;]+;\s*URL=([^"\']+)["\']', text, re.IGNORECASE)
            if m_refresh:
                redir_target = m_refresh.group(1).strip()
                redir_url = f"http://{ip}" + ("/" if not redir_target.startswith("/") else "") + redir_target if not redir_target.startswith("http") else redir_target
                try:
                    req_redir = urllib.request.Request(redir_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                    with urllib.request.urlopen(req_redir, timeout=1.5) as r2:
                        final_url = r2.geturl()
                        text_redir = r2.read().decode("utf-8", errors="ignore")
                        text += "\n" + text_redir
                except Exception:
                    pass

            return ip, True, status, final_url, text, headers
    except urllib.error.HTTPError as e:
        raw_body = e.read(65536) if hasattr(e, "read") else b""
        text = raw_body.decode("utf-8", errors="ignore")
        return ip, True, e.code, e.geturl() if hasattr(e, "geturl") else url, text, dict(e.headers)
    except Exception:
        return ip, False, 0, url, "", {}


def discover_network_routers(current_routers=None):
    """Scans the local network discovering routers/access points and returns candidate configs."""
    cfg = load_config()
    existing_list = current_routers if current_routers is not None else cfg.get('routers', [])

    candidates = set()
    # 1. Common default gateway and router infrastructure IPs
    for gip in ["192.168.1.1", "192.168.1.10", "192.168.1.11", "192.168.1.12", "192.168.1.13", "192.168.1.254", "192.168.0.1", "192.168.0.254"]:
        candidates.add(gip)

    # 2. AdGuard Home active leases
    leases_data = read_leases()
    for l in leases_data.get('leases', []):
        lip = l.get('ip')
        if lip:
            candidates.add(lip)

    # 3. ARP table entries
    arp_table = get_arp_table()
    for mac, ip_list in arp_table.items():
        for aip in ip_list:
            if aip:
                candidates.add(aip)

    # 4. Currently configured router IPs
    for r in existing_list:
        for rip in (r.get('ip') or '').split(','):
            rip_s = rip.strip()
            if rip_s:
                candidates.add(rip_s)

    # Discard loopback and local host IP
    candidates.discard("192.168.1.249")
    candidates.discard("127.0.0.1")

    # Concurrent probing
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(probe_router_http, sorted(list(candidates))))

    discovered = []
    for ip, success, status, final_url, text, headers in results:
        if not success and status == 0:
            continue
        auth_header = ""
        server = ""
        for hk, hv in headers.items():
            hk_l = hk.lower()
            if hk_l == "www-authenticate":
                auth_header = str(hv).lower()
            elif hk_l == "server":
                server = str(hv).lower()

        m_title = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
        title = m_title.group(1).strip() if m_title else ""
        title_lower = title.lower()

        # 1. Mercusys Halo Mesh
        if "webpages/index.html" in final_url or "ozkersubs" in text or "su.url.ozkersubs" in text or "mercusys" in text.lower() or "halo" in text.lower():
            discovered.append({
                "ip": ip,
                "type": "mercusys_halo",
                "name": "Mercusys Halo H80X",
                "user": "admin"
            })
        # 2. TP-Link CGI / Web interface
        elif "modelName=" in text or "modelDesc=" in text or "tplinklogin.net" in text or "tplinkwifi.net" in text or "tpInput.js" in text or "/userRpm/" in text:
            m_name = re.search(r'var\s+modelName\s*=\s*["\']([^"\']+)["\']', text)
            m_desc = re.search(r'var\s+modelDesc\s*=\s*["\']([^"\']+)["\']', text)
            model_name = m_name.group(1).strip() if m_name else ""
            model_desc = m_desc.group(1).strip() if m_desc else ""

            if "TL-WR841N" in model_name or "WR841N" in model_desc:
                disp_name = "TP-Link WR841N"
                rtype = "tplink_wr841n"
            elif model_name:
                disp_name = f"TP-Link {model_name}" + (f" ({model_desc})" if model_desc and model_desc != model_name else "")
                rtype = "tplink_wr841n" if ip != "192.168.1.1" else "generic_ap"
            elif model_desc:
                disp_name = model_desc
                rtype = "tplink_wr841n"
            else:
                disp_name = "TP-Link Router"
                rtype = "tplink_wr841n"

            discovered.append({
                "ip": ip,
                "type": rtype,
                "name": disp_name,
                "user": "admin"
            })
        # 3. MikroTik RouterOS
        elif "routeros" in server or "mikrotik" in text.lower() or "/webfig/" in text.lower():
            discovered.append({
                "ip": ip,
                "type": "mikrotik_rest",
                "name": "MikroTik RouterOS",
                "user": "admin"
            })
        # 4. OpenWrt / LuCI
        elif "luci" in text.lower() or "openwrt" in text.lower():
            discovered.append({
                "ip": ip,
                "type": "generic_ap",
                "name": "OpenWrt / LuCI AP",
                "user": "root"
            })
        # 5. Wi-Fi Repeater (e.g. Eminent EM4590, Realtek RTL8196/RTL8192, Boa server with Wifi-Repeater realm)
        elif "wifi-repeater" in auth_header or "repeater" in auth_header or "em4590" in auth_header or "realtek" in text.lower() or ("boa" in server and ("repeater" in auth_header or "router" in auth_header or "wireless" in auth_header or "wireless" in title_lower)):
            mac_candidate = ""
            for m_k, ips_k in arp_table.items():
                if ip in ips_k:
                    mac_candidate = m_k.lower()
                    break
            is_eminent = "wifi-repeater" in auth_header or "em4590" in auth_header or mac_candidate.startswith("00:14:5c")
            disp_name = "Wi-Fi Repeater EM4590 (Eminent)" if is_eminent else "Wi-Fi Repeater / AP"
            discovered.append({
                "ip": ip,
                "type": "generic_ap",
                "name": disp_name,
                "user": "admin"
            })
        # 6. Generic router web interface or HTTP auth
        elif title and any(k in title_lower for k in ["router", "ap", "access point", "modem", "gateway", "fibra", "wifi", "livebox"]):
            discovered.append({
                "ip": ip,
                "type": "generic_ap",
                "name": title,
                "user": "admin"
            })
        elif auth_header and any(k in auth_header for k in ["router", "gateway", "access point", "ap"]):
            discovered.append({
                "ip": ip,
                "type": "generic_ap",
                "name": f"Access Point / Router ({ip})",
                "user": "admin"
            })

    # Grouping & merging logic
    halo_ips = []
    other_discovered = []
    for d in discovered:
        if d["type"] == "mercusys_halo":
            halo_ips.append(d["ip"])
        else:
            other_discovered.append(d)

    final_routers = []

    # 1. Mercusys Halo Mesh group
    if halo_ips:
        sorted_halo_ips = sorted(halo_ips, key=lambda x: [int(p) if p.isdigit() else 0 for p in x.split('.')])
        joined_halo_ips = ", ".join(sorted_halo_ips)
        matched = None
        for r in existing_list:
            r_ips = [x.strip() for x in r.get("ip", "").split(",") if x.strip()]
            if any(hip in r_ips for hip in halo_ips) or r.get("type") == "mercusys_halo":
                matched = r
                break
        if matched:
            item = dict(matched)
            item["ip"] = joined_halo_ips
            final_routers.append(item)
        else:
            final_routers.append({
                "id": f"mercusys-halo-{int(time.time())}",
                "name": "Mercusys Halo H80X",
                "type": "mercusys_halo",
                "ip": joined_halo_ips,
                "user": "admin",
                "password": "",
                "enabled": True
            })

    # 2. Other discovered routers
    for d in other_discovered:
        dip = d["ip"]
        matched = None
        for r in existing_list:
            r_ips = [x.strip() for x in r.get("ip", "").split(",") if x.strip()]
            if dip in r_ips:
                matched = r
                break
        if matched:
            item = dict(matched)
            final_routers.append(item)
        else:
            final_routers.append({
                "id": f"router-{dip.replace('.', '-')}",
                "name": d["name"],
                "type": d["type"],
                "ip": dip,
                "user": d.get("user", "admin"),
                "password": "",
                "enabled": True
            })

    # 3. Preserve user-configured routers that may be offline during scan
    for r in existing_list:
        r_id = r.get("id")
        already_included = any(fr.get("id") == r_id for fr in final_routers)
        if not already_included:
            r_ips = [x.strip() for x in r.get("ip", "").split(",") if x.strip()]
            ip_included = any(any(rip in fr.get("ip", "") for rip in r_ips) for fr in final_routers)
            if not ip_included:
                final_routers.append(r)

    names = [r.get("name") or r.get("ip") for r in final_routers]
    msg = f"Discovered {len(final_routers)} router(s)/access point(s) on your network ({', '.join(names)})."
    return final_routers, msg


@app.route('/api/discover-routers', methods=['GET', 'POST'])
def api_discover_routers():
    payload = request.json if (request.is_json and request.json) else {}
    current_routers = payload.get('current_routers')
    discovered_list, msg = discover_network_routers(current_routers=current_routers)
    return jsonify({
        'status': 'success',
        'message': msg,
        'routers': discovered_list
    })


def build_state(force_refresh=False):
    cfg = load_config()
    adguard_available = check_adguard_available()
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
            if cmap or ninfo:
                halo_client_map.update(cmap)
                halo_node_info.update(ninfo)
            elif _HALO_CACHE.get("client_map") or _HALO_CACHE.get("node_info_by_ip"):
                halo_client_map.update(_HALO_CACHE.get("client_map", {}))
                halo_node_info.update(_HALO_CACHE.get("node_info_by_ip", {}))

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

        is_infra_node = (
            ip in halo_node_info or ip in infra_ips or
            any(k in hostname.lower() for k in ['mercusys-halo', 'wr841n', 'em4590']) or
            dev_class in ["Router / Access Point", "Repeater / Access Point"]
        )

        if ip in halo_node_info:
            raw_lbl = halo_node_info[ip].get("node_short") or halo_node_info[ip]["label"]
            router_node = re.sub(r'\s*·.*$', '', raw_lbl).strip()
            router_tooltip = halo_node_info[ip]["tooltip"]
            router_type = 'infra'
            conn_medium = 'cable'
            conn_medium_label = 'Wired Ethernet'
        elif ip in ('192.168.1.1', '192.168.1.249') or 'gateway' in hostname.lower() or 'xg-pon' in hostname.lower() or 'xgb430v' in hostname.lower():
            router_node = 'Gateway / LAN'
            router_tooltip = f'Core Gateway device ({ip})'
            router_type = 'infra'
            conn_medium = 'cable'
            conn_medium_label = 'Wired Ethernet'
        elif is_infra_node:
            if 'wr841n' in hostname.lower() or ip == '192.168.1.10':
                router_node = 'TP-Link WR841N'
            elif 'em4590' in hostname.lower() or ip == '192.168.1.9':
                router_node = 'Wi-Fi Repeater EM4590'
            else:
                router_node = hostname or 'AP / Router'
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
            router_node = halo_info.get("node_short") or halo_info["node_label"]
            router_tooltip = halo_info["tooltip"]
            router_type = 'halo'
            conn_medium = halo_info.get("medium", "wifi")
            conn_medium_label = halo_info.get("medium_label", "Wi-Fi")
        elif live_ips:
            if is_wireless:
                router_node = 'Gateway / Wi-Fi'
                router_tooltip = 'Wireless device connected to primary gateway (192.168.1.1)'
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
            'dev_cat': dev_cat,
            'web_links': [],
            'open_ports': []
        })

    seen_ips = {d['ip'] for d in devices if d.get('ip')}

    # Active devices detected via ARP without an AdGuard DHCP lease (e.g. manual static IPs / infrastructure)
    for arp_mac, arp_ips in arp.items():
        m = (arp_mac or '').lower()
        if m in ('', '00:00:00:00:00:00'):
            continue
        for aip in arp_ips:
            if not aip or ':' in aip or aip in seen_ips:
                continue
            if aip in ('127.0.0.1', '192.168.1.249'):
                continue

            hostname = ""
            for r in routers:
                r_ips = [x.strip() for x in (r.get('ip') or '').split(',') if x.strip()]
                if aip in r_ips:
                    hostname = r.get('name') or ''
                    break

            if not hostname:
                if aip == '192.168.1.1':
                    hostname = 'gateway-router'
                elif m.startswith('00:14:5c') or aip == '192.168.1.9':
                    hostname = 'wifi-repeater-em4590'
                else:
                    hostname = f"device-{aip.replace('.', '-')}"

            halo_info = halo_client_map.get(m)
            dev_class, dev_vendor, dev_icon, dev_cat = predict_device_info(hostname, m, halo_info)
            is_wireless = is_wireless_only_device(dev_class, dev_cat, hostname, m)

            is_infra_node = (
                aip in halo_node_info or aip in infra_ips or
                any(k in hostname.lower() for k in ['mercusys-halo', 'wr841n', 'em4590']) or
                dev_class in ["Router / Access Point", "Repeater / Access Point"]
            )

            router_tooltip = ""
            if aip in halo_node_info:
                raw_lbl = halo_node_info[aip].get("node_short") or halo_node_info[aip]["label"]
                router_node = re.sub(r'\s*·.*$', '', raw_lbl).strip()
                router_tooltip = halo_node_info[aip]["tooltip"]
                router_type = 'infra'
                conn_medium = 'cable'
                conn_medium_label = 'Wired Ethernet'
            elif aip in ('192.168.1.1', '192.168.1.249') or 'gateway' in hostname.lower() or 'xg-pon' in hostname.lower() or 'xgb430v' in hostname.lower():
                router_node = 'Gateway / LAN'
                router_tooltip = f'Core Gateway device ({aip})'
                router_type = 'infra'
                conn_medium = 'cable'
                conn_medium_label = 'Wired Ethernet'
            elif is_infra_node:
                if 'wr841n' in hostname.lower() or aip == '192.168.1.10':
                    router_node = 'TP-Link WR841N'
                elif 'em4590' in hostname.lower() or aip == '192.168.1.9':
                    router_node = 'Wi-Fi Repeater EM4590'
                else:
                    router_node = hostname or 'AP / Router'
                router_tooltip = f'Network infrastructure device ({aip})'
                router_type = 'infra'
                conn_medium = 'cable'
                conn_medium_label = 'Wired Ethernet'
            elif m in router_mac_map:
                router_node = router_mac_map[m]["label"]
                router_tooltip = router_mac_map[m]["tooltip"]
                router_type = router_mac_map[m]["type"]
                conn_medium = 'wifi'
                conn_medium_label = 'Wi-Fi 2.4 GHz'
            elif halo_info:
                router_node = halo_info.get("node_short") or halo_info["node_label"]
                router_tooltip = halo_info["tooltip"]
                router_type = 'halo'
                conn_medium = halo_info.get("medium", "wifi")
                conn_medium_label = halo_info.get("medium_label", "Wi-Fi")
            else:
                if is_wireless:
                    router_node = 'Gateway / Wi-Fi'
                    router_tooltip = 'Wireless device connected to primary gateway (192.168.1.1)'
                    router_type = 'wifi'
                    conn_medium = 'wifi'
                    conn_medium_label = 'Wi-Fi'
                else:
                    router_node = fallback_lan_name
                    router_tooltip = 'Connected via wired Ethernet / Switch'
                    router_type = 'lan'
                    conn_medium = 'cable'
                    conn_medium_label = 'Wired Ethernet'

            devices.append({
                'hostname': hostname,
                'mac': m,
                'ip': aip,
                'static': True,
                'manual_static': True,
                'expires': '',
                'expired': False,
                'live_ips': [aip],
                'mismatch_ip': None,
                'router_node': router_node,
                'router_tooltip': router_tooltip,
                'router_type': router_type,
                'conn_medium': conn_medium,
                'conn_medium_label': conn_medium_label,
                'dev_class': dev_class,
                'dev_vendor': dev_vendor,
                'dev_icon': dev_icon,
                'dev_cat': dev_cat,
                'web_links': [],
                'open_ports': []
            })
            seen_ips.add(aip)

    # Include Raspberry Pi local host if not already in devices
    if '192.168.1.249' not in seen_ips:
        devices.append({
            'hostname': 'pi-server (Local Host)',
            'mac': 'b8:27:eb:a0:ff:6e',
            'ip': '192.168.1.249',
            'static': True,
            'manual_static': True,
            'expires': '',
            'expired': False,
            'live_ips': ['192.168.1.249'],
            'mismatch_ip': None,
            'router_node': 'Gateway / LAN',
            'router_tooltip': 'Local host running AdGuard Home and DHCP Manager',
            'router_type': 'lan',
            'conn_medium': 'cable',
            'conn_medium_label': 'Wired Ethernet',
            'dev_class': 'Server / Raspberry Pi',
            'dev_vendor': 'Raspberry Pi Foundation',
            'dev_icon': '🍓',
            'dev_cat': 'server',
            'web_links': [],
            'open_ports': []
        })
        seen_ips.add('192.168.1.249')

    # Fast parallel pre-scan of common web ports for all active devices
    active_ips = set()
    for d in devices:
        if d.get('live_ips'):
            active_ips.add(d['ip'])
            for lip in d['live_ips']:
                active_ips.add(lip)
    active_ips.add('192.168.1.1')
    active_ips.add('192.168.1.249')
    for r in routers:
        for x in (r.get('ip') or '').split(','):
            if x.strip():
                active_ips.add(x.strip())

    now = time.time()
    if force_refresh:
        _SERVICE_SCAN_CACHE.clear()

    ips_to_scan = [a_ip for a_ip in active_ips if a_ip and (force_refresh or a_ip not in _SERVICE_SCAN_CACHE or (now - _SERVICE_SCAN_CACHE[a_ip][0]) >= 180)]
    if ips_to_scan:
        with ThreadPoolExecutor(max_workers=min(25, max(1, len(ips_to_scan) * 5))) as pool:
            futures = {pool.submit(scan_device_verified_services, a_ip): a_ip for a_ip in ips_to_scan}
            for f in futures:
                a_ip = futures[f]
                try:
                    v_services = f.result()
                    _SERVICE_SCAN_CACHE[a_ip] = (now, v_services)
                except Exception:
                    _SERVICE_SCAN_CACHE[a_ip] = (now, [])

    # Update web_links for all devices with detected services
    custom_names = cfg.get('custom_service_names', {})
    for d in devices:
        is_active = bool(d.get('live_ips')) or d['ip'] in ('192.168.1.1', '192.168.1.249')
        d['web_links'] = get_device_web_links(
            d['ip'],
            d.get('hostname', ''),
            d.get('dev_class', ''),
            d.get('dev_cat', ''),
            routers,
            halo_node_info,
            is_active=is_active,
            custom_service_names=custom_names
        )
        d['open_ports'] = sorted(list(set(l['port'] for l in d['web_links'] if 'port' in l)))

    devices.sort(key=lambda d: (not d['static'], ip_sort_key(d['ip'])))

    # Global network infrastructure links for the top quick-access dropdown
    global_network_links = []
    for r in routers:
        r_name = r.get('name') or 'Router'
        r_ips = [x.strip() for x in (r.get('ip') or '').split(',') if x.strip()]
        for rip in r_ips:
            node_title = halo_node_info.get(rip, {}).get('label', r_name) if r.get('type') == 'mercusys_halo' else r_name
            icon = "🌐" if r.get('type') == 'mercusys_halo' else ("📶" if any(k in r_name.lower() for k in ["repeater", "em4590"]) else "🖧")
            global_network_links.append({
                'name': node_title,
                'ip': rip,
                'url': f'http://{rip}',
                'icon': icon
            })

    existing_link_ips = {l['ip'] for l in global_network_links}
    if '192.168.1.1' not in existing_link_ips and '192.168.0.1' not in existing_link_ips:
        gw = '192.168.1.1'
        global_network_links.insert(0, {
            'name': 'Gateway Router',
            'ip': gw,
            'url': f'http://{gw}',
            'icon': '🏠'
        })

    global_network_links.append({
        'name': 'AdGuard Home (DNS/DHCP)',
        'ip': '192.168.1.249:8080',
        'url': 'http://192.168.1.249:8080',
        'icon': '🛡️'
    })

    ha_dev = next((d for d in devices if d.get('ip') == '192.168.1.219' or 'ha-vm' in (d.get('hostname') or '').lower()), None)
    if ha_dev:
        global_network_links.append({
            'name': 'Home Assistant',
            'ip': '192.168.1.219:8123',
            'url': 'http://192.168.1.219:8123',
            'icon': '🏠'
        })
        global_network_links.append({
            'name': 'Nginx Proxy Manager',
            'ip': '192.168.1.219:81',
            'url': 'http://192.168.1.219:81',
            'icon': '🔀'
        })

    return {
        'status': 'success',
        'adguard_available': adguard_available,
        'adguard_mode': 'connected' if adguard_available else 'standalone',
        'lease_duration': get_lease_duration(),
        'ghost_count': ghost_count,
        'expired_count': expired_count,
        'devices': devices,
        'network_links': global_network_links,
        'custom_service_names': custom_names
    }


@app.route('/api/state', methods=['GET'])
def api_state():
    force_refresh = bool(request.args.get('refresh') or request.args.get('force'))
    state = build_state(force_refresh=force_refresh)
    extras.enrich_state(state)
    return jsonify(state)


@app.route('/api/services/rename', methods=['POST'])
def api_rename_service():
    try:
        data = request.get_json(force=True) or {}
        url = (data.get('url') or '').strip()
        custom_name = (data.get('name') or '').strip()
        if not url:
            return jsonify({'success': False, 'error': 'Service URL not specified'}), 400

        cfg = load_config()
        if 'custom_service_names' not in cfg or not isinstance(cfg['custom_service_names'], dict):
            cfg['custom_service_names'] = {}

        norm_url = url.rstrip('/')
        if custom_name:
            cfg['custom_service_names'][norm_url] = custom_name
            cfg['custom_service_names'][norm_url + '/'] = custom_name
        else:
            cfg['custom_service_names'].pop(norm_url, None)
            cfg['custom_service_names'].pop(norm_url + '/', None)

        save_config(cfg)
        return jsonify({'success': True, 'custom_service_names': cfg['custom_service_names']})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/assign-static', methods=['POST'])
def api_assign_static():
    req = request.json or {}
    mac = (req.get('mac') or '').strip().lower()
    ip = (req.get('ip') or '').strip()
    hostname = (req.get('hostname') or '').strip()
    force_reconnect = bool(req.get('force_reconnect', False))
    force_rf = bool(req.get('force_rf', False))

    if not mac or not ip or not hostname:
        return jsonify({'status': 'error', 'message': 'MAC, IP y Nombre son obligatorios.'})

    if not check_adguard_available():
        return jsonify({'status': 'error', 'message': 'Modo Autónomo: La asignación DHCP estática en servidor requiere AdGuard Home activo.'}), 400

    # Obtener IP previa de la MAC antes de purgar
    old_ip = None
    try:
        curr_data = read_leases()
        for l in curr_data.get('leases', []):
            if (l.get('mac') or '').lower() == mac:
                old_ip = (l.get('ip') or '').strip()
                break
    except Exception:
        pass

    run_sudo(['docker', 'stop', 'adguardhome'])
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
        run_sudo(['docker', 'start', 'adguardhome'])

    base_msg = f'IP estática {ip} guardada en AdGuard Home para {hostname} ({mac}).'
    if removed > 0:
        base_msg += f' ({removed} concesiones previas purgadas).'

    if not force_reconnect:
        return jsonify({'status': 'success', 'verified': True, 'message': f'📌 {base_msg} Se aplicará automáticamente en su próxima renovación DHCP.'})

    # Forzar reconexión inteligente según router y broadcast DHCPNAK
    actions_taken = []
    cfg = load_config()

    # Identificar si está en Halo
    connected_to_halo = False
    try:
        for r in cfg.get('routers', []):
            if r.get('type') == 'mercusys_halo':
                hmap, _ = get_mercusys_halo_data(r)
                if mac in hmap:
                    connected_to_halo = True
                    break
    except Exception:
        pass

    # Si está en router compatible, lanzar reconexión AP
    for r in cfg.get('routers', []):
        if not r.get('enabled', True):
            continue
        rtype = r.get('type')
        if connected_to_halo and rtype == 'mercusys_halo':
            ok, rmsg = trigger_router_reconnect(r, mac)
            actions_taken.append(rmsg)

        elif rtype == 'tplink_wr841n' and not connected_to_halo:
            ok, rmsg = trigger_router_reconnect(r, mac)
            actions_taken.append(rmsg)

    # 2.5 Si el plugin Wi-Fi RF está activo y mon0 listo, emitir deauth adicional por radiofrecuencia
    if force_rf or (force_reconnect and cfg.get('wifi_plugin_enabled')):
        try:
            import wifi_plugin
            if hasattr(wifi_plugin, 'mon_listo') and wifi_plugin.mon_listo():
                ok_rf, rf_log = wifi_plugin.send_rf_deauth_if_available(mac)
                if ok_rf:
                    actions_taken.append("Expulsión RF (802.11 aire) emitida")
        except Exception:
            pass

    # Enviar SIEMPRE ráfaga DHCPNAK por L2 y purgar entrada ARP local
    try:
        send_nak_script = os.path.join(os.path.dirname(__file__), 'send_nak.py')
        if os.path.exists(send_nak_script):
            nak_res = run_sudo(['python3', send_nak_script, mac, '192.168.1.249', old_ip or '-', 'eth0'])
            if nak_res.returncode == 0:
                actions_taken.append("DHCPNAK emitido")
    except Exception as e:
        actions_taken.append(f"DHCPNAK err: {e}")

    # Esperar propagación L2
    time.sleep(3)

    # Verificación verídica L2 (sin falsos positivos)
    verified_new, _ = verify_ip_l2(ip, mac)
    if verified_new:
        full_msg = f"✅ {base_msg} | ¡Nueva IP {ip} confirmada y activa en el dispositivo!"
        return jsonify({'status': 'success', 'verified': True, 'message': full_msg})

    still_on_old = False
    if old_ip and old_ip != ip:
        still_on_old, _ = verify_ip_l2(old_ip, mac)

    if still_on_old:
        full_msg = f"⚠️ {base_msg} | El dispositivo aún mantiene activa la IP anterior ({old_ip}). Tomará {ip} automáticamente al renovar su concesión DHCP."
    else:
        full_msg = f"⚠️ {base_msg} | El dispositivo aún no responde en {ip}. Se le asignará en cuanto solicite DHCP."

    return jsonify({'status': 'warning', 'verified': False, 'old_ip': old_ip, 'message': full_msg})


@app.route('/api/ping', methods=['POST'])
def api_ping():
    req = request.json or {}
    ip = (req.get('ip') or '').strip()
    mac = (req.get('mac') or '').strip().lower()
    alive = False
    if ip:
        alive, _ = verify_ip_l2(ip, mac if mac else None)
        if not alive:
            alive = ping_ip(ip)
    return jsonify({
        'status': 'success',
        'alive': alive,
        'message': f'¡Comprobación exitosa! {ip} responde activamente.' if alive else f'Sin respuesta en {ip} todavía.'
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

    if ip:
        try:
            run_sudo(['ip', 'neigh', 'del', ip, 'dev', 'eth0'])
        except Exception:
            pass

    return jsonify({'status': 'success', 'message': f'Lease / record {ip} ({mac}) removed successfully.'})


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



try:
    import wifi_plugin
    wifi_plugin.init_app(app, {
        'run_sudo': run_sudo,
        'load_config': load_config,
        'save_config_raw': save_config_raw,
        'get_arp_table': get_arp_table,
        'read_leases': read_leases,
        'build_state': build_state,
    })
except Exception as _e_wifi:
    print(f"Aviso: no se pudo cargar wifi_plugin: {_e_wifi}")

extras.init_app(app, {
    'CONFIG_PATH': CONFIG_PATH,
    'YAML_PATH': DEFAULT_CONFIG['yaml_path'],
    'load_config': load_config,
    'save_config_raw': save_config_raw,
    'build_state': build_state,
    'is_locally_administered_mac': is_locally_administered_mac,
    'run_sudo': run_sudo,
    'get_arp_table': get_arp_table,
    'read_leases': read_leases,
    'write_leases': write_leases,
})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('DHCP_PANEL_PORT', '5001')))
