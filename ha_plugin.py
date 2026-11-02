# -*- coding: utf-8 -*-
"""
ha_plugin.py - Plugin de Integración con Home Assistant (Multi-Instancia)
Gestor de IPs Estáticas AdGuard Home
"""

import os
import json
import time
import socket
import struct
import base64
import urllib.request
import urllib.error
import threading
import re
from typing import Dict, List, Any, Optional

# Caché en memoria para evitar consultas lentas
_HA_CACHE = {
    "timestamp": 0.0,
    "ttl": 45.0, # 45 segundos de frescura
    "mac_map": {}, # mac_norm -> dict info
    "instances_status": {}, # instance_id -> { online: bool, version: str, count: int, error: str }
    "refreshing": False
}
_CACHE_LOCK = threading.Lock()

def norm_mac(mac: str) -> str:
    """Normaliza una dirección MAC a formato minúsculas con dos puntos (aa:bb:cc:dd:ee:ff)."""
    if not mac:
        return ""
    clean = "".join(c for c in str(mac).lower() if c in "0123456789abcdef")
    if len(clean) == 12:
        return ":".join(clean[i:i+2] for i in range(0, 12, 2))
    return mac.strip().lower()

# ---------------------------------------------------------------------------
# WebSocket Client RFC 6455 en Python puro (con buffer de handshake y tramas)
# ---------------------------------------------------------------------------
class HAWebSocketClient:
    def __init__(self, host: str, port: int, path: str = "/api/websocket", timeout: float = 6.0):
        self.host = host
        self.port = port
        self.path = path
        self.timeout = timeout
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(timeout)
        self._buf = bytearray()

    def connect(self):
        self.s.connect((self.host, self.port))
        key = base64.b64encode(os.urandom(16)).decode()
        req = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.s.sendall(req.encode())

        resp = bytearray()
        while b"\r\n\r\n" not in resp:
            chunk = self.s.recv(4096)
            if not chunk:
                raise Exception("Conexión cerrada durante handshake HTTP")
            resp.extend(chunk)

        header_bytes, rest = resp.split(b"\r\n\r\n", 1)
        if b"101 Switching Protocols" not in header_bytes:
            raise Exception("Handshake HTTP fallido: " + header_bytes.decode('utf-8', errors='ignore'))
        
        self._buf.extend(rest)

    def _read_exact(self, n: int) -> bytearray:
        while len(self._buf) < n:
            chunk = self.s.recv(max(4096, n - len(self._buf)))
            if not chunk:
                raise Exception("Conexión cerrada prematuramente")
            self._buf.extend(chunk)
        res = self._buf[:n]
        del self._buf[:n]
        return res

    def send(self, data_str: str):
        data = data_str.encode('utf-8')
        mask = os.urandom(4)
        length = len(data)
        if length < 126:
            hdr = bytearray([0x81, 0x80 | length])
        elif length < 65536:
            hdr = bytearray([0x81, 0x80 | 126]) + struct.pack(">H", length)
        else:
            hdr = bytearray([0x81, 0x80 | 127]) + struct.pack(">Q", length)
        masked = bytearray(b ^ mask[i % 4] for i, b in enumerate(data))
        self.s.sendall(hdr + mask + masked)

    def recv(self) -> Optional[str]:
        while True:
            try:
                hdr = self._read_exact(2)
            except Exception:
                return None
            b1, b2 = hdr[0], hdr[1]
            opcode = b1 & 0x0F
            is_masked = bool(b2 & 0x80)
            length = b2 & 0x7F

            if length == 126:
                try:
                    length = struct.unpack(">H", self._read_exact(2))[0]
                except Exception:
                    return None
            elif length == 127:
                try:
                    length = struct.unpack(">Q", self._read_exact(8))[0]
                except Exception:
                    return None

            mask = self._read_exact(4) if is_masked else None
            try:
                payload = self._read_exact(length)
            except Exception:
                return None

            if mask:
                payload = bytearray(b ^ mask[i % 4] for i, b in enumerate(payload))

            if opcode == 0x8: # Close
                self.close()
                return None
            elif opcode == 0x9: # Ping
                pong = bytearray([0x8A, 0])
                try:
                    self.s.sendall(pong)
                except Exception:
                    pass
                continue
            elif opcode == 0xA: # Pong
                continue
            elif opcode in (0x1, 0x2): # Text or Binary
                return payload.decode('utf-8', errors='ignore')

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass

def _parse_url_host_port(url_str: str):
    url = url_str.strip().rstrip('/')
    if url.startswith('http://'):
        rest = url[7:]
    elif url.startswith('https://'):
        rest = url[8:]
    else:
        rest = url
    if '/' in rest:
        rest = rest.split('/', 1)[0]
    if ':' in rest:
        host, port_s = rest.split(':', 1)
        port = int(port_s)
    else:
        host = rest
        port = 8123
    return host, port

# ---------------------------------------------------------------------------
# Verificación y comunicación con una instancia de Home Assistant
# ---------------------------------------------------------------------------
def test_ha_instance(url: str, token: str) -> Dict[str, Any]:
    """Verifica la conectividad y credenciales contra una instancia de Home Assistant."""
    url = url.strip().rstrip('/')
    token = token.strip()
    if not url:
        return {"success": False, "message": "URL no especificada"}
    if not token:
        return {"success": False, "message": "Token de acceso de larga duración requerido"}

    host, port = _parse_url_host_port(url)

    # 1. Probar REST API básica (/api/config)
    try:
        req = urllib.request.Request(
            f"{url}/api/config",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            cfg_data = json.loads(resp.read().decode('utf-8'))
            version = cfg_data.get('version', 'Desconocida')
            location_name = cfg_data.get('location_name', 'Home Assistant')
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return {"success": False, "message": "Autenticación denegada (401). Verifica el token de acceso de larga duración."}
        return {"success": False, "message": f"Error HTTP {e.code}: {e.reason}"}
    except Exception as e:
        return {"success": False, "message": f"No se pudo conectar a {url}: {e}"}

    # 2. Probar WebSocket para comprobar device_registry
    dev_count = 0
    try:
        ws = HAWebSocketClient(host, port, timeout=5.0)
        ws.connect()
        init_raw = ws.recv()
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_raw = ws.recv()
        auth_data = json.loads(auth_raw or "{}")
        if auth_data.get("type") != "auth_ok":
            ws.close()
            return {"success": False, "message": "WebSocket: Token rechazado por Home Assistant"}

        # Pedir lista de dispositivos
        ws.send(json.dumps({"id": 1, "type": "config/device_registry/list"}))
        devs_raw = ws.recv()
        ws.close()

        if devs_raw:
            d_json = json.loads(devs_raw)
            if d_json.get("success"):
                dev_count = len(d_json.get("result", []))
    except Exception as e:
        # Si el WS falla pero REST funcionó, al menos confirmamos REST
        pass

    return {
        "success": True,
        "version": version,
        "location_name": location_name,
        "devices_count": dev_count,
        "message": f"Conexión exitosa a {location_name} (HA v{version}) — {dev_count} dispositivos sincronizados."
    }

def fetch_instance_catalog(instance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Consulta la instancia de HA y devuelve un diccionario: norm_mac -> metadata."""
    url = (instance.get('url') or '').strip().rstrip('/')
    token = (instance.get('token') or '').strip()
    inst_id = instance.get('id', 'default')
    inst_name = instance.get('name') or 'Home Assistant'

    if not url or not token or not instance.get('enabled', True):
        return {}

    host, port = _parse_url_host_port(url)
    res_map = {}

    try:
        ws = HAWebSocketClient(host, port, timeout=6.0)
        ws.connect()
        ws.recv() # auth_required
        ws.send(json.dumps({"type": "auth", "access_token": token}))
        auth_raw = ws.recv()
        auth_data = json.loads(auth_raw or "{}")
        if auth_data.get("type") != "auth_ok":
            ws.close()
            return {}

        # 1. Device registry
        ws.send(json.dumps({"id": 1, "type": "config/device_registry/list"}))
        devs_raw = ws.recv()
        devices = json.loads(devs_raw or "{}").get("result", [])

        # 2. Entity registry
        ws.send(json.dumps({"id": 2, "type": "config/entity_registry/list"}))
        ents_raw = ws.recv()
        entities = json.loads(ents_raw or "{}").get("result", [])

        # 3. Area registry
        ws.send(json.dumps({"id": 3, "type": "config/area_registry/list"}))
        areas_raw = ws.recv()
        areas = {(a.get('area_id') or a.get('id')): a.get('name') for a in json.loads(areas_raw or "{}").get("result", []) if isinstance(a, dict)}

        ws.close()

        # Mapa de entidades por device_id
        dev_to_ents = {}
        for ent in entities:
            did = ent.get('device_id')
            if did:
                dev_to_ents.setdefault(did, []).append({
                    "entity_id": ent.get('entity_id'),
                    "name": ent.get('name') or ent.get('original_name'),
                    "platform": ent.get('platform')
                })

        # Extraer estados en vivo vía REST rápida (/api/states)
        live_states = {}
        try:
            req = urllib.request.Request(
                f"{url}/api/states",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                all_states = json.loads(resp.read().decode('utf-8'))
                for st in all_states:
                    live_states[st.get('entity_id')] = {
                        "state": st.get('state'),
                        "unit": st.get('attributes', {}).get('unit_of_measurement'),
                        "friendly_name": st.get('attributes', {}).get('friendly_name')
                    }
        except Exception:
            pass

        # Procesar dispositivos y extraer MACs
        for dev in devices:
            macs = set()
            # 1. Conexiones (MAC estándar)
            for conn in dev.get('connections', []):
                if isinstance(conn, (list, tuple)) and len(conn) >= 2:
                    if str(conn[0]).lower() == 'mac':
                        m = norm_mac(str(conn[1]))
                        if m: macs.add(m)

            # 2. Identificadores (Tuya, eWeLink, ESPHome, Tasmota)
            for ident in dev.get('identifiers', []):
                if isinstance(ident, (list, tuple)) and len(ident) >= 2:
                    val = str(ident[1]).strip()
                    if re.fullmatch(r'[0-9a-fA-F]{12}', val):
                        m = norm_mac(val)
                        if m: macs.add(m)
                    elif len(val) >= 12 and re.match(r'^[0-9a-fA-F]{12}$', val[-12:]):
                        m = norm_mac(val[-12:])
                        if m: macs.add(m)

            if not macs:
                continue

            dev_id = dev.get('id')
            user_name = dev.get('name_by_user') or dev.get('name') or ''
            manuf = dev.get('manufacturer') or ''
            model = dev.get('model') or ''
            area_name = areas.get(dev.get('area_id'), '')
            dev_entities = dev_to_ents.get(dev_id, [])

            # Calcular vatios actuales y estado general
            power_w = None
            main_state = None
            for e in dev_entities:
                eid = e.get('entity_id')
                lst = live_states.get(eid)
                if lst:
                    e['state'] = lst.get('state')
                    e['unit'] = lst.get('unit')
                    if 'power' in eid or lst.get('unit') == 'W':
                        try:
                            power_w = float(lst.get('state'))
                        except Exception:
                            pass
                    if not main_state and eid.startswith(('switch.', 'light.')):
                        main_state = lst.get('state')

            item_info = {
                "instance_id": inst_id,
                "instance_name": inst_name,
                "device_id": dev_id,
                "name": user_name,
                "manufacturer": manuf,
                "model": model,
                "area": area_name,
                "entities": dev_entities,
                "power_w": power_w,
                "state": main_state,
                "last_sync": int(time.time())
            }

            for m in macs:
                res_map[m] = item_info

    except Exception as e:
        print(f"[HA-Plugin] Error al obtener catálogo de {inst_name}: {e}")

    return res_map

# ---------------------------------------------------------------------------
# Motor de caché y sincronización en segundo plano
# ---------------------------------------------------------------------------
def get_ha_mac_map(cfg: Dict[str, Any], force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
    """Devuelve el diccionario completo de MACs indexadas desde todas las instancias de HA activas."""
    if not cfg.get('ha_plugin_enabled', False):
        return {}

    instances = [i for i in cfg.get('home_assistant_instances', []) if i.get('enabled', True)]
    if not instances:
        return {}

    now = time.time()
    with _CACHE_LOCK:
        if not force_refresh and (now - _HA_CACHE["timestamp"]) < _HA_CACHE["ttl"] and _HA_CACHE["mac_map"]:
            return _HA_CACHE["mac_map"]

    merged = {}
    statuses = {}
    for inst in instances:
        inst_id = inst.get('id', 'default')
        try:
            m = fetch_instance_catalog(inst)
            merged.update(m)
            statuses[inst_id] = {"online": True, "count": len(m)}
        except Exception as e:
            statuses[inst_id] = {"online": False, "error": str(e), "count": 0}

    with _CACHE_LOCK:
        _HA_CACHE["timestamp"] = now
        _HA_CACHE["mac_map"] = merged
        _HA_CACHE["instances_status"] = statuses

    return merged

def discover_ha_instances(subnet_prefix: str = "192.168.1") -> List[Dict[str, Any]]:
    """Escanea rápidamente IPs clave en la red local buscando instancias de Home Assistant (puerto 8123)."""
    candidates = [
        "127.0.0.1", "192.168.1.14", "192.168.1.249", "192.168.1.2", "192.168.1.3",
        "192.168.1.15", "192.168.1.20", "192.168.1.50", "192.168.1.100", "192.168.1.200"
    ]
    # Añadir rango común 1..30
    for i in range(1, 31):
        ip = f"{subnet_prefix}.{i}"
        if ip not in candidates:
            candidates.append(ip)

    discovered = []
    def check_ip(ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.35)
            r = sock.connect_ex((ip, 8123))
            sock.close()
            if r == 0:
                # Comprobar si responde cabecera de Home Assistant
                try:
                    req = urllib.request.Request(f"http://{ip}:8123/manifest.json")
                    with urllib.request.urlopen(req, timeout=0.8) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        name = data.get('name', 'Home Assistant')
                        discovered.append({
                            "url": f"http://{ip}:8123",
                            "name": name,
                            "ip": ip
                        })
                except Exception:
                    # Puede ser HA que requiere auth
                    discovered.append({
                        "url": f"http://{ip}:8123",
                        "name": f"Home Assistant en {ip}",
                        "ip": ip
                    })
        except Exception:
            pass

    threads = [threading.Thread(target=check_ip, args=(ip,), daemon=True) for ip in candidates]
    for t in threads: t.start()
    for t in threads: t.join(timeout=1.5)

    return discovered

# ---------------------------------------------------------------------------
# EL CAZADOR DE MACs (Inspector Forense Multi-Nivel)
# ---------------------------------------------------------------------------
def hunt_mac_forensics(target_mac_raw: str, cfg: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta una investigación forense exhaustiva sobre una dirección MAC:
    1. OUI & Chipset
    2. Home Assistant (todas las instancias activas)
    3. Malla Wi-Fi / Routers
    4. Histórico de Red (panel.db y AdGuard)
    5. Sondeo activo de Capa 2 / ARP
    6. Síntesis diagnóstica
    """
    mac = norm_mac(target_mac_raw)
    if not mac or len(mac) < 17:
        return {"success": False, "error": "Dirección MAC no válida. Formato esperado: AA:BB:CC:DD:EE:FF"}

    # 1. OUI & Hardware
    prefix_3 = ":".join(mac.split(":")[:3]).upper()
    oui_info = _lookup_oui(prefix_3, mac)

    # 2. Home Assistant
    ha_info = None
    ha_enabled = cfg.get('ha_plugin_enabled', False)
    if ha_enabled:
        ha_map = get_ha_mac_map(cfg)
        ha_info = ha_map.get(mac)
        if not ha_info:
            ha_map = get_ha_mac_map(cfg, force_refresh=True)
            ha_info = ha_map.get(mac)

    # 3. Malla Wi-Fi y Topología
    mesh_info = None
    all_devs = state.get('devices', [])
    matched_dev = next((d for d in all_devs if norm_mac(d.get('mac')) == mac), None)

    if matched_dev:
        mesh_info = {
            "router_node": matched_dev.get('router_node'),
            "router_type": matched_dev.get('router_type'),
            "conn_medium": matched_dev.get('conn_medium'),
            "conn_medium_label": matched_dev.get('conn_medium_label'),
            "tooltip": matched_dev.get('router_tooltip'),
            "rf_detected": matched_dev.get('rf_detected'),
            "rf_channel": matched_dev.get('rf_channel')
        }

    # 4. Histórico en base de datos panel.db
    history_info = _get_db_history(mac)

    # 5. AdGuard / Estado actual
    adguard_info = {
        "is_static": matched_dev.get('static', False) if matched_dev else False,
        "static_order": matched_dev.get('static_order_idx') if matched_dev else None,
        "assigned_ip": matched_dev.get('ip') if matched_dev else None,
        "live_ips": matched_dev.get('live_ips', []) if matched_dev else [],
        "mismatch_ip": matched_dev.get('mismatch_ip') if matched_dev else None,
        "hostname": matched_dev.get('hostname') if matched_dev else None
    }

    # 6. Sondeo en vivo si no tenemos IP activa
    active_ping = None
    check_ip = adguard_info["mismatch_ip"] or adguard_info["assigned_ip"] or (history_info.get("last_ip"))
    if check_ip:
        active_ping = _fast_ping(check_ip)

    # 7. Diagnóstico inteligente
    diagnosis = _build_hunter_diagnosis(mac, oui_info, ha_info, mesh_info, adguard_info, history_info, active_ping)

    # 8. Inteligencia en Internet & Pistas OSINT
    internet_intel = _gather_internet_forensic_clues(mac, oui_info, ha_info, adguard_info, history_info)

    return {
        "success": True,
        "mac": mac.upper(),
        "oui": oui_info,
        "home_assistant": {
            "plugin_active": ha_enabled,
            "found": bool(ha_info),
            "data": ha_info
        },
        "mesh": mesh_info,
        "history": history_info,
        "adguard": adguard_info,
        "active_ping": active_ping,
        "diagnosis": diagnosis,
        "internet_intel": internet_intel
    }

def _gather_internet_forensic_clues(mac: str, oui_info: Dict[str, Any], ha_info: Optional[Dict[str, Any]], adguard_info: Dict[str, Any], history_info: Dict[str, Any]) -> Dict[str, Any]:
    """Recopila inteligencia en Internet, pistas heurísticas de huella y enlaces OSINT de investigación."""
    import urllib.parse
    intel = {
        "online_vendor": None,
        "heuristic_clues": [],
        "web_snippets": [],
        "search_links": []
    }

    hostname = adguard_info.get("hostname") or history_info.get("last_hostname") or ""
    ha_data = ha_info.get("data") if (isinstance(ha_info, dict) and "data" in ha_info) else ha_info
    host_lower = hostname.lower()

    # 1. Consulta en línea a API oficial IEEE OUI (MacVendors)
    try:
        req = urllib.request.Request(f"https://api.macvendors.com/{urllib.parse.quote(mac)}", headers={"User-Agent": "DHCPPanel/2.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            ven = resp.read().decode('utf-8', errors='ignore').strip()
            if ven and "errors" not in ven.lower() and "<html" not in ven.lower():
                intel["online_vendor"] = ven
    except Exception:
        pass

    # 2. Pistas Heurísticas por huellas de comportamiento y nombres de red
    if re.match(r'^esp-[0-9a-f]{6}$', host_lower):
        intel["heuristic_clues"].append({
            "type": "Chipset & SDK de Fábrica",
            "icon": "⚡",
            "text": f"El hostname '{hostname}' es la huella de fábrica asignada por el SDK oficial de Espressif (ESP8266/ESP32). Muy común en enchufes y bombillas inteligentes Tuya Smart, Tasmota o ESPHome antes de ser personalizados."
        })
    elif "ck-bl602" in host_lower or (ha_data and "ck-bl602" in str(ha_data).lower()):
        intel["heuristic_clues"].append({
            "type": "Hardware CoolKit / Sonoff",
            "icon": "🔌",
            "text": "La referencia 'CK-BL602' corresponde al chipset RISC-V Bouffalo Lab BL602 utilizado por Shenzhen Sonoff / CoolKit en enchufes inteligentes eWeLink de última generación con monitorización de energía."
        })
    elif "tasmota" in host_lower:
        intel["heuristic_clues"].append({
            "type": "Firmware Open Source",
            "icon": "🛠️",
            "text": f"El hostname '{hostname}' indica que el dispositivo ha sido liberado con el firmware de código abierto Tasmota, permitiendo control MQTT y HTTP 100% local sin nube."
        })
    elif "shelly" in host_lower:
        intel["heuristic_clues"].append({
            "type": "Domótica Shelly",
            "icon": "🏠",
            "text": "Dispositivo del ecosistema Shelly (Allterco Robotics). Incluye interfaz web propia en el puerto 80 y soporte CoAP/MQTT/REST local."
        })
    elif "wled" in host_lower:
        intel["heuristic_clues"].append({
            "type": "Controlador LED WLED",
            "icon": "🌈",
            "text": "Controlador de tiras LED direccionables (WS2812B/SK6812) ejecutando el firmware de código abierto WLED."
        })
    elif host_lower.startswith(("desktop-", "laptop-")):
        intel["heuristic_clues"].append({
            "type": "Sistema Operativo",
            "icon": "💻",
            "text": f"El hostname '{hostname}' es la nomenclatura estándar asignada durante la instalación de Microsoft Windows."
        })

    if ha_data and isinstance(ha_data, dict):
        mfg = (ha_data.get('manufacturer') or '').lower()
        model = (ha_data.get('model') or '').lower()
        if 'tuya' in mfg:
            intel["heuristic_clues"].append({
                "type": "Ecosistema Tuya / Smart Life",
                "icon": "☁️",
                "text": f"Dispositivo fabricado bajo la plataforma global Tuya IoT ({ha_data.get('model') or 'Smart Socket'}). Compatible con Smart Life y controlable vía protocolo local o nube Tuya."
            })
        elif 'kingart' in mfg or 'sonoff' in mfg or 'coolkit' in mfg:
            intel["heuristic_clues"].append({
                "type": "Ecosistema eWeLink / Sonoff",
                "icon": "📶",
                "text": f"Dispositivo basado en plataforma CoolKit/eWeLink ({ha_data.get('manufacturer')} {ha_data.get('model')}). Habitual en interruptores táctiles de pared, enchufes y relés de domótica."
            })

    # 3. Búsqueda activa de fragmentos en Internet (DuckDuckGo Search)
    search_term = ""
    if ha_data and isinstance(ha_data, dict) and ha_data.get('model') and ha_data.get('model') != 'smart socket':
        search_term = f"{ha_data.get('model')} {ha_data.get('manufacturer') or ''}".strip()
    elif hostname and not re.match(r'^esp-[0-9a-f]{6}$', host_lower) and not host_lower.startswith(("desktop-", "laptop-")):
        search_term = hostname
    elif ha_data and isinstance(ha_data, dict) and ha_data.get('name') and ha_data.get('manufacturer'):
        search_term = f"{ha_data.get('manufacturer')} {ha_data.get('model') or 'smart socket'} IoT".strip()
    elif oui_info and oui_info.get('family'):
        search_term = f"{oui_info.get('vendor')} {oui_info.get('type')}".strip()

    if search_term:
        try:
            url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(search_term)
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                html = resp.read().decode('utf-8', errors='ignore')
                snips = re.findall(r'<a class="result__snippet[^>]*>(.*?)</a>', html, re.DOTALL)
                for s in snips[:2]:
                    cl = re.sub(r'<[^>]+>', '', s).strip()
                    cl = cl.replace('&quot;', '"').replace('&#x27;', "'").replace('&amp;', '&').replace('&nbsp;', ' ')
                    if cl and len(cl) > 20:
                        intel["web_snippets"].append({"term": search_term, "snippet": cl})
        except Exception:
            pass

    # 4. Enlaces directos a motores de búsqueda y repositorios de hardware (OSINT 1-Click)
    link_query = search_term or hostname or mac
    intel["search_links"] = [
        {"name": "Google", "url": f"https://www.google.com/search?q={urllib.parse.quote(link_query)}", "icon": "🔍"},
        {"name": "DuckDuckGo", "url": f"https://duckduckgo.com/?q={urllib.parse.quote(link_query)}", "icon": "🦆"},
        {"name": "Blakadder IoT DB", "url": f"https://templates.blakadder.com/search.html?q={urllib.parse.quote(search_term or oui_info.get('vendor') or 'tuya')}", "icon": "🔌"},
        {"name": "Wireshark OUI", "url": f"https://www.wireshark.org/tools/oui-lookup.html?search={mac[:8]}", "icon": "📑"}
    ]

    return intel

def _lookup_oui(prefix: str, full_mac: str) -> Dict[str, Any]:
    """Identifica fabricante, chipsets típicos y tipo de dispositivo por prefijo OUI."""
    OUI_DATABASE = {
        "DC:4F:22": {"vendor": "Espressif Systems Inc. (Tuya IoT)", "family": "Espressif / Tuya Smart Socket", "chip": "ESP8266 / ESP32 / Tuya Wi-Fi", "type": "Enchufe / Interruptor Inteligente Smart"},
        "D0:27:03": {"vendor": "Shenzhen Sonoff Technology Co., Ltd. (SONOFF)", "family": "Sonoff / eWeLink", "chip": "Bouffalo Lab (BL602) / ESP8266", "type": "Enchufe / Interruptor Inteligente Wi-Fi"},
        "60:01:94": {"vendor": "Espressif Systems Inc.", "family": "ESP8266 / NodeMCU", "chip": "ESP8266 Wi-Fi SoC", "type": "Módulo IoT / Microcontrolador Domótico"},
        "24:4C:AB": {"vendor": "Espressif Systems Inc.", "family": "ESP32", "chip": "ESP32 Dual-Core Wi-Fi+BLE", "type": "Módulo IoT / Domótica"},
        "C4:DD:57": {"vendor": "Tuya Smart Inc. (Wuxi)", "family": "Tuya Smart / Smart Life", "chip": "Tuya Wi-Fi SoC (BK7231 / RTL8710)", "type": "Enchufe / Relé Domótico Smart"},
        "80:64:7C": {"vendor": "Tuya Smart Inc.", "family": "Tuya Smart / Smart Life", "chip": "Tuya Wi-Fi (BK7231N / ESP8266)", "type": "Bombilla / Enchufe Smart"},
        "B4:60:ED": {"vendor": "Xiaomi Communications", "family": "Xiaomi Smart Home", "chip": "Espressif / Xiaomi IoT", "type": "Electrodoméstico Smart (Airfryer / Robot)"},
        "D4:AD:FC": {"vendor": "Shenzhen Intellirocks Tech (Govee)", "family": "Govee Immersion / Ambilight", "chip": "Espressif Wi-Fi+BLE", "type": "Iluminación LED / Tira TV"},
        "78:0F:77": {"vendor": "Broadlink Technology Co., Ltd.", "family": "BroadLink Smart Home", "chip": "Marvell / Broadlink Wi-Fi", "type": "Mando Emisor Universal IR / RF 433MHz"},
        "B8:27:EB": {"vendor": "Raspberry Pi Foundation", "family": "Raspberry Pi (Model B / 3B)", "chip": "Broadcom BCM2835/2837", "type": "Microordenador / Servidor Local"},
        "DC:A6:32": {"vendor": "Raspberry Pi Foundation", "family": "Raspberry Pi 4B", "chip": "Broadcom BCM2711", "type": "Microordenador / Servidor Local"},
        "E4:5F:01": {"vendor": "Raspberry Pi Trading Ltd", "family": "Raspberry Pi 4B / Compute Module", "chip": "Broadcom BCM2711", "type": "Microordenador / Servidor Local"},
        "28:CD:C1": {"vendor": "Raspberry Pi Trading Ltd", "family": "Raspberry Pi 5", "chip": "Broadcom BCM2712", "type": "Microordenador / Servidor Local"},
        "84:47:09": {"vendor": "GMKtec / Intel", "family": "Mini PC Intel", "chip": "Intel I225/I226 2.5GbE", "type": "Mini PC / Servidor Proxmox"}
    }
    hit = OUI_DATABASE.get(prefix)
    if hit:
        return hit
    return {
        "vendor": f"Fabricante OUI {prefix}",
        "family": "Dispositivo de Red",
        "chip": "No identificado en base local",
        "type": "Equipo de red / IoT"
    }

def _get_db_history(mac: str) -> Dict[str, Any]:
    try:
        import extras
        db_path = extras.DB_PATH or '/home/yo/dhcp-panel/panel.db'
        if not os.path.exists(db_path):
            return {}
        import sqlite3
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        dev_row = c.execute("SELECT hostname, last_ip, online, last_seen FROM devices WHERE lower(mac)=?", (mac,)).fetchone()
        ev_rows = c.execute("SELECT ts, ip, event FROM device_events WHERE lower(mac)=? ORDER BY ts DESC LIMIT 8", (mac,)).fetchall()
        conn.close()

        history_ips = list(dict.fromkeys([r[1] for r in ev_rows if r[1]]))
        return {
            "registered": bool(dev_row),
            "last_hostname": dev_row[0] if dev_row else None,
            "last_ip": dev_row[1] if dev_row else None,
            "online_in_db": bool(dev_row[2]) if dev_row else False,
            "last_seen_ts": dev_row[3] if dev_row else None,
            "past_ips": history_ips,
            "events_count": len(ev_rows)
        }
    except Exception:
        return {}

def _fast_ping(ip: str) -> Dict[str, Any]:
    try:
        import subprocess
        res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], capture_output=True, text=True)
        alive = res.returncode == 0
        lat = None
        if alive:
            for l in res.stdout.splitlines():
                if "time=" in l:
                    try: lat = float(l.split("time=")[1].split()[0])
                    except Exception: pass
        return {"target_ip": ip, "alive": alive, "latency_ms": lat}
    except Exception:
        return {"target_ip": ip, "alive": False, "error": "Ping falló"}

def _build_hunter_diagnosis(mac, oui, ha, mesh, adguard, history, ping) -> Dict[str, Any]:
    """Genera un diagnóstico claro y recomendaciones precisas."""
    recs = []
    status_label = "Desconocido"
    badge_type = "warn"

    d = ha.get("data") if (isinstance(ha, dict) and "data" in ha) else ha
    if d and isinstance(d, dict) and (d.get("name") or d.get("device_id")):
        name = d.get("name") or "Dispositivo Smart"
        inst = d.get("instance_name") or "Home Assistant"
        status_label = f"Identificado en {inst} como «{name}»"
        badge_type = "success"

        if adguard.get("assigned_ip"):
            recs.append(f"El dispositivo tiene IP asignada en AdGuard Home: {adguard.get('assigned_ip')}.")
        elif not adguard.get("live_ips") and not (ping and ping.get("alive")):
            recs.append("El dispositivo está controlado en Home Assistant pero no responde en la red local ni tiene lease DHCP en AdGuard.")
            recs.append("Causa probable: Se comunica por NUBE (WebSocket eWeLink/Tuya) o conserva una IP fija antigua del router.")
            recs.append("Solución recomendada: Desconecta el dispositivo de la corriente 5 segundos y vuelve a enchufarlo para forzar petición DHCP a AdGuard.")
    elif mesh and mesh.get("router_node"):
        status_label = f"Conectado a Wi-Fi en {mesh['router_node']}"
        badge_type = "info"
        recs.append(f"El dispositivo está físicamente asociado al punto de acceso {mesh['router_node']}.")
    elif history and history.get("registered"):
        status_label = f"Registrado previamente (visto en {history.get('last_ip')})"
        badge_type = "warn"
        recs.append(f"Tuvo actividad previa en la IP {history.get('last_ip')}, pero actualmente está inactivo o desconectado.")
    else:
        status_label = "Dispositivo no detectado en el tráfico de red actual"
        badge_type = "danger"
        recs.append("No hay registros de tráfico DHCP ni ARP de esta MAC en la Raspberry Pi.")
        recs.append("Si es un aparato nuevo, asegúrate de que no está en modo emparejamiento (emitiendo su propio Wi-Fi) o verifica la alimentación eléctrica.")

    return {
        "status_label": status_label,
        "badge_type": badge_type,
        "recommendations": recs
    }
