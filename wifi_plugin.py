#!/usr/bin/env python3
"""
wifi_plugin.py - Plugin de Gestión Wi-Fi / Radar RF y Modo Monitor (Nexmon / brcmfmac).
Integrado dentro de AdGuard DHCP Panel.
"""
import os
import glob
import re
import json
import time
import shutil
import subprocess
from flask import request, jsonify

VERSION = "v1.10"

# Asegurar que /usr/sbin y /sbin estén en PATH para herramientas como airodump-ng, aireplay-ng, iw
for p in ('/usr/sbin', '/sbin', '/usr/local/sbin'):
    if p not in os.environ.get('PATH', ''):
        os.environ['PATH'] = p + ':' + os.environ.get('PATH', '')

MON_IFACE = "mon0"
SCAN_SECONDS = 12
CANAL_SCAN_SECONDS = 10

_context = {}
_CACHE_CLIENTES_RF = {}
CACHE_RF_FILE = os.path.join(os.path.dirname(__file__), 'wifi_rf_cache.json')

def _cargar_cache_rf():
    global _CACHE_CLIENTES_RF
    if os.path.exists(CACHE_RF_FILE):
        try:
            with open(CACHE_RF_FILE, 'r', encoding='utf-8') as f:
                _CACHE_CLIENTES_RF = json.load(f) or {}
        except Exception:
            _CACHE_CLIENTES_RF = {}

def _guardar_cache_rf():
    try:
        tmp = CACHE_RF_FILE + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(_CACHE_CLIENTES_RF, f, indent=2)
        os.replace(tmp, CACHE_RF_FILE)
    except Exception:
        pass

_cargar_cache_rf()


def sh(cmd, timeout=25):
    """Ejecuta un comando con privilegios y devuelve (rc, stdout, stderr)."""
    try:
        if cmd[0] != 'sudo' and os.geteuid() != 0:
            cmd = ['sudo'] + cmd
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, (res.stdout or ""), (res.stderr or "")
    except Exception as e:
        return -1, "", str(e)


def ejecutar_comando_debug(cmd_list, timeout=25):
    """Ejecuta un comando y devuelve el log completo + el código de salida."""
    rc, out, err = sh(cmd_list, timeout=timeout)
    log = "-> Ejecutando: " + " ".join(cmd_list) + "\n"
    if out.strip():
        log += "   [STDOUT]:\n" + out.strip() + "\n"
    if err.strip():
        log += "   [STDERR]:\n" + err.strip() + "\n"
    log += "   [Exit Code]: " + str(rc) + "\n"
    return log, rc


def leer(path, default=""):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return default


def matar_procesos():
    """Mata restos de capturas o inyecciones anteriores."""
    for patron in ("airodump-ng", "aireplay-ng"):
        sh(['pkill', '-9', '-f', patron])


def phy_de(netdev):
    return leer(f"/sys/class/net/{netdev}/phy80211/name") or None


def tipo_netdev(netdev):
    """1 = Ethernet, 803 = radiotap (modo monitor real)."""
    return leer(f"/sys/class/net/{netdev}/type")


def mac_real_wlan0():
    addr = leer("/sys/class/net/wlan0/address")
    if addr and len(addr) == 17:
        return addr
    return "b8:27:eb:00:00:00"


def mon_listo():
    return (os.path.exists(f"/sys/class/net/{MON_IFACE}") and
            tipo_netdev(MON_IFACE) == "803")


def _crear_monitor(logs):
    """Crea la interfaz monitor mon0 dedicada."""
    sh(['nmcli', 'device', 'set', 'wlan0', 'managed', 'no'])
    sh(['ip', 'link', 'set', 'wlan0', 'up'])
    time.sleep(0.4)

    # monitor=0 es OBLIGATORIO antes de crear el vif con nexutil
    sh(['nexutil', '-Iwlan0', '-m0'])
    sh(['ip', 'link', 'set', 'wlan0', 'down'])

    phy = phy_de("wlan0")
    if not phy:
        logs.append("[!] No se pudo determinar el phy de wlan0.")
        return False

    rc, out, err = sh(['iw', 'phy', phy, 'interface', 'add', MON_IFACE, 'type', 'monitor'])
    if rc != 0:
        logs.append(f"[!] Fallo creando {MON_IFACE} sobre {phy}: {(err or out).strip()}")
        return False

    sh(['ip', 'link', 'set', MON_IFACE, 'up'])

    if tipo_netdev(MON_IFACE) != "803":
        logs.append(f"[!] {MON_IFACE} no ha quedado en radiotap (tipo={tipo_netdev(MON_IFACE)}).")
        return False

    logs.append(f"[+] Interfaz monitor {MON_IFACE} lista (radiotap sobre {phy}).")
    return True


def preparar_monitor(logs):
    """Garantiza una interfaz monitor funcional."""
    matar_procesos()

    if mon_listo():
        sh(['ip', 'link', 'set', MON_IFACE, 'up'])
        logs.append(f"[+] Reutilizando la interfaz monitor {MON_IFACE}.")
        return True

    # Restos en estado inconsistente
    if os.path.exists(f"/sys/class/net/{MON_IFACE}"):
        logs.append(f"[*] Eliminando {MON_IFACE} en estado inconsistente...")
        sh(['ip', 'link', 'set', MON_IFACE, 'down'])
        sh(['iw', 'dev', MON_IFACE, 'del'])
        time.sleep(0.5)

    logs.append(f"[*] Creando la interfaz monitor {MON_IFACE}...")
    if _crear_monitor(logs):
        return True

    # Recuperación de módulo brcmfmac si el firmware se quedó bloqueado
    logs.append("[*] Recuperando el driver brcmfmac (recarga del módulo)...")
    sh(['modprobe', '-r', 'brcmfmac'], timeout=40)
    time.sleep(1)
    sh(['modprobe', 'brcmfmac'], timeout=40)
    time.sleep(3)

    if _crear_monitor(logs):
        return True

    logs.append("[X] No se ha podido habilitar el modo monitor en esta tarjeta.")
    return False


def _ip_propia():
    """IP de la Pi en la LAN."""
    rc, out, _ = sh(['ip', 'route', 'get', '1.1.1.1'])
    m = re.search(r'src\s+(\d{1,3}(?:\.\d{1,3}){3})', out)
    return m.group(1) if m else ""


def _mapa_ips_y_nombres():
    """Devuelve {mac_minusculas: dict(ip, hostname, is_static, vendor, icon, cat)} cruzando estado completo y DHCP."""
    res = {}
    build_state = _context.get('build_state')
    if callable(build_state):
        try:
            st = build_state()
            for d in st.get('devices', []):
                mac = (d.get('mac') or '').strip().lower()
                if mac and mac != '00:00:00:00:00:00':
                    is_st = bool(d.get('static') or d.get('is_static', False))
                    res[mac] = {
                        'ip': d.get('ip') or '',
                        'hostname': d.get('custom_name') or d.get('hostname') or '',
                        'is_static': is_st,
                        'static_order': d.get('static_order_idx'),
                        'manual_static': bool(d.get('manual_static')),
                        'vendor': d.get('dev_vendor') or '',
                        'icon': d.get('dev_icon') or '📱',
                        'cat': d.get('dev_cat') or 'dispositivo'
                    }
            if res:
                return res
        except Exception:
            pass

    # Fallback si build_state no está disponible
    read_leases = _context.get('read_leases')
    if callable(read_leases):
        try:
            data = read_leases()
            for l in data.get('leases', []):
                mac = (l.get('mac') or '').strip().lower()
                ip = (l.get('ip') or '').strip()
                host = (l.get('hostname') or '').strip()
                is_static = bool(l.get('static', False))
                if mac and mac != '00:00:00:00:00:00':
                    res[mac] = {
                        'ip': ip,
                        'hostname': host,
                        'is_static': is_static,
                        'vendor': '',
                        'icon': '📱',
                        'cat': 'dispositivo'
                    }
        except Exception:
            pass

    # Tabla ARP
    get_arp = _context.get('get_arp_table')
    if callable(get_arp):
        try:
            arp = get_arp()
            for mac, ips in arp.items():
                mac_l = mac.strip().lower()
                if ips and mac_l not in res:
                    res[mac_l] = {
                        'ip': ips[0],
                        'hostname': '',
                        'is_static': False,
                        'vendor': '',
                        'icon': '📱',
                        'cat': 'dispositivo'
                    }
        except Exception:
            pass

    return res


def _parsear_csv(ruta):
    """Extrae los clientes asociados del CSV de airodump-ng."""
    aps = {}
    estaciones = []

    try:
        with open(ruta, "r", encoding="latin1", errors="replace") as f:
            lineas = f.readlines()
    except Exception:
        return []

    en_estaciones = False
    for linea in lineas:
        s = linea.strip()
        if not s:
            continue
        if s.startswith("Station MAC"):
            en_estaciones = True
            continue

        parts = [p.strip() for p in s.split(",")]

        if not en_estaciones:
            if len(parts) < 14 or parts[0] == "BSSID" or not parts[0]:
                continue
            bssid = parts[0]
            canal = parts[3] if parts[3].isdigit() else "1"
            essid = ",".join(parts[13:-1]).strip()
            aps[bssid] = {"channel": canal, "essid": essid}
        else:
            if len(parts) < 6 or not parts[0]:
                continue
            cliente = parts[0]
            bssid = parts[5]
            if bssid not in aps:
                continue
            estaciones.append({
                "client": cliente,
                "bssid": bssid,
                "essid": aps[bssid]["essid"],
                "channel": aps[bssid]["channel"],
            })

    return estaciones


def _captura_csv(prefijo, segundos, logs):
    """Lanza airodump-ng sobre mon0 y devuelve la ruta del CSV o None."""
    sh(['bash', '-c', f"rm -f {prefijo}*"])

    proc = subprocess.Popen(
        ['sudo', 'airodump-ng', '-w', prefijo, '--output-format', 'csv',
         '--write-interval', '1', MON_IFACE],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    logs.append(f"[*] Capturando {segundos}s en {MON_IFACE} (salto de canales)...")
    time.sleep(segundos)

    sh(['pkill', '-9', '-f', 'airodump-ng'])
    try:
        proc.kill()
    except Exception:
        pass
    time.sleep(0.5)

    ficheros = sorted(glob.glob(prefijo + '*.csv'), key=os.path.getmtime, reverse=True)
    return ficheros[0] if ficheros else None


def _canal_de_bssid(bssid, logs):
    """Segunda pasada rápida para localizar el canal de un BSSID concreto."""
    ruta = _captura_csv('/tmp/wifi_chan', CANAL_SCAN_SECONDS, logs)
    if not ruta:
        logs.append("[!] No se generó CSV para la autodetección de canal.")
        return '1'

    try:
        with open(ruta, "r", encoding="latin1", errors="replace") as f:
            for linea in f:
                if bssid.lower() in linea.lower():
                    parts = [p.strip() for p in linea.split(',')]
                    if len(parts) > 3 and parts[3].isdigit():
                        return parts[3]
    except Exception as e:
        logs.append(f"[!] Error leyendo CSV de canal: {e}")

    logs.append("[!] BSSID no localizado; usando canal 1 por defecto.")
    return '1'


def _deauth(bssid, cliente, canal, logs):
    """Sintoniza el canal y lanza el deauth 802.11 sobre mon0."""
    if canal and str(canal).isdigit():
        rc, out, err = sh(['iw', 'dev', MON_IFACE, 'set', 'channel', str(canal)])
        logs.append(f"[*] Sintonizando {MON_IFACE} al canal {canal} (rc={rc}) {(err or out).strip()}")

    mac = mac_real_wlan0()
    logs.append(f"[*] MAC de origen de la interfaz: {mac}")

    log, rc = ejecutar_comando_debug(
        ['aireplay-ng', '--deauth', '10', '-a', bssid, '-c', cliente,
         '-h', mac, '--ignore-negative-one', MON_IFACE], timeout=90)
    logs.append(log)
    return rc == 0


def send_rf_deauth_if_available(client_mac, bssid=None, channel=None):
    """Función de conveniencia para invocar deauth por RF desde el panel principal."""
    if not mon_listo():
        return False, "Modo monitor no activo"
    logs = []
    c_mac = (client_mac or '').strip().lower()
    if not bssid and c_mac in _CACHE_CLIENTES_RF:
        bssid = _CACHE_CLIENTES_RF[c_mac].get('bssid')
        if not channel:
            channel = _CACHE_CLIENTES_RF[c_mac].get('channel')
    if not channel and bssid:
        channel = _canal_de_bssid(bssid, logs)
    channel = channel or '1'
    bssid = bssid or 'FF:FF:FF:FF:FF:FF'
    ok = _deauth(bssid, client_mac, channel, logs)
    return ok, "\n".join(logs)


def init_app(app, context):
    """Registra las rutas y endpoints del plugin Wi-Fi en la aplicación Flask."""
    global _context
    _context = context

    @app.route('/api/wifi/status', methods=['GET'])
    def api_wifi_status():
        load_cfg = _context.get('load_config', lambda: {})
        cfg = load_cfg()
        enabled = bool(cfg.get('wifi_plugin_enabled', False))
        has_wlan0 = os.path.exists('/sys/class/net/wlan0')
        has_mon = mon_listo()
        has_aircrack = bool(shutil.which('airodump-ng') or os.path.exists('/usr/sbin/airodump-ng') or os.path.exists('/usr/bin/airodump-ng'))
        has_nexutil = (shutil.which('nexutil') is not None) or os.path.exists('/usr/bin/nexutil') or os.path.exists('/usr/local/bin/nexutil')
        mode = 'monitor' if has_mon else 'normal'

        return jsonify({
            'status': 'success',
            'enabled': enabled,
            'version': VERSION,
            'has_wlan0': has_wlan0,
            'has_mon': has_mon,
            'mon_iface': MON_IFACE,
            'mode': mode,
            'has_aircrack': has_aircrack,
            'has_nexutil': has_nexutil,
            'pi_ip': _ip_propia(),
            'scanned_clients': _CACHE_CLIENTES_RF,
            'scanned_count': len(_CACHE_CLIENTES_RF)
        })

    @app.route('/api/wifi/toggle-plugin', methods=['POST'])
    def api_wifi_toggle_plugin():
        req = request.json or {}
        enable = bool(req.get('enable', False))
        load_cfg = _context.get('load_config', lambda: {})
        save_cfg = _context.get('save_config_raw') or _context.get('save_config')
        cfg = load_cfg()
        cfg['wifi_plugin_enabled'] = enable
        if callable(save_cfg):
            save_cfg(cfg)
        return jsonify({
            'status': 'success',
            'enabled': enable,
            'message': f"Plugin Wi-Fi RF {'activado' if enable else 'desactivado'} correctamente."
        })

    @app.route('/api/wifi/install-deps', methods=['POST'])
    def api_wifi_install_deps():
        logs = ["[*] Iniciando asistente de instalación y preparación de dependencias Wi-Fi..."]

        has_aircrack = shutil.which('airodump-ng') is not None
        if not has_aircrack:
            logs.append("[*] Instalando aircrack-ng y wireless-tools vía apt-get...")
            log1, rc1 = ejecutar_comando_debug(['apt-get', 'update'], timeout=120)
            logs.append(log1)
            log2, rc2 = ejecutar_comando_debug(['apt-get', 'install', '-y', 'aircrack-ng', 'wireless-tools'], timeout=180)
            logs.append(log2)
        else:
            logs.append("[+] Herramientas aircrack-ng (airodump-ng, aireplay-ng) ya instaladas.")

        if os.path.exists('/sys/class/net/wlan0'):
            logs.append("[+] Interfaz de red inalámbrica wlan0 detectada.")
        else:
            logs.append("[!] Advertencia: No se detecta wlan0 en el sistema.")

        has_nex = shutil.which('nexutil') is not None or os.path.exists('/usr/bin/nexutil')
        if has_nex:
            logs.append("[+] Utilidad nexutil detectada (firmware Nexmon presente).")
        else:
            logs.append("[i] nexutil no encontrado en PATH; si tu tarjeta usa driver estándar se usará iw directamente.")

        logs.append("[+] Comprobación finalizada.")
        return jsonify({
            'status': 'success',
            'output': "\n".join(logs),
            'has_aircrack': shutil.which('airodump-ng') is not None,
            'has_wlan0': os.path.exists('/sys/class/net/wlan0')
        })

    @app.route('/api/wifi/set-mode', methods=['POST'])
    def api_wifi_set_mode():
        data = request.get_json(silent=True) or {}
        mode = (data.get('mode') or '').strip().lower()
        logs = [f"[*] [{VERSION}] Cambio de modo solicitado: {mode.upper()}"]

        try:
            if mode == 'monitor':
                if preparar_monitor(logs):
                    logs.append(f"[+] Modo monitor activo en {MON_IFACE}.")
                    return jsonify({'status': 'success', 'mode': 'monitor', 'output': "\n".join(logs)})
                return jsonify({'status': 'error', 'mode': 'normal', 'output': "\n".join(logs)})

            if mode == 'normal':
                matar_procesos()
                if os.path.exists(f"/sys/class/net/{MON_IFACE}"):
                    sh(['ip', 'link', 'set', MON_IFACE, 'down'])
                    sh(['iw', 'dev', MON_IFACE, 'del'])
                sh(['nexutil', '-Iwlan0', '-m0'])
                sh(['ip', 'link', 'set', 'wlan0', 'down'])
                sh(['iw', 'dev', 'wlan0', 'set', 'type', 'managed'])
                sh(['ip', 'link', 'set', 'wlan0', 'up'])
                sh(['nmcli', 'device', 'set', 'wlan0', 'managed', 'yes'])
                sh(['systemctl', 'restart', 'wpa_supplicant'])
                logs.append("[+] wlan0 devuelta a modo normal (Managed / NetworkManager).")
                return jsonify({'status': 'success', 'mode': 'normal', 'output': "\n".join(logs)})

            logs.append(f"[!] Modo desconocido: {mode}")
            return jsonify({'status': 'error', 'output': "\n".join(logs)})

        except Exception as e:
            logs.append(f"[EXCEPCION en set_mode]: {e}")
            return jsonify({'status': 'error', 'output': "\n".join(logs)})

    @app.route('/api/wifi/scan', methods=['GET'])
    def api_wifi_scan():
        logs = [f"[*] [{VERSION}] Solicitud de escaneo de espectro Wi-Fi."]
        try:
            if not preparar_monitor(logs):
                return jsonify({
                    'status': 'error', 'devices': [],
                    'debug': "\n".join(logs),
                    'message': 'No se pudo activar el modo monitor para escanear.'
                })

            ruta = _captura_csv('/tmp/wifi_scan', SCAN_SECONDS, logs)
            if not ruta:
                logs.append("[!] airodump-ng no generó ningún fichero CSV.")
                return jsonify({
                    'status': 'error', 'devices': [],
                    'debug': "\n".join(logs),
                    'message': 'La captura no generó datos en el aire.'
                })

            estaciones = _parsear_csv(ruta)
            mapa = _mapa_ips_y_nombres()
            resueltas = 0
            for est in estaciones:
                c_mac = est["client"].lower()
                dev_info = mapa.get(c_mac, {})
                est["ip"] = dev_info.get("ip", "")
                est["hostname"] = dev_info.get("hostname", "")
                est["is_static"] = bool(dev_info.get("is_static", False))
                est["static_order"] = dev_info.get("static_order")
                est["manual_static"] = bool(dev_info.get("manual_static", False))
                est["vendor"] = dev_info.get("vendor", "")
                est["icon"] = dev_info.get("icon", "📱")
                est["cat"] = dev_info.get("cat", "dispositivo")
                _CACHE_CLIENTES_RF[c_mac] = {
                    'bssid': est.get('bssid'),
                    'channel': est.get('channel'),
                    'essid': est.get('essid'),
                    'hostname': est["hostname"],
                    'ip': est["ip"],
                    'ts': time.time()
                }
                if est["ip"]:
                    resueltas += 1

            _guardar_cache_rf()

            logs.append(f"[+] Escaneo completado. Clientes detectados en el aire: {len(estaciones)}")
            logs.append(f"[+] IP y nombre resueltos para {resueltas} de {len(estaciones)} clientes (DHCP/ARP).")

            return jsonify({
                'status': 'success',
                'devices': estaciones,
                'debug': "\n".join(logs),
                'pi_ip': _ip_propia(),
                'mon_iface': MON_IFACE
            })
        except Exception as e:
            logs.append(f"[EXCEPCION en api_wifi_scan]: {e}")
            return jsonify({'status': 'error', 'devices': [], 'debug': "\n".join(logs)})

    @app.route('/api/wifi/deauth', methods=['POST'])
    def api_wifi_deauth():
        data = request.get_json(silent=True) or {}
        bssid = (data.get('bssid') or '').strip()
        cliente = (data.get('client') or '').strip()
        canal = (data.get('channel') or '').strip()
        auto_channel = bool(data.get('auto_channel', False))

        if not bssid or not cliente:
            return jsonify({'status': 'error', 'message': 'BSSID y Cliente son obligatorios.'})

        logs = [f"[*] [{VERSION}] Orden de desasociación RF - BSSID: {bssid} | Cliente: {cliente}"]

        try:
            if not preparar_monitor(logs):
                return jsonify({'status': 'error', 'output': "\n".join(logs)})

            if auto_channel or not canal or not str(canal).isdigit():
                logs.append("[*] Autodetectando canal de radio...")
                canal = _canal_de_bssid(bssid, logs)
                logs.append(f"[*] Canal detectado: {canal}")

            ok = _deauth(bssid, cliente, canal, logs)
            return jsonify({
                'status': 'success' if ok else 'warning',
                'output': "\n".join(logs),
                'channel': canal
            })
        except Exception as e:
            logs.append(f"[EXCEPCION en deauth]: {e}")
            return jsonify({'status': 'error', 'output': "\n".join(logs)})
