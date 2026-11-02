# -*- coding: utf-8 -*-
"""
Funciones avanzadas del Panel DHCP:
  - Persistencia (SQLite): historial de presencia, servicios conocidos, comprobaciones, eventos
  - Monitor en segundo plano (latencia, TTL/SO, estado real de servicios, presencia)
  - Alertas (ntfy, Telegram, webhook genérico / Home Assistant)
  - Exportar / importar configuración con vista previa
  - Mapa de IPs, diagnóstico de red, ficha de dispositivo, línea temporal
  - Acciones: bloquear Internet (AdGuard), Wake-on-LAN, escaneo completo de puertos
"""
import os
import re
import json
import time
import socket
import sqlite3
import secrets
import smtplib
import html
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate
import subprocess
import urllib.request
import urllib.parse
import http.cookiejar
import io
import zipfile
import base64
from collections import Counter
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, jsonify, Response

bp = Blueprint('extras', __name__)

D = {}                    # dependencias inyectadas desde app.py
DB_PATH = None
PHOTOS_DIR = None
_DB_LOCK = threading.Lock()
_PING = {}                # ip -> {'ts', 'ms', 'ttl', 'alive'}
_MONITOR_STATE = {'last_run': 0, 'running': False, 'last_error': '', 'cycles': 0}
_SCAN_JOBS = {}           # job_id -> {...}
MONITOR_INTERVAL = int(os.environ.get('DHCP_PANEL_MONITOR_INTERVAL', '60'))
SERVICE_DOWN_THRESHOLD = 2   # comprobaciones fallidas seguidas para marcar como caído en panel
SERVICE_DOWN_ALERT_SEC = 600  # 10 minutos (600 s) caído antes de emitir notificación al usuario
OFFLINE_GRACE_SEC = 300      # segundos sin ver un dispositivo antes de marcarlo desconectado

DEFAULT_ALERTS = {
    'enabled': False,
    'ntfy_url': '',
    'telegram_token': '',
    'telegram_chat_id': '',
    'webhook_url': '',
    'email_enabled': False,
    'smtp_host': 'smtp.gmail.com',
    'smtp_port': 587,
    'smtp_user': '',
    'smtp_pass': '',
    'smtp_to': '',
    'smtp_tls': True,
    'email_notify_new_device': True,
    'email_notify_device_connect': False,
    'notify_new_device': True,
    'notify_device_connect': False,
    'notify_service_down': True,
    'notify_service_up': True,
    'notify_watched_offline': True,
    'watched_macs': [],
}


# =====================================================================
#  Utilidades
# =====================================================================
def now_ts():
    return int(time.time())


def iso(ts):
    if not ts:
        return ''
    return datetime.fromtimestamp(int(ts), timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def norm_mac(mac):
    return (mac or '').strip().lower().replace('-', ':')


def valid_mac(mac):
    return bool(re.fullmatch(r'([0-9a-f]{2}:){5}[0-9a-f]{2}', norm_mac(mac)))


def valid_ipv4(ip):
    try:
        parts = [int(x) for x in (ip or '').split('.')]
        return len(parts) == 4 and all(0 <= p <= 255 for p in parts)
    except Exception:
        return False


# =====================================================================
#  Base de datos
# =====================================================================
def db():
    con = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def db_exec(sql, params=(), many=False):
    with _DB_LOCK:
        con = db()
        try:
            if many:
                con.executemany(sql, params)
            else:
                con.execute(sql, params)
            con.commit()
        finally:
            con.close()


def db_query(sql, params=()):
    with _DB_LOCK:
        con = db()
        try:
            return [dict(r) for r in con.execute(sql, params).fetchall()]
        finally:
            con.close()


def init_db():
    with _DB_LOCK:
        con = db()
        con.executescript('''
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS devices (
                mac TEXT PRIMARY KEY,
                first_seen INTEGER, last_seen INTEGER, last_ip TEXT, hostname TEXT,
                online INTEGER DEFAULT 0,
                notes TEXT DEFAULT '', room TEXT DEFAULT '', tags TEXT DEFAULT '[]',
                known INTEGER DEFAULT 1,
                latency_ms REAL, ttl INTEGER
            );
            CREATE TABLE IF NOT EXISTS device_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER, mac TEXT, ip TEXT, event TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_dev_events ON device_events(mac, ts);
            CREATE TABLE IF NOT EXISTS services (
                url TEXT PRIMARY KEY,
                mac TEXT, ip TEXT, port INTEGER, label TEXT,
                first_seen INTEGER, last_seen_up INTEGER, last_check INTEGER,
                up INTEGER DEFAULT 1, fail_count INTEGER DEFAULT 0, latency_ms REAL,
                alerted_down INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS service_checks (
                url TEXT, ts INTEGER, up INTEGER, ms REAL
            );
            CREATE INDEX IF NOT EXISTS idx_svc_checks ON service_checks(url, ts);
            CREATE TABLE IF NOT EXISTS events_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER, kind TEXT, title TEXT, message TEXT, sent INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v TEXT);
        ''')
        try:
            con.execute("ALTER TABLE devices ADD COLUMN photo TEXT DEFAULT ''")
        except Exception:
            pass
        con.commit()
        con.close()


def kv_get(k, default=None):
    r = db_query('SELECT v FROM kv WHERE k=?', (k,))
    return json.loads(r[0]['v']) if r else default


def kv_set(k, v):
    db_exec('INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)', (k, json.dumps(v)))

def save_device_photo_file(mac, photo_data_url):
    """Guarda la foto como archivo en disco en PHOTOS_DIR y devuelve la ruta."""
    if not photo_data_url or not PHOTOS_DIR:
        return None
    try:
        clean_mac = norm_mac(mac).replace(':', '-').lower()
        if ',' in photo_data_url:
            header, b64 = photo_data_url.split(',', 1)
            ext = 'webp' if 'webp' in header else ('jpeg' if 'jpeg' in header or 'jpg' in header else 'png')
            raw = base64.b64decode(b64)
            filepath = os.path.join(PHOTOS_DIR, f"{clean_mac}.{ext}")
            with open(filepath, 'wb') as f:
                f.write(raw)
            return filepath
    except Exception as e:
        print(f"Error guardando foto en disco para {mac}: {e}")
    return None


def get_device_photo_data_url(mac):
    """Devuelve el data URL de la foto desde SQLite o desde disco si existe."""
    clean_mac = norm_mac(mac).replace(':', '-').lower()
    row = db_query('SELECT photo FROM devices WHERE mac=?', (norm_mac(mac),))
    if row and row[0]['photo']:
        return row[0]['photo']
    if PHOTOS_DIR and os.path.exists(PHOTOS_DIR):
        for ext in ('webp', 'jpeg', 'jpg', 'png'):
            fpath = os.path.join(PHOTOS_DIR, f"{clean_mac}.{ext}")
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'rb') as f:
                        b64 = base64.b64encode(f.read()).decode('ascii')
                    mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
                    return f"data:{mime};base64,{b64}"
                except Exception:
                    pass
    return ''



# =====================================================================
#  Ping / latencia / TTL
# =====================================================================
def ping_detail(ip):
    try:
        res = subprocess.run(['ping', '-c', '1', '-W', '1', ip], capture_output=True, text=True, timeout=3)
        out = res.stdout
        m_t = re.search(r'time[=<]([\d.]+)\s*ms', out)
        m_ttl = re.search(r'ttl=(\d+)', out, re.IGNORECASE)
        alive = res.returncode == 0 and bool(m_t)
        return {'ts': now_ts(), 'alive': alive,
                'ms': float(m_t.group(1)) if m_t else None,
                'ttl': int(m_ttl.group(1)) if m_ttl else None}
    except Exception:
        return {'ts': now_ts(), 'alive': False, 'ms': None, 'ttl': None}


def os_guess(ttl, dev_class=''):
    if not ttl:
        return ''
    c = (dev_class or '').lower()
    # Si la clase del dispositivo ya nos indica qué tipo de equipo es, la respetamos
    if any(k in c for k in ['smartphone', 'móvil', 'movil', 'android', 'phone']):
        return 'Android'
    if any(k in c for k in ['iphone', 'ipad', 'apple', 'macbook', 'imac', 'macos']):
        return 'iOS / macOS'
    if any(k in c for k in ['enchufe', 'bombilla', 'sensor', 'esp', 'domótica', 'domotica', 'cámara', 'camara', 'cam', 'iot']):
        return 'Firmware IoT (RTOS)'

    if ttl <= 64:
        return 'Linux / Android / Unix'
    if ttl <= 128:
        return 'Windows'
    return 'Equipo de red (Cisco/Router)'

def tcp_latency(ip, port, timeout=1.5):
    t0 = time.time()
    try:
        s = socket.create_connection((ip, int(port)), timeout=timeout)
        s.close()
        return True, round((time.time() - t0) * 1000, 1)
    except Exception:
        return False, None


# =====================================================================
#  Alertas
# =====================================================================
def get_alerts_cfg():
    cfg = D['load_config']()
    a = dict(DEFAULT_ALERTS)
    a.update(cfg.get('alerts') or {})
    return a


def _http_post(url, data, headers=None, timeout=8):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method='POST')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def send_smtp_email(host, port, user, password, to_addr, subject, body_text, body_html=None, use_tls=True):
    """Envía un correo electrónico mediante SMTP (ej. Gmail)."""
    if not host or not user or not password or not to_addr:
        return False, "Faltan credenciales SMTP (servidor, usuario, contraseña o destinatario)."
    clean_pass = (password or '').replace(' ', '').strip()
    user = (user or '').strip()
    to_addr = (to_addr or '').strip()
    host = (host or 'smtp.gmail.com').strip()
    try:
        port = int(port or 587)
    except (ValueError, TypeError):
        port = 587

    msg = MIMEMultipart('alternative')
    msg['From'] = f"Panel DHCP <{user}>"
    msg['To'] = to_addr
    msg['Subject'] = subject
    msg['Date'] = formatdate(localtime=True)
    msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    if body_html:
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    try:
        if port == 465:
            server = smtplib.SMTP_SSL(host, port, timeout=12)
        else:
            server = smtplib.SMTP(host, port, timeout=12)
            if use_tls:
                server.starttls()
        server.login(user, clean_pass)
        server.sendmail(user, [to_addr], msg.as_string())
        server.quit()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def build_device_alert_content(d, is_new=True, is_watched=False):
    """Construye el contenido en texto plano y HTML detallado para alertas de dispositivos."""
    hostname = d.get('hostname') or d.get('custom_name') or '(Sin nombre registrado)'
    ip = d.get('ip') or '(Sin IP)'
    mac = norm_mac(d.get('mac') or '')
    vendor = d.get('dev_vendor') or 'Desconocido'
    dev_class = d.get('dev_class') or 'Dispositivo de red'
    node = d.get('router_node') or 'Router Principal / Red Local'
    medium = d.get('conn_medium_label') or 'Desconocido'
    rssi = f"{d.get('wifi_rssi')} dBm" if d.get('wifi_rssi') else (d.get('wifi_signal') or 'N/A')
    ip_type = 'Estática (Fija)' if d.get('static') else 'Dinámica (DHCP)'
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if is_watched:
        title = f"🔔 Dispositivo marcado conectado: {hostname}"
    elif is_new:
        title = f"🚨 Nuevo dispositivo conectado: {hostname}"
    else:
        title = f"⚡ Dispositivo conectado: {hostname}"

    text_body = (
        f"{title}\n"
        f"-----------------------------------------\n"
        f"Nombre de equipo : {hostname}\n"
        f"Dirección IP     : {ip} ({ip_type})\n"
        f"Dirección MAC    : {mac}\n"
        f"Fabricante (OUI) : {vendor}\n"
        f"Tipo de equipo   : {dev_class}\n"
        f"Punto de acceso  : {node}\n"
        f"Medio de enlace  : {medium}\n"
        f"Señal Wi-Fi      : {rssi}\n"
        f"Fecha y hora     : {time_str}\n"
        f"-----------------------------------------\n"
        f"Acceso al Panel: http://192.168.1.249:5001\n"
    )

    if is_watched:
        hdr_bg = 'linear-gradient(135deg, #d97706, #b45309)'
        hdr_title = f'🔔 Dispositivo marcado conectado a la red'
    elif is_new:
        hdr_bg = 'linear-gradient(135deg, #dc2626, #991b1b)'
        hdr_title = '🚨 Nuevo dispositivo conectado a la red'
    else:
        hdr_bg = 'linear-gradient(135deg, #0284c7, #0369a1)'
        hdr_title = '⚡ Dispositivo conectado / inicio de sesión'

    html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:20px; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color:#0f172a; color:#e2e8f0;">
  <div style="max-width:600px; margin:0 auto; background:#1e293b; border-radius:12px; border:1px solid #334155; overflow:hidden; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <div style="background:{hdr_bg}; padding:20px; color:#ffffff;">
      <h2 style="margin:0; font-size:1.25rem;">{hdr_title}</h2>
      <div style="font-size:0.88rem; opacity:0.9; margin-top:4px;">{time_str}</div>
    </div>
    <div style="padding:22px;">
      <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8; width:38%;">Nombre de equipo:</td>
          <td style="padding:9px 0; font-weight:bold; color:#f8fafc;">{html.escape(hostname)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Dirección IP:</td>
          <td style="padding:9px 0; font-family:monospace; color:#38bdf8; font-weight:bold;">{html.escape(ip)} <span style="font-size:0.8rem; color:#94a3b8; font-weight:normal;">({ip_type})</span></td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Dirección MAC:</td>
          <td style="padding:9px 0; font-family:monospace; color:#cbd5e1;">{html.escape(mac)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Fabricante:</td>
          <td style="padding:9px 0; color:#cbd5e1;">{html.escape(vendor)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Tipo de equipo:</td>
          <td style="padding:9px 0; color:#cbd5e1;">{html.escape(dev_class)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Punto de acceso / Nodo:</td>
          <td style="padding:9px 0; color:#cbd5e1; font-weight:600;">{html.escape(node)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">Medio de enlace:</td>
          <td style="padding:9px 0; color:#cbd5e1;">{html.escape(medium)}</td>
        </tr>
        <tr>
          <td style="padding:9px 0; color:#94a3b8;">Señal Wi-Fi:</td>
          <td style="padding:9px 0; color:#cbd5e1;">{html.escape(str(rssi))}</td>
        </tr>
      </table>
      <div style="margin-top:24px; text-align:center;">
        <a href="http://192.168.1.249:5001" style="display:inline-block; background:#38bdf8; color:#0f172a; text-decoration:none; font-weight:bold; padding:10px 24px; border-radius:8px; font-size:0.9rem;">
          Abrir Panel DHCP
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""
    return title, text_body, html_body


def build_service_alert_content(url, label, ip, port, down_seconds, is_down=True):
    """Construye el contenido en texto plano y HTML para alertas de servicios."""
    time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    down_min = max(10, down_seconds // 60)
    label_str = label or url
    if is_down:
        title = f"🔴 Servicio web caído (10+ min): {label_str}"
        text_body = (
            f"{title}\n"
            f"-----------------------------------------\n"
            f"Servicio         : {label_str}\n"
            f"URL              : {url}\n"
            f"IP / Puerto      : {ip}:{port}\n"
            f"Tiempo de caída  : más de {down_min} minutos\n"
            f"Fecha y hora     : {time_str}\n"
            f"-----------------------------------------\n"
            f"Acceso al Panel: http://192.168.1.249:5001\n"
        )
        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:20px; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color:#0f172a; color:#e2e8f0;">
  <div style="max-width:600px; margin:0 auto; background:#1e293b; border-radius:12px; border:1px solid #ef4444; overflow:hidden; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <div style="background:linear-gradient(135deg, #dc2626, #991b1b); padding:20px; color:#ffffff;">
      <h2 style="margin:0; font-size:1.25rem;">🔴 Servicio web caído hace más de {down_min} minutos</h2>
      <div style="font-size:0.88rem; opacity:0.9; margin-top:4px;">{time_str}</div>
    </div>
    <div style="padding:22px;">
      <table style="width:100%; border-collapse:collapse; font-size:0.9rem;">
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8; width:35%;">Servicio:</td>
          <td style="padding:9px 0; font-weight:bold; color:#f8fafc;">{html.escape(label_str)}</td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">URL:</td>
          <td style="padding:9px 0; font-family:monospace; color:#38bdf8;"><a href="{html.escape(url)}" style="color:#38bdf8;">{html.escape(url)}</a></td>
        </tr>
        <tr style="border-bottom:1px solid #334155;">
          <td style="padding:9px 0; color:#94a3b8;">IP / Puerto:</td>
          <td style="padding:9px 0; font-family:monospace; color:#cbd5e1;">{html.escape(str(ip))}:{html.escape(str(port))}</td>
        </tr>
        <tr>
          <td style="padding:9px 0; color:#94a3b8;">Tiempo de caída:</td>
          <td style="padding:9px 0; color:#ef4444; font-weight:bold;">Más de {down_min} minutos</td>
        </tr>
      </table>
      <div style="margin-top:24px; text-align:center;">
        <a href="http://192.168.1.249:5001" style="display:inline-block; background:#38bdf8; color:#0f172a; text-decoration:none; font-weight:bold; padding:10px 24px; border-radius:8px; font-size:0.9rem;">
          Revisar en Panel DHCP
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""
    else:
        title = f"🟢 Servicio recuperado: {label_str}"
        text_body = (
            f"{title}\n"
            f"-----------------------------------------\n"
            f"Servicio         : {label_str}\n"
            f"URL              : {url}\n"
            f"Estado           : Restablecido y respondiendo OK\n"
            f"Fecha y hora     : {time_str}\n"
            f"-----------------------------------------\n"
        )
        html_body = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:20px; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color:#0f172a; color:#e2e8f0;">
  <div style="max-width:600px; margin:0 auto; background:#1e293b; border-radius:12px; border:1px solid #10b981; overflow:hidden; box-shadow:0 10px 25px rgba(0,0,0,0.5);">
    <div style="background:linear-gradient(135deg, #059669, #047857); padding:20px; color:#ffffff;">
      <h2 style="margin:0; font-size:1.25rem;">🟢 Servicio web restablecido</h2>
      <div style="font-size:0.88rem; opacity:0.9; margin-top:4px;">{time_str}</div>
    </div>
    <div style="padding:22px;">
      <p style="margin:0 0 12px; font-size:0.95rem;">El servicio <strong>{html.escape(label_str)}</strong> ({html.escape(url)}) vuelve a responder con normalidad.</p>
      <div style="margin-top:16px; text-align:center;">
        <a href="http://192.168.1.249:5001" style="display:inline-block; background:#10b981; color:#0f172a; text-decoration:none; font-weight:bold; padding:8px 20px; border-radius:8px; font-size:0.85rem;">
          Ir al Panel
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""
    return title, text_body, html_body


def send_alert(title, message, kind='info', force=False, cfg_override=None, email_html=None, force_email=False):
    """Registra el evento y lo envía por los canales configurados (ntfy, Telegram, webhook, email SMTP). Devuelve lista de resultados."""
    a = cfg_override or get_alerts_cfg()
    results = []
    sent = 0
    if a.get('enabled') or force or force_email:
        prio = {'new_device': 'high', 'service_down': 'high', 'offline': 'default', 'watched_online': 'high'}.get(kind, 'default')
        tag = {'new_device': 'rotating_light', 'service_down': 'red_circle', 'service_up': 'green_circle',
               'offline': 'warning', 'online': 'white_check_mark', 'watched_online': 'bell', 'test': 'bell'}.get(kind, 'bell')
        if a.get('ntfy_url'):
            try:
                _http_post(a['ntfy_url'], message.encode('utf-8'),
                           {'Title': title.encode('utf-8').decode('latin-1', 'ignore'), 'Priority': prio, 'Tags': tag})
                results.append(('ntfy', True, 'OK'))
            except Exception as e:
                results.append(('ntfy', False, str(e)))
        if a.get('telegram_token') and a.get('telegram_chat_id'):
            try:
                url = f"https://api.telegram.org/bot{a['telegram_token']}/sendMessage"
                body = urllib.parse.urlencode({'chat_id': a['telegram_chat_id'], 'text': f'{title}\n{message}'}).encode()
                _http_post(url, body, {'Content-Type': 'application/x-www-form-urlencoded'})
                results.append(('telegram', True, 'OK'))
            except Exception as e:
                results.append(('telegram', False, str(e)))
        if a.get('webhook_url'):
            try:
                body = json.dumps({'title': title, 'message': message, 'kind': kind, 'ts': iso(now_ts())}).encode()
                _http_post(a['webhook_url'], body, {'Content-Type': 'application/json'})
                results.append(('webhook', True, 'OK'))
            except Exception as e:
                results.append(('webhook', False, str(e)))
        if a.get('email_enabled') or force_email or (force and a.get('smtp_user') and a.get('smtp_pass') and a.get('smtp_to')):
            if a.get('smtp_user') and a.get('smtp_pass') and a.get('smtp_to'):
                email_allowed = True
                if not force and not force_email:
                    if kind == 'new_device' and not a.get('email_notify_new_device', True):
                        email_allowed = False
                    elif kind == 'online' and not a.get('email_notify_device_connect', False):
                        email_allowed = False
                if email_allowed:
                    ok, err = send_smtp_email(
                        host=a.get('smtp_host') or 'smtp.gmail.com',
                        port=a.get('smtp_port') or 587,
                        user=a.get('smtp_user', '').strip(),
                        password=a.get('smtp_pass', '').strip(),
                        to_addr=a.get('smtp_to', '').strip(),
                        subject=f"[Panel DHCP] {title}",
                        body_text=message,
                        body_html=email_html,
                        use_tls=bool(a.get('smtp_tls', True))
                    )
                    results.append(('email', ok, err))
        sent = 1 if any(r[1] for r in results) else 0
    db_exec('INSERT INTO events_log (ts, kind, title, message, sent) VALUES (?,?,?,?,?)',
            (now_ts(), kind, title, message, sent))
    return results


# =====================================================================
#  Monitor en segundo plano
# =====================================================================
def monitor_cycle():
    state = D['build_state'](False)
    devices = state.get('devices', [])
    ts = now_ts()
    alerts = get_alerts_cfg()

    # --- Ping concurrente a dispositivos activos (latencia + TTL) ---
    ips = sorted({d['ip'] for d in devices if d.get('live_ips') and valid_ipv4(d.get('ip'))})
    with ThreadPoolExecutor(max_workers=32) as pool:
        for ip, r in zip(ips, pool.map(ping_detail, ips)):
            _PING[ip] = r

    # --- Presencia de dispositivos ---
    existing = {r['mac']: r for r in db_query('SELECT * FROM devices')}
    first_run = len(existing) == 0
    watched = set(norm_mac(m) for m in alerts.get('watched_macs', []))
    seen_now = set()
    for d in devices:
        mac = norm_mac(d.get('mac'))
        if not valid_mac(mac) or mac == '00:00:00:00:00:00':
            continue
        online = bool(d.get('live_ips'))
        p = _PING.get(d.get('ip')) or {}
        row = existing.get(mac)
        if online:
            seen_now.add(mac)
        if row is None:
            db_exec('''INSERT INTO devices (mac, first_seen, last_seen, last_ip, hostname, online, known, latency_ms, ttl)
                       VALUES (?,?,?,?,?,?,?,?,?)''',
                    (mac, ts, ts if online else None, d.get('ip'), d.get('hostname'), 1 if online else 0,
                     1 if first_run else 0, p.get('ms'), p.get('ttl')))
            db_exec('INSERT INTO device_events (ts, mac, ip, event) VALUES (?,?,?,?)',
                    (ts, mac, d.get('ip'), 'new' if not first_run else ('online' if online else 'offline')))
            if not first_run and online and alerts.get('notify_new_device', True):
                t, b_txt, b_html = build_device_alert_content(d, is_new=True)
                send_alert(t, b_txt, 'new_device', email_html=b_html)
            continue

        if online:
            active_live_ip = (d.get('live_ips') or [d.get('ip')])[0]
            db_exec('UPDATE devices SET last_seen=?, last_ip=?, hostname=?, latency_ms=COALESCE(?, latency_ms), ttl=COALESCE(?, ttl) WHERE mac=?',
                    (ts, active_live_ip, d.get('hostname'), p.get('ms'), p.get('ttl'), mac))
            if not row['online']:
                db_exec('UPDATE devices SET online=1 WHERE mac=?', (mac,))
                db_exec('INSERT INTO device_events (ts, mac, ip, event) VALUES (?,?,?,?)', (ts, mac, d.get('ip'), 'online'))
                if mac in watched:
                    t, b_txt, b_html = build_device_alert_content(d, is_new=False, is_watched=True)
                    send_alert(t, b_txt, 'watched_online', email_html=b_html, force_email=True)
                elif alerts.get('notify_device_connect', False):
                    t, b_txt, b_html = build_device_alert_content(d, is_new=False, is_watched=False)
                    send_alert(t, b_txt, 'online', email_html=b_html)
        else:
            last = row['last_seen'] or 0
            if row['online'] and ts - last > OFFLINE_GRACE_SEC:
                db_exec('UPDATE devices SET online=0 WHERE mac=?', (mac,))
                db_exec('INSERT INTO device_events (ts, mac, ip, event) VALUES (?,?,?,?)', (ts, mac, d.get('ip'), 'offline'))
                if mac in watched and alerts.get('notify_watched_offline', True):
                    send_alert('⚠️ Dispositivo marcado desconectado',
                               f"{d.get('hostname')} ({d.get('ip')}) no responde desde hace {OFFLINE_GRACE_SEC // 60} min.", 'offline', force_email=True)

    # --- Servicios: detectados ahora + recordados ---
    known = {r['url']: r for r in db_query('SELECT * FROM services')}
    detected = {}
    for d in devices:
        for l in d.get('web_links') or []:
            detected[l['url']] = (d, l)

    to_check = []
    for url, (d, l) in detected.items():
        to_check.append((url, d.get('ip'), l.get('port') or (443 if url.startswith('https') else 80), l.get('label'), norm_mac(d.get('mac'))))
    for url, r in known.items():
        if url not in detected:
            to_check.append((url, r['ip'], r['port'], r['label'], r['mac']))

    def _chk(item):
        url, ip, port, label, mac = item
        if url in detected:
            ok, ms = tcp_latency(ip, port)
            return item, True if not ok and ms is None and url in detected else ok, ms
        ok, ms = tcp_latency(ip, port)
        return item, ok, ms

    with ThreadPoolExecutor(max_workers=24) as pool:
        results = list(pool.map(_chk, to_check))

    checks = []
    for (url, ip, port, label, mac), ok, ms in results:
        checks.append((url, ts, 1 if ok else 0, ms))
        r = known.get(url)
        if r is None:
            db_exec('''INSERT INTO services (url, mac, ip, port, label, first_seen, last_seen_up, last_check, up, fail_count, latency_ms)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                    (url, mac, ip, port, label, ts, ts if ok else None, ts, 1 if ok else 0, 0 if ok else 1, ms))
            continue
        if ok:
            was_alerted = r['alerted_down']
            db_exec('''UPDATE services SET mac=?, ip=?, port=?, label=?, last_seen_up=?, last_check=?, up=1, fail_count=0,
                       latency_ms=?, alerted_down=0 WHERE url=?''', (mac or r['mac'], ip, port, label or r['label'], ts, ts, ms, url))
            if was_alerted and alerts.get('notify_service_up', True):
                t, b_txt, b_html = build_service_alert_content(url, label or r['label'], ip, port, 0, is_down=False)
                send_alert(t, b_txt, 'service_up', email_html=b_html)
        else:
            fc = (r['fail_count'] or 0) + 1
            alerted = r['alerted_down']
            last_up = r['last_seen_up'] or r['first_seen'] or ts
            down_seconds = max(0, ts - last_up)
            # Solo notificar si el servicio ha estado caído al menos 10 minutos (600s)
            if down_seconds >= SERVICE_DOWN_ALERT_SEC and not alerted:
                alerted = 1
                if alerts.get('notify_service_down', True):
                    t, b_txt, b_html = build_service_alert_content(url, label or r['label'], ip, port, down_seconds, is_down=True)
                    send_alert(t, b_txt, 'service_down', email_html=b_html)
            db_exec('UPDATE services SET last_check=?, up=?, fail_count=?, alerted_down=? WHERE url=?',
                    (ts, 0 if fc >= SERVICE_DOWN_THRESHOLD else 1, fc, alerted, url))
    if checks:
        db_exec('INSERT INTO service_checks (url, ts, up, ms) VALUES (?,?,?,?)', checks, many=True)

    # --- Limpieza diaria ---
    if ts - (kv_get('last_prune', 0) or 0) > 86400:
        db_exec('DELETE FROM service_checks WHERE ts < ?', (ts - 7 * 86400,))
        db_exec('DELETE FROM device_events WHERE ts < ?', (ts - 60 * 86400,))
        db_exec('DELETE FROM events_log WHERE ts < ?', (ts - 30 * 86400,))
        kv_set('last_prune', ts)


def monitor_loop():
    time.sleep(8)
    while True:
        t0 = time.time()
        _MONITOR_STATE['running'] = True
        try:
            monitor_cycle()
            _MONITOR_STATE['last_error'] = ''
        except Exception as e:
            _MONITOR_STATE['last_error'] = f'{type(e).__name__}: {e}'
        _MONITOR_STATE['running'] = False
        _MONITOR_STATE['last_run'] = now_ts()
        _MONITOR_STATE['cycles'] += 1
        time.sleep(max(10, MONITOR_INTERVAL - (time.time() - t0)))


# =====================================================================
#  Enriquecer /api/state con datos persistentes
# =====================================================================
def enrich_state(state):
    devs = {r['mac']: r for r in db_query('SELECT * FROM devices')}
    svc_rows = {r['url']: r for r in db_query('SELECT * FROM services')}
    since = now_ts() - 86400
    upt = {r['url']: r for r in db_query(
        'SELECT url, AVG(up) AS avg_up, COUNT(*) AS n FROM service_checks WHERE ts > ? GROUP BY url', (since,))}
    hist = {}
    for r in db_query('SELECT url, ts, up, ms FROM service_checks WHERE ts > ? ORDER BY ts', (now_ts() - 6 * 3600,)):
        hist.setdefault(r['url'], []).append([r['up'], r['ms']])
    blocked = set(get_blocked_clients(silent=True))
    is_lam = D.get('is_locally_administered_mac') or (lambda m: False)
    prev_ips_map = {}
    try:
        for r in db_query("SELECT mac, ip FROM device_events WHERE ip IS NOT NULL AND ip != '' ORDER BY ts ASC"):
            m_norm = norm_mac(r['mac'])
            if r['ip'] not in prev_ips_map.setdefault(m_norm, []):
                prev_ips_map[m_norm].append(r['ip'])
    except Exception:
        pass

    alerts_cfg = get_alerts_cfg()
    watched_set = set(norm_mac(m) for m in alerts_cfg.get('watched_macs', []))
    state['alerts_summary'] = {
        'enabled': bool(alerts_cfg.get('enabled')),
        'email_enabled': bool(alerts_cfg.get('email_enabled')),
        'smtp_configured': bool(alerts_cfg.get('smtp_user') and alerts_cfg.get('smtp_pass') and alerts_cfg.get('smtp_to')),
        'smtp_to': alerts_cfg.get('smtp_to', ''),
        'watched_count': len(watched_set),
        'watched_macs': sorted(list(watched_set))
    }

    detected_urls = set()
    for d in state.get('devices', []):
        mac = norm_mac(d.get('mac'))
        d['watched'] = mac in watched_set
        row = devs.get(mac) or {}
        p = _PING.get(d.get('ip')) or {}
        ttl = p.get('ttl') or row.get('ttl')
        d['first_seen'] = iso(row.get('first_seen'))
        d['last_seen'] = iso(row.get('last_seen')) if not d.get('live_ips') else iso(now_ts())
        d['notes'] = row.get('notes') or ''
        d['room'] = row.get('room') or ''
        d['photo'] = row.get('photo') or ''
        try:
            d['tags'] = json.loads(row.get('tags') or '[]')
        except Exception:
            d['tags'] = []
        d['known'] = bool(row.get('known', 1)) if row else True
        d['latency_ms'] = p.get('ms') if d.get('live_ips') else None
        d['ttl'] = ttl
        d['os_guess'] = os_guess(ttl, d.get('dev_class'))
        d['random_mac'] = bool(is_lam(mac))
        d['blocked'] = d.get('ip') in blocked
        last_ip = row.get('last_ip')
        if d.get('mismatch_ip'):
            d['pending_migration_ip'] = d['mismatch_ip']
        elif last_ip and last_ip != d.get('ip'):
            d['pending_migration_ip'] = last_ip
            if not d.get('live_ips'):
                d['mismatch_ip'] = last_ip
                d['live_ips'] = [last_ip]
        elif d.get('static') and (not d.get('live_ips') or d.get('ip') not in d.get('live_ips')):
            # Buscar en el historial de eventos la última IP conocida distinta de la asignada
            p_evs = [p for p in prev_ips_map.get(mac, []) if p and p != d.get('ip')]
            if p_evs:
                last_hist_ip = p_evs[-1]
                d['pending_migration_ip'] = last_hist_ip
                if not d.get('mismatch_ip'):
                    d['mismatch_ip'] = last_hist_ip
                if not d.get('live_ips'):
                    d['live_ips'] = [last_hist_ip]
        for l in d.get('web_links') or []:
            detected_urls.add(l['url'])
            sr = svc_rows.get(l['url']) or {}
            u = upt.get(l['url'])
            l['status'] = 'up' if sr.get('up', 1) else 'down'
            l['latency_ms'] = sr.get('latency_ms')
            l['uptime_24h'] = round(u['avg_up'] * 100, 1) if u and u['n'] else None
            l['history'] = (hist.get(l['url']) or [])[-40:]
            l['first_seen'] = iso(sr.get('first_seen'))

    # Enriquecer lista de fijadas con fecha y hora si falta
    so = state.get('static_order_summary') or {}
    for it in so.get('list', []):
        if not it.get('assigned_at') or it.get('assigned_at') == '':
            row = devs.get(norm_mac(it.get('mac'))) or {}
            it['assigned_at'] = iso(row.get('first_seen')) or iso(now_ts())

    # Dispositivos recordados en panel.db que estén desconectados (sin lease activo ni ARP)
    existing_macs = {norm_mac(d.get('mac')) for d in state.get('devices', []) if d.get('mac')}
    predict_fn = D.get('predict_device_info') or (lambda h, m, x: ('Dispositivo', 'Desconocido', '📱', 'other'))
    for row_mac, row in devs.items():
        if not row_mac or row_mac in existing_macs or row_mac == '00:00:00:00:00:00':
            continue
        h = row.get('hostname') or '(Sin nombre)'
        dev_class, dev_vendor, dev_icon, dev_cat = predict_fn(h, row_mac, None)
        try:
            row_tags = json.loads(row.get('tags') or '[]')
        except Exception:
            row_tags = []
        state.setdefault('devices', []).append({
            'hostname': h,
            'mac': row_mac,
            'ip': row.get('last_ip') or '',
            'static': False,
            'expires': '',
            'expired': False,
            'live_ips': [],
            'mismatch_ip': None,
            'router_node': 'Desconectado',
            'router_tooltip': 'Dispositivo guardado en historial (actualmente desconectado)',
            'router_type': 'offline',
            'conn_medium': 'offline',
            'conn_medium_label': 'Desconectado',
            'dev_class': dev_class,
            'dev_vendor': dev_vendor,
            'dev_icon': dev_icon,
            'dev_cat': dev_cat,
            'first_seen': iso(row.get('first_seen')),
            'last_seen': iso(row.get('last_seen')),
            'notes': row.get('notes') or '',
            'room': row.get('room') or '',
            'photo': row.get('photo') or '',
            'tags': row_tags,
            'known': bool(row.get('known', 1)),
            'watched': row_mac in watched_set,
            'latency_ms': None,
            'ttl': row.get('ttl'),
            'os_guess': os_guess(row.get('ttl'), dev_class),
            'random_mac': bool(is_lam(row_mac)),
            'blocked': False,
            'web_links': [],
            'open_ports': []
        })

    # Servicios recordados que ya no se detectan → caídos
    dev_by_mac = {norm_mac(d.get('mac')): d for d in state.get('devices', [])}
    down = []
    for url, sr in svc_rows.items():
        if url in detected_urls:
            continue
        if sr.get('up') and (sr.get('fail_count') or 0) < SERVICE_DOWN_THRESHOLD:
            continue
        dev = dev_by_mac.get(sr.get('mac')) or {}
        u = upt.get(url)
        down.append({
            'url': url, 'label': sr.get('label'), 'port': sr.get('port'), 'ip': sr.get('ip'), 'mac': sr.get('mac'),
            'hostname': dev.get('hostname') or (devs.get(sr.get('mac')) or {}).get('hostname') or sr.get('ip'),
            'dev_icon': dev.get('dev_icon') or '💻', 'last_seen_up': iso(sr.get('last_seen_up')),
            'uptime_24h': round(u['avg_up'] * 100, 1) if u and u['n'] else None,
            'history': (hist.get(url) or [])[-40:], 'status': 'down',
            'custom_name': (state.get('custom_service_names') or {}).get(url),
        })
    state['down_services'] = down
    state['monitor'] = {'last_run': iso(_MONITOR_STATE['last_run']), 'interval': MONITOR_INTERVAL,
                        'error': _MONITOR_STATE['last_error'], 'cycles': _MONITOR_STATE['cycles']}
    return state


# =====================================================================
#  AdGuard Home API (estadísticas DNS y bloqueo de clientes)
# =====================================================================
_AG_SESSION = {'ts': 0, 'op': None, 'url': '', 'key': ''}
_TOPO_TELEMETRY_CACHE = {'ts': 0, 'payload': None}


def ag_opener(force_new=False):
    cfg = D['load_config']()
    url = (cfg.get('adguard_url') or '').rstrip('/')
    user = (cfg.get('adguard_user') or '').strip()
    pwd = (cfg.get('adguard_pass') or '').strip()
    if not url or not user or not pwd:
        raise RuntimeError('Credenciales de AdGuard Home no configuradas (⚙️ Configuraciones).')
    key = f'{url}|{user}|{pwd}'
    if not force_new and _AG_SESSION['op'] is not None and _AG_SESSION['key'] == key and (time.time() - _AG_SESSION['ts'] < 600):
        return _AG_SESSION['op'], url
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(f'{url}/control/login', data=json.dumps({'name': user, 'password': pwd}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    op.open(req, timeout=5).read()
    _AG_SESSION.update({'ts': time.time(), 'op': op, 'url': url, 'key': key})
    return op, url


def ag_get(path):
    try:
        op, url = ag_opener()
        with op.open(f'{url}{path}', timeout=6) as r:
            return json.loads(r.read().decode('utf-8') or '{}')
    except Exception:
        op, url = ag_opener(force_new=True)
        with op.open(f'{url}{path}', timeout=6) as r:
            return json.loads(r.read().decode('utf-8') or '{}')


def ag_post(path, body):
    op, url = ag_opener()
    req = urllib.request.Request(f'{url}{path}', data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    with op.open(req, timeout=8) as r:
        return r.read().decode('utf-8')


_BLOCK_CACHE = {'ts': 0, 'list': []}


def get_blocked_clients(silent=False):
    if time.time() - _BLOCK_CACHE['ts'] < 30:
        return _BLOCK_CACHE['list']
    try:
        data = ag_get('/control/access/list')
        _BLOCK_CACHE['list'] = data.get('disallowed_clients') or []
    except Exception:
        if not silent:
            raise
    _BLOCK_CACHE['ts'] = time.time()
    return _BLOCK_CACHE['list']


def set_client_blocked(ip, block):
    data = ag_get('/control/access/list')
    dis = list(data.get('disallowed_clients') or [])
    if block and ip not in dis:
        dis.append(ip)
    if not block:
        dis = [x for x in dis if x != ip]
    body = {'allowed_clients': data.get('allowed_clients') or [], 'disallowed_clients': dis,
            'blocked_hosts': data.get('blocked_hosts') or []}
    ag_post('/control/access/set', body)
    _BLOCK_CACHE['ts'] = 0


def dns_stats_for(ip, limit=500):
    data = ag_get(f'/control/querylog?search={urllib.parse.quote(ip)}&limit={limit}&response_status=all')
    entries = [e for e in (data.get('data') or []) if e.get('client') == ip]
    domains = Counter()
    blocked = Counter()
    for e in entries:
        host = ((e.get('question') or {}).get('name') or '').rstrip('.')
        if not host:
            continue
        domains[host] += 1
        reason = e.get('reason') or ''
        if reason.startswith('Filtered') or reason in ('FilteredBlackList', 'FilteredBlockedService', 'FilteredParental', 'FilteredSafeBrowsing'):
            blocked[host] += 1
    whitelisted = {}
    custom_blocked = {}
    try:
        filt = ag_get('/control/filtering/status')
        for r in filt.get('user_rules') or []:
            if r.startswith('@@||'):
                rest = r[4:]
                d_part = rest.split('^')[0].strip().lower()
                is_global = '$client=' not in r
                is_this_client = bool(ip and (f"$client='{ip}'" in r or f"$client={ip}" in r))
                if is_global or is_this_client:
                    whitelisted[d_part] = {
                        'rule': r,
                        'mode': 'global' if is_global else 'client'
                    }
            elif r.startswith('||'):
                rest = r[2:]
                d_part = rest.split('^')[0].strip().lower()
                is_global = '$client=' not in r
                is_this_client = bool(ip and (f"$client='{ip}'" in r or f"$client={ip}" in r))
                if is_global or is_this_client:
                    custom_blocked[d_part] = {
                        'rule': r,
                        'mode': 'global' if is_global else 'client'
                    }
    except Exception:
        pass

    return {
        'total': len(entries),
        'blocked_total': sum(blocked.values()),
        'top_domains': domains.most_common(15),
        'top_blocked': blocked.most_common(10),
        'whitelisted': whitelisted,
        'custom_blocked': custom_blocked,
        'oldest': entries[-1].get('time') if entries else None,
    }


# =====================================================================
#  DHCP: rango del pool
# =====================================================================
def dhcp_range():
    try:
        res = D['run_sudo'](['cat', D['YAML_PATH']])
        txt = res.stdout if res.returncode == 0 else ''
        m = re.search(r'dhcpv4:(.*?)(?:dhcpv6:|\n\S)', txt, re.DOTALL)
        block = m.group(1) if m else txt
        rs = re.search(r'range_start:\s*([\d.]+)', block)
        re_ = re.search(r'range_end:\s*([\d.]+)', block)
        gw = re.search(r'gateway_ip:\s*([\d.]+)', block)
        return {'start': rs.group(1) if rs else '', 'end': re_.group(1) if re_ else '', 'gateway': gw.group(1) if gw else ''}
    except Exception:
        return {'start': '', 'end': '', 'gateway': ''}


def ip_last(ip):
    try:
        return int(ip.split('.')[-1])
    except Exception:
        return -1


# =====================================================================
#  ENDPOINTS
# =====================================================================
@bp.route('/api/monitor/status')
def api_monitor_status():
    return jsonify({'status': 'success', **_MONITOR_STATE, 'last_run_iso': iso(_MONITOR_STATE['last_run'])})


@bp.route('/api/topology/telemetry')
def api_topology_telemetry():
    now_f = time.time()
    if _TOPO_TELEMETRY_CACHE['payload'] is not None and (now_f - _TOPO_TELEMETRY_CACHE['ts'] < 2.5):
        return jsonify(_TOPO_TELEMETRY_CACHE['payload'])

    clients = {}
    for ip, p in list(_PING.items()):
        if p and p.get('alive'):
            clients[ip] = {
                'queries': 0,
                'blocked': 0,
                'last_domain': '',
                'last_blocked_domain': '',
                'latency_ms': p.get('ms')
            }

    source = 'ping_only'
    total_q = 0
    total_b = 0
    try:
        data = ag_get('/control/querylog?limit=320&response_status=all')
        entries = data.get('data') or []
        source = 'adguard_live'
        for e in entries:
            cip = (e.get('client') or '').strip()
            if not cip:
                continue
            c = clients.setdefault(cip, {
                'queries': 0,
                'blocked': 0,
                'last_domain': '',
                'last_blocked_domain': '',
                'latency_ms': (_PING.get(cip) or {}).get('ms')
            })
            c['queries'] += 1
            total_q += 1
            dom = ((e.get('question') or {}).get('name') or '').rstrip('.')
            if dom and not c['last_domain']:
                c['last_domain'] = dom
            reason = e.get('reason') or ''
            if reason.startswith('Filtered') or reason in ('FilteredBlackList', 'FilteredBlockedService', 'FilteredParental', 'FilteredSafeBrowsing'):
                c['blocked'] += 1
                total_b += 1
                if dom and not c['last_blocked_domain']:
                    c['last_blocked_domain'] = dom
    except Exception:
        pass

    payload = {
        'status': 'success',
        'source': source,
        'total_queries': total_q,
        'total_blocked': total_b,
        'clients': clients,
        'ts': now_ts()
    }
    _TOPO_TELEMETRY_CACHE['ts'] = now_f
    _TOPO_TELEMETRY_CACHE['payload'] = payload
    return jsonify(payload)


# ---------- Servicios ----------
@bp.route('/api/services/forget', methods=['POST'])
def api_services_forget():
    url = (request.json or {}).get('url') or ''
    db_exec('DELETE FROM services WHERE url=?', (url,))
    db_exec('DELETE FROM service_checks WHERE url=?', (url,))
    return jsonify({'status': 'success', 'message': 'Servicio olvidado. Si vuelve a aparecer, se detectará de nuevo.'})


# ---------- Alertas ----------
@bp.route('/api/alerts/config', methods=['GET', 'POST'])
def api_alerts_config():
    if request.method == 'GET':
        return jsonify({'status': 'success', 'alerts': get_alerts_cfg()})
    body = request.json or {}
    a = get_alerts_cfg()
    for k in DEFAULT_ALERTS:
        if k in body:
            a[k] = body[k]
    a['watched_macs'] = [norm_mac(m) for m in a.get('watched_macs') or [] if valid_mac(m)]
    cfg = D['load_config']()
    cfg['alerts'] = a
    D['save_config_raw'](cfg)
    return jsonify({'status': 'success', 'message': 'Configuración de alertas guardada.', 'alerts': a})


@bp.route('/api/device/<path:mac>/watch', methods=['POST'])
def api_device_watch_toggle(mac):
    mac = norm_mac(mac)
    if not valid_mac(mac):
        return jsonify({'status': 'error', 'message': 'MAC no válida'}), 400

    cfg = D['load_config']()
    alerts = cfg.get('alerts') or {}
    for k, v in DEFAULT_ALERTS.items():
        if k not in alerts:
            alerts[k] = v

    watched = set(norm_mac(m) for m in alerts.get('watched_macs', []))

    req_data = request.get_json(silent=True) or {}
    if 'watched' in req_data:
        should_watch = bool(req_data['watched'])
    else:
        should_watch = mac not in watched

    if should_watch:
        watched.add(mac)
    else:
        watched.discard(mac)

    alerts['watched_macs'] = sorted(list(watched))
    alerts['enabled'] = True
    if alerts.get('smtp_user') and alerts.get('smtp_pass') and alerts.get('smtp_to'):
        alerts['email_enabled'] = True

    cfg['alerts'] = alerts
    D['save_config_raw'](cfg)

    smtp_ok = bool(alerts.get('smtp_user') and alerts.get('smtp_pass') and alerts.get('smtp_to'))
    smtp_to = alerts.get('smtp_to', '')

    return jsonify({
        'status': 'success',
        'mac': mac,
        'watched': should_watch,
        'watched_count': len(watched),
        'smtp_configured': smtp_ok,
        'smtp_to': smtp_to,
        'message': f'Notificación de conexión por correo {"activada" if should_watch else "desactivada"}.'
    })


@bp.route('/api/alerts/test', methods=['POST'])
def api_alerts_test():
    body = request.json or {}
    a = get_alerts_cfg()
    a.update({k: v for k, v in body.items() if k in DEFAULT_ALERTS})
    has_channel = bool(
        a.get('ntfy_url') or
        (a.get('telegram_token') and a.get('telegram_chat_id')) or
        a.get('webhook_url') or
        (a.get('smtp_user') and a.get('smtp_pass') and a.get('smtp_to'))
    )
    if not has_channel:
        return jsonify({'status': 'error', 'message': 'No hay ningún canal configurado (ntfy, Telegram, webhook o correo SMTP/Gmail).'})
    test_title = '🔔 Prueba de alertas del Panel DHCP'
    test_msg = 'Si ves este mensaje, las notificaciones del Panel DHCP (incluyendo el correo electrónico) funcionan correctamente.'
    test_html = f"""<!DOCTYPE html>
<html><body style="background:#0f172a; color:#e2e8f0; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding:20px;">
  <div style="max-width:600px; margin:0 auto; background:#1e293b; padding:24px; border-radius:12px; border:1px solid #38bdf8; box-shadow:0 8px 24px rgba(0,0,0,0.4);">
    <h2 style="color:#38bdf8; margin-top:0;">🔔 Prueba de Alertas por Correo</h2>
    <p style="font-size:1rem; line-height:1.6; color:#f8fafc;">{test_msg}</p>
    <div style="background:#0f172a; border-radius:8px; padding:12px; margin-top:16px; font-size:0.85rem; color:#94a3b8;">
      Servidor SMTP: <strong>{a.get('smtp_host', 'smtp.gmail.com')}:{a.get('smtp_port', 587)}</strong><br>
      Remitente: <strong>{a.get('smtp_user', '')}</strong><br>
      Destinatario: <strong>{a.get('smtp_to', '')}</strong><br>
      Fecha/Hora: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
    </div>
    <p style="font-size:0.8rem; color:#64748b; margin-top:20px; border-top:1px solid #334155; padding-top:10px;">
      Panel DHCP &copy; Raspberry Pi 4 · {datetime.now().year}
    </p>
  </div>
</body></html>"""
    res = send_alert(test_title, test_msg, 'test', force=True, cfg_override=a, email_html=test_html)
    ok = [r[0] for r in res if r[1]]
    ko = [f'{r[0]}: {r[2]}' for r in res if not r[1]]
    msg = (f'Enviado correctamente por: {", ".join(ok)}. ' if ok else '') + (f'Fallos → {" | ".join(ko)}' if ko else '')
    return jsonify({'status': 'success' if ok else 'error', 'message': msg or 'Sin resultados.'})


@bp.route('/api/alerts/test-smtp', methods=['POST'])
def api_alerts_test_smtp():
    body = request.json or {}
    a = get_alerts_cfg()
    user = (body.get('smtp_user') or a.get('smtp_user') or '').strip()
    password = (body.get('smtp_pass') or a.get('smtp_pass') or '').strip()
    to_addr = (body.get('smtp_to') or a.get('smtp_to') or '').strip()
    host = (body.get('smtp_host') or a.get('smtp_host') or 'smtp.gmail.com').strip()
    try:
        port = int(body.get('smtp_port') or a.get('smtp_port') or 587)
    except Exception:
        port = 587
    use_tls = bool(body.get('smtp_tls', a.get('smtp_tls', True)))

    if not user or not password or not to_addr:
        return jsonify({'status': 'error', 'message': 'Faltan credenciales: se requiere correo remitente (usuario), contraseña de aplicación y destinatario.'})

    test_title = '[Panel DHCP] 📧 Prueba de Configuración SMTP / Correo'
    test_msg = f'¡Enhorabuena! El envío de correos mediante el servidor SMTP ({host}:{port}) está configurado correctamente y funcionando a la perfección.'
    test_html = f"""<!DOCTYPE html>
<html><body style="background:#0f172a; color:#e2e8f0; font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding:20px;">
  <div style="max-width:600px; margin:0 auto; background:#1e293b; padding:24px; border-radius:12px; border:1px solid #10b981; box-shadow:0 8px 24px rgba(0,0,0,0.4);">
    <h2 style="color:#10b981; margin-top:0;">✅ Prueba de Correo SMTP Exitosa</h2>
    <p style="font-size:1rem; line-height:1.6; color:#f8fafc;">{test_msg}</p>
    <div style="background:#0f172a; border-radius:8px; padding:12px; margin-top:16px; font-size:0.85rem; color:#94a3b8;">
      Servidor SMTP: <strong>{host}:{port}</strong><br>
      Remitente: <strong>{user}</strong><br>
      Destinatario: <strong>{to_addr}</strong><br>
      Seguridad TLS: <strong>{'Activada (STARTTLS)' if use_tls else 'Desactivada'}</strong><br>
      Fecha/Hora: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong>
    </div>
    <p style="font-size:0.8rem; color:#64748b; margin-top:20px; border-top:1px solid #334155; padding-top:10px;">
      Panel DHCP &copy; Raspberry Pi 4 · {datetime.now().year}
    </p>
  </div>
</body></html>"""

    ok, err = send_smtp_email(
        host=host,
        port=port,
        user=user,
        password=password,
        to_addr=to_addr,
        subject=test_title,
        body_text=test_msg,
        body_html=test_html,
        use_tls=use_tls
    )
    if ok:
        db_exec('INSERT INTO events_log (ts, kind, title, message, sent) VALUES (?,?,?,?,?)',
                (now_ts(), 'test', test_title, f'Correo de prueba enviado a {to_addr}', 1))
        return jsonify({'status': 'success', 'message': f'Correo de prueba enviado correctamente a {to_addr}.'})
    else:
        return jsonify({'status': 'error', 'message': f'Error al enviar correo SMTP: {err}'})


@bp.route('/api/events')
def api_events():
    limit = min(int(request.args.get('limit', 100)), 500)
    rows = db_query('SELECT * FROM events_log ORDER BY ts DESC LIMIT ?', (limit,))
    for r in rows:
        r['time'] = iso(r['ts'])
        r['detail'] = r.get('message') or ''
    return jsonify({'status': 'success', 'events': rows})


# ---------- Ficha de dispositivo ----------

@bp.route('/api/device/<mac>/export-sheet')
def api_device_export_sheet(mac):
    mac = norm_mac(mac)
    if not valid_mac(mac):
        return jsonify({'status': 'error', 'message': 'MAC no válida'}), 400

    dev_state = None
    try:
        state = D['build_state']()
        dev_state = next((d for d in state.get('devices', []) if norm_mac(d.get('mac')) == mac), None)
    except Exception:
        pass

    row = db_query('SELECT notes, room, tags, known, photo FROM devices WHERE mac=?', (mac,))
    meta = row[0] if row else {}
    photo_b64 = meta.get('photo') or get_device_photo_data_url(mac)

    hostname = (dev_state.get('hostname') if dev_state else '') or mac
    ip = (dev_state.get('ip') if dev_state else '') or ''
    clean_mac = mac.replace(':', '-').lower()
    safe_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', hostname)

    sheet_data = {
        'app': 'adguard-dhcp-panel',
        'type': 'device_sheet',
        'format_version': 1,
        'exported_at': datetime.now().isoformat(),
        'device': {
            'mac': mac,
            'ip': ip,
            'hostname': hostname,
            'vendor': dev_state.get('dev_vendor') if dev_state else '',
            'class': dev_state.get('dev_class') if dev_state else '',
            'medium': dev_state.get('conn_medium_label') if dev_state else '',
            'router_node': dev_state.get('router_node') if dev_state else '',
            'room': meta.get('room') or '',
            'tags': json.loads(meta.get('tags') or '[]'),
            'notes': meta.get('notes') or '',
            'photo': photo_b64 or '',
            'static': bool(dev_state.get('static')) if dev_state else False
        }
    }

    fmt = request.args.get('format', 'zip').lower()
    if fmt == 'json':
        fname = f"ficha-{safe_name}-{clean_mac}.json"
        return Response(json.dumps(sheet_data, indent=2, ensure_ascii=False), mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename="{fname}"'})

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('ficha.json', json.dumps(sheet_data, indent=2, ensure_ascii=False).encode('utf-8'))
        if photo_b64 and ',' in photo_b64:
            try:
                header, b64 = photo_b64.split(',', 1)
                ext = 'webp' if 'webp' in header else ('jpeg' if 'jpeg' in header or 'jpg' in header else 'png')
                raw_img = base64.b64decode(b64)
                zf.writestr(f"images/{clean_mac}.{ext}", raw_img)
            except Exception as e:
                print(f"Error empaquetando imagen en ficha zip para {mac}: {e}")

    buf.seek(0)
    fname = f"ficha-{safe_name}-{clean_mac}.zip"
    return Response(buf.getvalue(), mimetype='application/zip',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})


@bp.route('/api/device/import-sheet', methods=['POST'])
def api_device_import_sheet():
    try:
        f = request.files.get('file')
        content_type = request.content_type or ''
        sheet_data = None
        extracted_photo = None

        if f:
            filename = (f.filename or '').lower()
            if filename.endswith('.zip'):
                content = f.read()
                with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
                    json_name = next((n for n in zf.namelist() if n == 'ficha.json' or n.endswith('.json')), None)
                    if not json_name:
                        return jsonify({'status': 'error', 'message': 'El archivo comprimido .zip no contiene ficha.json.'}), 400
                    sheet_data = json.loads(zf.read(json_name).decode('utf-8'))
                    for name in zf.namelist():
                        if name.startswith('images/') or name.startswith('photos/'):
                            base_name = os.path.basename(name)
                            if not base_name: continue
                            raw_img = zf.read(name)
                            ext = os.path.splitext(base_name)[1].lstrip('.').lower()
                            mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
                            extracted_photo = f"data:{mime};base64,{base64.b64encode(raw_img).decode('ascii')}"
                            if PHOTOS_DIR:
                                with open(os.path.join(PHOTOS_DIR, base_name), 'wb') as img_out:
                                    img_out.write(raw_img)
                            break
            else:
                sheet_data = json.loads(f.read().decode('utf-8'))
        else:
            sheet_data = request.get_json(force=True)

        if not isinstance(sheet_data, dict) or sheet_data.get('app') != 'adguard-dhcp-panel':
            return jsonify({'status': 'error', 'message': 'Archivo de ficha técnica no válido.'}), 400

        dev = sheet_data.get('device') or {}
        mac = norm_mac(dev.get('mac') or '')
        if not valid_mac(mac):
            return jsonify({'status': 'error', 'message': f'MAC inválida en la ficha: {mac}'}), 400

        photo_to_save = extracted_photo or dev.get('photo')

        if not db_query('SELECT mac FROM devices WHERE mac=?', (mac,)):
            db_exec('INSERT INTO devices (mac, first_seen, known) VALUES (?,?,1)', (mac, now_ts()))

        db_exec('''
            UPDATE devices 
            SET notes=?, room=?, tags=?, known=1, photo=COALESCE(?, photo) 
            WHERE mac=?
        ''', (
            dev.get('notes') or '',
            dev.get('room') or '',
            json.dumps(dev.get('tags') or []),
            photo_to_save,
            mac
        ))

        if photo_to_save:
            save_device_photo_file(mac, photo_to_save)

        return jsonify({
            'status': 'success',
            'message': f'Ficha técnica y foto de {dev.get("hostname") or mac} importadas correctamente.',
            'mac': mac
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@bp.route('/api/device/<mac>')
def api_device_detail(mac):
    mac = norm_mac(mac)
    row = (db_query('SELECT * FROM devices WHERE mac=?', (mac,)) or [{}])[0]
    events = db_query('SELECT ts, ip, event FROM device_events WHERE mac=? ORDER BY ts DESC LIMIT 200', (mac,))
    for e in events:
        e['time'] = iso(e['ts'])
    services = db_query('SELECT * FROM services WHERE mac=?', (mac,))
    for s in services:
        s['first_seen'] = iso(s['first_seen'])
        s['last_seen_up'] = iso(s['last_seen_up'])
    # % de tiempo en línea en los últimos 7 días a partir de los eventos
    online_pct = presence_pct(mac, 7 * 86400)
    dns = None
    dns_error = ''
    ip = request.args.get('ip') or (row.get('last_ip') if row else '')
    if ip and valid_ipv4(ip):
        try:
            dns = dns_stats_for(ip)
        except Exception as e:
            dns_error = str(e)
    return jsonify({'status': 'success', 'device': {
        'mac': mac, 'first_seen': iso(row.get('first_seen')), 'last_seen': iso(row.get('last_seen')),
        'notes': row.get('notes') or '', 'room': row.get('room') or '',
        'tags': json.loads(row.get('tags') or '[]') if row else [], 'known': bool(row.get('known', 1)) if row else True,
        'latency_ms': row.get('latency_ms'), 'ttl': row.get('ttl'),
    }, 'events': events, 'services': services, 'online_pct_7d': online_pct, 'dns': dns, 'dns_error': dns_error})


def presence_pct(mac, window):
    t_end = now_ts()
    t_start = t_end - window
    evs = db_query('SELECT ts, event FROM device_events WHERE mac=? ORDER BY ts', (mac,))
    if not evs:
        return None
    state = None
    for e in evs:
        if e['ts'] <= t_start:
            state = e['event'] in ('online', 'new')
    first_ts = max(t_start, evs[0]['ts'])
    online_sec = 0
    cur_t = first_ts
    for e in evs:
        if e['ts'] <= first_ts:
            continue
        if state:
            online_sec += e['ts'] - cur_t
        state = e['event'] in ('online', 'new')
        cur_t = e['ts']
    if state:
        online_sec += t_end - cur_t
    total = t_end - first_ts
    return round(online_sec * 100 / total, 1) if total > 0 else None


@bp.route('/api/device/<mac>/meta', methods=['POST'])
def api_device_meta(mac):
    mac = norm_mac(mac)
    if not valid_mac(mac):
        return jsonify({'status': 'error', 'message': 'MAC no válida.'}), 400
    body = request.json or {}
    if not db_query('SELECT mac FROM devices WHERE mac=?', (mac,)):
        db_exec('INSERT INTO devices (mac, first_seen, known) VALUES (?,?,1)', (mac, now_ts()))
    fields, vals = [], []
    if 'notes' in body:
        fields.append('notes=?'); vals.append(str(body['notes'])[:2000])
    if 'room' in body:
        fields.append('room=?'); vals.append(str(body['room'])[:60])
    if 'photo' in body:
        fields.append('photo=?'); vals.append(str(body['photo'])[:2500000])
        save_device_photo_file(mac, body['photo'])
    if 'tags' in body and isinstance(body['tags'], list):
        fields.append('tags=?'); vals.append(json.dumps([str(t)[:30] for t in body['tags']][:15]))
    if 'known' in body:
        fields.append('known=?'); vals.append(1 if body['known'] else 0)
    if fields:
        db_exec(f'UPDATE devices SET {", ".join(fields)} WHERE mac=?', (*vals, mac))
    return jsonify({'status': 'success', 'message': 'Ficha del dispositivo guardada.'})


# ---------- Línea temporal ----------
@bp.route('/api/timeline')
def api_timeline():
    hours = max(1, min(int(request.args.get('hours', 24)), 24 * 30))
    t_end = now_ts()
    t_start = t_end - hours * 3600
    devs = db_query('SELECT mac, hostname, last_ip, online, first_seen FROM devices')
    evs = db_query('SELECT ts, mac, event FROM device_events ORDER BY ts')
    by_mac = {}
    for e in evs:
        by_mac.setdefault(e['mac'], []).append(e)
    out = []
    for d in devs:
        lst = by_mac.get(d['mac'], [])
        state = None
        for e in lst:
            if e['ts'] <= t_start:
                state = e['event'] in ('online', 'new')
        segs = []
        cur = t_start if state else None
        for e in lst:
            if e['ts'] <= t_start:
                continue
            is_on = e['event'] in ('online', 'new')
            if is_on and cur is None:
                cur = e['ts']
            elif not is_on and cur is not None:
                segs.append([cur, e['ts']])
                cur = None
        if cur is not None:
            segs.append([cur, t_end])
        changes = sum(1 for e in lst if e['ts'] > t_start and e['event'] in ('online', 'offline'))
        out.append({'mac': d['mac'], 'hostname': d['hostname'], 'ip': d['last_ip'], 'online': bool(d['online']),
                    'segments': segs, 'changes': changes})
    return jsonify({'status': 'success', 'start': t_start, 'end': t_end, 'devices': out,
                    'history_since': iso((db_query('SELECT MIN(ts) AS t FROM device_events') or [{}])[0].get('t'))})


# ---------- Mapa de IPs ----------
@bp.route('/api/ipmap')
def api_ipmap():
    state = D['build_state'](False)
    rng = dhcp_range()
    rs, re_ = ip_last(rng['start']), ip_last(rng['end'])
    cells = {i: {'n': i, 'ip': f'192.168.1.{i}', 'status': 'free', 'devices': []} for i in range(1, 255)}
    for d in state.get('devices', []):
        ips = set([d.get('ip')] + list(d.get('live_ips') or []))
        for ip in ips:
            if not ip or not ip.startswith('192.168.1.'):
                continue
            n = ip_last(ip)
            if n not in cells:
                continue
            cells[n]['devices'].append({'hostname': d.get('hostname'), 'mac': d.get('mac'), 'static': d.get('static'),
                                        'online': bool(d.get('live_ips')), 'icon': d.get('dev_icon'),
                                        'lease_ip': d.get('ip'), 'manual': bool(d.get('manual_static'))})
    for n, c in cells.items():
        c['in_pool'] = rs > 0 and re_ > 0 and rs <= n <= re_
        macs = {x['mac'] for x in c['devices']}
        if len(macs) > 1:
            c['status'] = 'conflict'
        elif c['devices']:
            x = c['devices'][0]
            if x['manual']:
                c['status'] = 'manual'
            elif x['static']:
                c['status'] = 'static_on' if x['online'] else 'static_off'
            else:
                c['status'] = 'dynamic_on' if x['online'] else 'dynamic_off'
        if c['ip'] == rng.get('gateway') or n == 1:
            c['gateway'] = True
    return jsonify({'status': 'success', 'range': rng, 'cells': list(cells.values())})


# ---------- Diagnóstico ----------
@bp.route('/api/diagnostics')
def api_diagnostics():
    state = D['build_state'](False)
    devices = state.get('devices', [])
    rng = dhcp_range()
    rs, re_ = ip_last(rng['start']), ip_last(rng['end'])
    is_lam = D.get('is_locally_administered_mac') or (lambda m: False)
    issues = []

    def add(sev, cat, title, detail, mac=None, ip=None, fix=None):
        issues.append({'severity': sev, 'category': cat, 'title': title, 'detail': detail, 'mac': mac, 'ip': ip, 'fix': fix})

    # IP compartida por varias MAC (ARP)
    arp = D['get_arp_table']()
    ip_macs = {}
    for m, ips in arp.items():
        for ip in ips:
            ip_macs.setdefault(ip, set()).add(m)
    for ip, macs in ip_macs.items():
        if len(macs) > 1:
            add('critical', 'Conflicto', f'IP duplicada {ip}', f'Varias MAC responden en la misma IP: {", ".join(sorted(macs))}', ip=ip)

    # Varias concesiones para la misma MAC / misma IP en leases
    leases = D['read_leases']().get('leases', [])
    by_mac, by_ip = {}, {}
    for l in leases:
        m = norm_mac(l.get('mac'))
        if m == '00:00:00:00:00:00' or ':' in (l.get('ip') or '.'):
            continue
        by_mac.setdefault(m, set()).add(l.get('ip'))
        by_ip.setdefault(l.get('ip'), set()).add(m)
    for m, ips in by_mac.items():
        if len(ips) > 1:
            add('warning', 'Concesiones', 'Varias concesiones para un mismo dispositivo',
                f'{m} tiene concesiones en {", ".join(sorted(ips))}', mac=m, fix='Borra las sobrantes desde la tabla.')
    for ip, macs in by_ip.items():
        if len(macs) > 1:
            add('critical', 'Conflicto', f'IP {ip} asignada a varias MAC en AdGuard', ', '.join(sorted(macs)), ip=ip)

    for d in devices:
        ip, mac, host = d.get('ip'), d.get('mac'), d.get('hostname') or ''
        n = ip_last(ip or '')
        if d.get('static') and not d.get('manual_static') and rs > 0 and rs <= n <= re_:
            add('warning', 'DHCP', f'IP estática dentro del rango dinámico ({ip})',
                f'{host}: la IP {ip} está dentro del pool {rng["start"]}–{rng["end"]}. AdGuard podría ofrecerla a otro equipo.',
                mac=mac, ip=ip, fix='Asigna una IP fuera del rango dinámico (usa el 🗺️ Mapa de IPs).')
        if d.get('mismatch_ip'):
            add('warning', 'Desajuste', f'{host} usa una IP distinta a la asignada',
                f'Asignada {ip}, pero responde en {d.get("mismatch_ip")}. Puede que no haya renovado su concesión.',
                mac=mac, ip=ip, fix='Usa "⚡ Guardar + Forzar Reconexión AP" o reinicia el dispositivo.')
        if is_lam(mac) and d.get('static'):
            add('info', 'Privacidad', f'{host}: MAC aleatoria con IP fija',
                f'{mac} es una MAC privada/aleatoria; si el dispositivo la rota, la IP fija dejará de aplicarse.',
                mac=mac, ip=ip, fix='Desactiva "Dirección MAC privada" para esta red en el móvil.')
        if re.fullmatch(r'(\(sin nombre\)|192-168-1-\d+|android-[0-9a-f]+|esp_[0-9a-f]+|unknown.*|)', host.lower()):
            add('info', 'Identificación', f'Dispositivo sin nombre descriptivo ({ip})',
                f'"{host}" · {d.get("dev_vendor") or ""}', mac=mac, ip=ip, fix='Ponle un nombre con "Editar / Fijar".')
        if d.get('expired'):
            add('info', 'Concesiones', f'Concesión caducada: {host} ({ip})', 'Puede purgarse con "🧹 Purgar".', mac=mac, ip=ip)

    if state.get('ghost_count'):
        add('info', 'Concesiones', f'{state["ghost_count"]} entradas fantasma (00:00:00:00:00:00)', 'Pulsa "🧹 Purgar".')

    # Servicios caídos
    for s in db_query('SELECT * FROM services WHERE up=0'):
        add('warning', 'Servicios', f'Servicio caído: {s["label"]}', f'{s["url"]} · última vez activo: {iso(s["last_seen_up"]) or "nunca"}', mac=s['mac'], ip=s['ip'])

    # Monitor
    if _MONITOR_STATE['last_error']:
        add('warning', 'Panel', 'Error en el monitor en segundo plano', _MONITOR_STATE['last_error'])

    order = {'critical': 0, 'warning': 1, 'info': 2}
    issues.sort(key=lambda i: order.get(i['severity'], 3))
    counts = Counter(i['severity'] for i in issues)
    score = max(0, 100 - counts.get('critical', 0) * 20 - counts.get('warning', 0) * 6 - counts.get('info', 0) * 1)
    return jsonify({'status': 'success', 'issues': issues, 'counts': dict(counts), 'score': score, 'range': rng})


# ---------- Acciones ----------
@bp.route('/api/device/block', methods=['POST'])
def api_device_block():
    body = request.json or {}
    ip = (body.get('ip') or '').strip()
    block = bool(body.get('block'))
    if not valid_ipv4(ip):
        return jsonify({'status': 'error', 'message': 'IP no válida.'})
    if ip in ('192.168.1.249', '192.168.1.1', '127.0.0.1') and block:
        return jsonify({'status': 'error', 'message': 'No se puede bloquear el servidor ni el router principal.'})
    try:
        set_client_blocked(ip, block)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'AdGuard Home: {e}'})
    send_alert('⛔ Internet bloqueado' if block else '✅ Internet restaurado', f'Cliente {ip}', 'info')
    return jsonify({'status': 'success', 'message': (
        f'⛔ {ip} bloqueado en AdGuard Home: ya no podrá resolver DNS (sin navegación).'
        if block else f'✅ {ip} desbloqueado: vuelve a tener acceso a Internet.')})


@bp.route('/api/dns/whitelist', methods=['POST'])
def api_dns_whitelist():
    body = request.json or {}
    domain = (body.get('domain') or '').strip().lower().rstrip('.')
    ip = (body.get('ip') or '').strip()
    mode = body.get('mode', 'client')
    if not domain:
        return jsonify({'status': 'error', 'message': 'Dominio no proporcionado.'}), 400

    if mode == 'client' and ip:
        rule = f"@@||{domain}^$client='{ip}'"
        target_desc = f"para este dispositivo ({ip})"
    else:
        rule = f"@@||{domain}^"
        target_desc = "para toda la red"

    try:
        status = ag_get('/control/filtering/status')
        rules = list(status.get('user_rules') or [])
        if rule not in rules:
            rules.append(rule)
            ag_post('/control/filtering/set_rules', {'rules': rules})
            send_alert('🔓 Dominio desbloqueado', f"AdGuard Home: {domain} permitido {target_desc}.", 'info')
        return jsonify({
            'status': 'success',
            'message': f'✅ Dominio {domain} desbloqueado {target_desc}.',
            'domain': domain,
            'rule': rule,
            'mode': mode
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error en AdGuard Home: {e}'}), 500


@bp.route('/api/dns/unwhitelist', methods=['POST'])
def api_dns_unwhitelist():
    body = request.json or {}
    domain = (body.get('domain') or '').strip().lower().rstrip('.')
    ip = (body.get('ip') or '').strip()
    rule_to_remove = (body.get('rule') or '').strip()
    if not domain and not rule_to_remove:
        return jsonify({'status': 'error', 'message': 'Dominio no proporcionado.'}), 400

    try:
        status = ag_get('/control/filtering/status')
        rules = list(status.get('user_rules') or [])
        new_rules = []
        removed = 0
        for r in rules:
            if rule_to_remove and r == rule_to_remove:
                removed += 1
                continue
            if not rule_to_remove and domain:
                if r.startswith(f"@@||{domain}^"):
                    if ip:
                        if f"$client='{ip}'" in r or f"$client={ip}" in r or "$client=" not in r:
                            removed += 1
                            continue
                    else:
                        removed += 1
                        continue
            new_rules.append(r)

        if removed > 0:
            ag_post('/control/filtering/set_rules', {'rules': new_rules})
            send_alert('⛔ Excepción DNS eliminada', f"AdGuard Home: {domain} volverá a filtrarse normalmente.", 'info')
            return jsonify({
                'status': 'success',
                'message': f'Excepción eliminada para {domain}. El dominio volverá a filtrarse.',
                'domain': domain
            })
        else:
            return jsonify({'status': 'success', 'message': f'No se encontró ninguna regla activa para {domain}.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error en AdGuard Home: {e}'}), 500


@bp.route('/api/dns/block', methods=['POST'])
def api_dns_block():
    body = request.json or {}
    domain = (body.get('domain') or '').strip().lower().rstrip('.')
    ip = (body.get('ip') or '').strip()
    mode = body.get('mode', 'client')
    if not domain:
        return jsonify({'status': 'error', 'message': 'Dominio no proporcionado.'}), 400

    if mode == 'client' and ip:
        rule = f"||{domain}^$client='{ip}'"
        target_desc = f"para este dispositivo ({ip})"
    else:
        rule = f"||{domain}^"
        target_desc = "para toda la red"

    try:
        status = ag_get('/control/filtering/status')
        rules = list(status.get('user_rules') or [])
        # Quitar posible regla de excepción previa que anularía el bloqueo
        rules = [r for r in rules if not (r.startswith(f"@@||{domain}^") and (mode != 'client' or f"$client='{ip}'" in r or '$client=' not in r))]
        if rule not in rules:
            rules.append(rule)
            ag_post('/control/filtering/set_rules', {'rules': rules})
            send_alert('🚫 Dominio bloqueado', f"AdGuard Home: {domain} bloqueado {target_desc}.", 'info')
        return jsonify({
            'status': 'success',
            'message': f'🚫 Dominio {domain} bloqueado {target_desc}.',
            'domain': domain,
            'rule': rule,
            'mode': mode
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error en AdGuard Home: {e}'}), 500


@bp.route('/api/dns/unblock', methods=['POST'])
def api_dns_unblock():
    body = request.json or {}
    domain = (body.get('domain') or '').strip().lower().rstrip('.')
    ip = (body.get('ip') or '').strip()
    rule_to_remove = (body.get('rule') or '').strip()
    if not domain and not rule_to_remove:
        return jsonify({'status': 'error', 'message': 'Dominio no proporcionado.'}), 400

    try:
        status = ag_get('/control/filtering/status')
        rules = list(status.get('user_rules') or [])
        new_rules = []
        removed = 0
        for r in rules:
            if rule_to_remove and r == rule_to_remove:
                removed += 1
                continue
            if not rule_to_remove and domain:
                if r.startswith(f"||{domain}^"):
                    if ip:
                        if f"$client='{ip}'" in r or f"$client={ip}" in r or "$client=" not in r:
                            removed += 1
                            continue
                    else:
                        removed += 1
                        continue
            new_rules.append(r)

        if removed > 0:
            ag_post('/control/filtering/set_rules', {'rules': new_rules})
            send_alert('✅ Bloqueo DNS eliminado', f"AdGuard Home: Regla de bloqueo eliminada para {domain}.", 'info')
            return jsonify({
                'status': 'success',
                'message': f'Bloqueo eliminado para {domain}.',
                'domain': domain
            })
        else:
            return jsonify({'status': 'success', 'message': f'No se encontró regla de bloqueo para {domain}.'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error en AdGuard Home: {e}'}), 500


@bp.route('/api/wol', methods=['POST'])
def api_wol():
    mac = norm_mac((request.json or {}).get('mac'))
    if not valid_mac(mac):
        return jsonify({'status': 'error', 'message': 'MAC no válida.'})
    payload = b'\xff' * 6 + bytes.fromhex(mac.replace(':', '')) * 16
    sent = 0
    for addr in ('255.255.255.255', '192.168.1.255'):
        for port in (9, 7):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(payload, (addr, port))
                s.close()
                sent += 1
            except Exception:
                pass
    if not sent:
        return jsonify({'status': 'error', 'message': 'No se pudo enviar el paquete mágico.'})
    return jsonify({'status': 'success', 'message': f'⚡ Paquete Wake-on-LAN enviado a {mac}. Si el equipo tiene WoL activado en BIOS/red, arrancará en unos segundos.'})


COMMON_PORT_NAMES = {
    20: 'FTP-data', 21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS', 67: 'DHCP', 80: 'HTTP', 81: 'HTTP-alt',
    110: 'POP3', 111: 'RPC', 123: 'NTP', 135: 'MS-RPC', 139: 'NetBIOS', 143: 'IMAP', 161: 'SNMP', 443: 'HTTPS',
    445: 'SMB', 548: 'AFP', 554: 'RTSP', 631: 'IPP (impresora)', 853: 'DNS-over-TLS', 993: 'IMAPS', 995: 'POP3S',
    1080: 'SOCKS', 1194: 'OpenVPN', 1433: 'MSSQL', 1883: 'MQTT', 1900: 'UPnP', 1984: 'go2rtc', 2283: 'Immich',
    3000: 'Grafana/Node', 3306: 'MySQL', 3389: 'RDP', 4357: 'HA Observer', 5000: 'HTTP-alt', 5001: 'HTTP-alt',
    5353: 'mDNS', 5432: 'PostgreSQL', 5900: 'VNC', 6052: 'ESPHome', 6379: 'Redis', 6881: 'BitTorrent',
    8006: 'Proxmox', 8080: 'HTTP-proxy', 8086: 'InfluxDB', 8096: 'Jellyfin', 8123: 'Home Assistant', 8443: 'HTTPS-alt',
    8883: 'MQTT-TLS', 8888: 'HTTP-alt', 9000: 'Portainer', 9100: 'Impresora RAW', 9443: 'Portainer-TLS',
    32400: 'Plex', 51820: 'WireGuard', 62078: 'iPhone sync',
}


def _scan_port(ip, port, timeout):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        if s.connect_ex((ip, port)) == 0:
            banner = ''
            try:
                s.settimeout(0.6)
                data = s.recv(120)
                banner = data.decode('utf-8', 'ignore').strip().splitlines()[0][:80] if data else ''
            except Exception:
                pass
            return port, banner
    except Exception:
        pass
    finally:
        s.close()
    return None


def _run_scan(job_id, ip, ports, timeout):
    job = _SCAN_JOBS[job_id]
    with ThreadPoolExecutor(max_workers=300) as pool:
        futs = [pool.submit(_scan_port, ip, p, timeout) for p in ports]
        for i, f in enumerate(futs):
            if job.get('cancel'):
                break
            r = f.result()
            if r:
                job['open'].append({'port': r[0], 'service': COMMON_PORT_NAMES.get(r[0], ''), 'banner': r[1]})
            job['done'] = i + 1
    job['open'].sort(key=lambda x: x['port'])
    job['finished'] = True
    job['elapsed'] = round(time.time() - job['started'], 1)


@bp.route('/api/portscan', methods=['POST'])
def api_portscan_start():
    body = request.json or {}
    ip = (body.get('ip') or '').strip()
    mode = body.get('mode', 'common')
    if not valid_ipv4(ip) or not ip.startswith('192.168.'):
        return jsonify({'status': 'error', 'message': 'Solo se permiten IPs de la red local.'})
    if mode == 'full':
        ports, timeout = list(range(1, 65536)), 0.35
    elif mode == 'top':
        ports, timeout = sorted(set(list(range(1, 1025)) + list(COMMON_PORT_NAMES.keys()))), 0.5
    else:
        ports, timeout = sorted(COMMON_PORT_NAMES.keys()), 0.6
    for jid, j in list(_SCAN_JOBS.items()):
        if j.get('finished') and time.time() - j['started'] > 1800:
            _SCAN_JOBS.pop(jid, None)
    job_id = secrets.token_hex(6)
    _SCAN_JOBS[job_id] = {'ip': ip, 'mode': mode, 'total': len(ports), 'done': 0, 'open': [],
                          'finished': False, 'started': time.time()}
    threading.Thread(target=_run_scan, args=(job_id, ip, ports, timeout), daemon=True).start()
    return jsonify({'status': 'success', 'job_id': job_id, 'total': len(ports)})


@bp.route('/api/portscan/<job_id>', methods=['GET', 'DELETE'])
def api_portscan_status(job_id):
    job = _SCAN_JOBS.get(job_id)
    if not job:
        return jsonify({'status': 'error', 'message': 'Escaneo no encontrado.'}), 404
    if request.method == 'DELETE':
        job['cancel'] = True
    return jsonify({'status': 'success', **{k: v for k, v in job.items() if k != 'cancel'}})


# ---------- Exportar / Importar ----------
SECRET_ROUTER_KEYS = ('password',)


def build_backup(include_secrets=False):
    cfg = D['load_config']()
    c = json.loads(json.dumps(cfg))
    if not include_secrets:
        c['adguard_pass'] = ''
        for r in c.get('routers', []):
            for k in SECRET_ROUTER_KEYS:
                if k in r:
                    r[k] = ''
        if 'alerts' in c:
            c['alerts']['telegram_token'] = ''
            c['alerts']['smtp_pass'] = ''
    leases = D['read_leases']().get('leases', [])
    static = [{'mac': norm_mac(l.get('mac')), 'ip': l.get('ip'), 'hostname': l.get('hostname') or ''}
              for l in leases if l.get('static') and norm_mac(l.get('mac')) != '00:00:00:00:00:00']
    meta = {}
    for r in db_query('SELECT mac, notes, room, tags, known, photo FROM devices'):
        if r['notes'] or r['room'] or (r['tags'] and r['tags'] != '[]') or not r['known'] or r.get('photo'):
            meta[r['mac']] = {
                'notes': r['notes'], 'room': r['room'],
                'tags': json.loads(r['tags'] or '[]'), 'known': bool(r['known']),
                'photo': r.get('photo') or ''
            }
    topo_positions = kv_get('topology_custom_positions', {}) or {}
    return {
        'app': 'adguard-dhcp-panel', 'format_version': 1, 'exported_at': iso(now_ts()),
        'includes_secrets': bool(include_secrets),
        'config': c, 'static_leases': static, 'device_meta': meta, 'favorites': [],
        'topology_custom_positions': topo_positions,
    }


@bp.route('/api/backup/export')
def api_backup_export():
    inc = request.args.get('secrets') == '1'
    fmt = request.args.get('format', 'zip').lower()
    data = build_backup(inc)

    if fmt == 'json':
        fname = f"dhcp-panel-backup-{datetime.now().strftime('%Y%m%d-%H%M')}{'-con-claves' if inc else ''}.json"
        return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype='application/json',
                        headers={'Content-Disposition': f'attachment; filename="{fname}"'})

    # Por defecto: Archivo Comprimido .ZIP completo con backup.json y carpeta images/
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('backup.json', json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'))
        meta = data.get('device_meta') or {}
        for mac, info in meta.items():
            photo_b64 = info.get('photo')
            if photo_b64 and ',' in photo_b64:
                try:
                    header, b64 = photo_b64.split(',', 1)
                    ext = 'webp' if 'webp' in header else ('jpeg' if 'jpeg' in header or 'jpg' in header else 'png')
                    raw_img = base64.b64decode(b64)
                    clean_mac = norm_mac(mac).replace(':', '-').lower()
                    zf.writestr(f"images/{clean_mac}.{ext}", raw_img)
                    save_device_photo_file(mac, photo_b64)
                except Exception as e:
                    print(f"Error empaquetando imagen en zip para {mac}: {e}")

    buf.seek(0)
    fname = f"dhcp-panel-backup-{datetime.now().strftime('%Y%m%d-%H%M')}{'-con-claves' if inc else ''}.zip"
    return Response(buf.getvalue(), mimetype='application/zip',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})


def _validate_backup(b):
    if not isinstance(b, dict) or b.get('app') != 'adguard-dhcp-panel':
        raise ValueError('El archivo no es una copia de seguridad válida del Panel DHCP.')
    if int(b.get('format_version', 0)) > 1:
        raise ValueError('La copia es de una versión más nueva del panel.')
    for l in b.get('static_leases', []):
        if not valid_mac(l.get('mac')) or not valid_ipv4(l.get('ip')):
            raise ValueError(f'Concesión no válida en la copia: {l}')


def _diff_backup(b):
    cur = build_backup(True)
    cur_static = {l['mac']: l for l in cur['static_leases']}
    ip_owner = {l['ip']: l['mac'] for l in cur['static_leases']}
    leases = {'add': [], 'change': [], 'same': [], 'conflict': [], 'remove_if_replace': []}
    bk_macs = set()
    for l in b.get('static_leases', []):
        m = norm_mac(l['mac'])
        bk_macs.add(m)
        c = cur_static.get(m)
        owner = ip_owner.get(l['ip'])
        if owner and owner != m:
            leases['conflict'].append({**l, 'current_owner': owner})
        elif c is None:
            leases['add'].append(l)
        elif c['ip'] != l['ip'] or (c['hostname'] or '') != (l.get('hostname') or ''):
            leases['change'].append({**l, 'old_ip': c['ip'], 'old_hostname': c['hostname']})
        else:
            leases['same'].append(l)
    for m, l in cur_static.items():
        if m not in bk_macs:
            leases['remove_if_replace'].append(l)
    bc = b.get('config', {})
    cc = cur['config']
    cur_r = {(r.get('ip'), r.get('type')) for r in cc.get('routers', [])}
    bk_r = {(r.get('ip'), r.get('type')) for r in bc.get('routers', [])}
    names_b = bc.get('custom_service_names') or {}
    names_c = cc.get('custom_service_names') or {}
    return {
        'exported_at': b.get('exported_at'), 'includes_secrets': b.get('includes_secrets'),
        'leases': leases,
        'routers': {'backup': [r.get('name') for r in bc.get('routers', [])], 'new': len(bk_r - cur_r), 'missing': len(cur_r - bk_r)},
        'adguard': {'url': bc.get('adguard_url'), 'user': bc.get('adguard_user'), 'changes': bc.get('adguard_url') != cc.get('adguard_url') or bc.get('adguard_user') != cc.get('adguard_user')},
        'names': {'total': len(names_b), 'changed': sum(1 for k, v in names_b.items() if names_c.get(k) != v)},
        'meta': {'total': len(b.get('device_meta') or {})},
        'favorites': len(b.get('favorites') or []),
        'alerts': bool(bc.get('alerts')),
        'topology_nodes': len(b.get('topology_custom_positions') or b.get('topology_layout') or {}),
    }


@bp.route('/api/backup/preview', methods=['POST'])
def api_backup_preview():
    try:
        b = None
        images_found = 0
        if 'file' in request.files:
            f = request.files['file']
            filename = (f.filename or '').lower()
            if filename.endswith('.zip'):
                content = f.read()
                with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
                    json_name = next((n for n in zf.namelist() if n == 'backup.json' or n.endswith('.json')), None)
                    if not json_name:
                        return jsonify({'status': 'error', 'message': 'El archivo .zip no contiene ningún backup.json válido.'})
                    b = json.loads(zf.read(json_name).decode('utf-8'))
                    meta = b.get('device_meta') or {}
                    for name in zf.namelist():
                        if name.startswith('images/') or name.startswith('photos/'):
                            base_name = os.path.basename(name)
                            if not base_name: continue
                            raw_img = zf.read(name)
                            if PHOTOS_DIR:
                                with open(os.path.join(PHOTOS_DIR, base_name), 'wb') as img_out:
                                    img_out.write(raw_img)
                            ext = os.path.splitext(base_name)[1].lstrip('.').lower()
                            mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else f'image/{ext}'
                            b64 = f"data:{mime};base64,{base64.b64encode(raw_img).decode('ascii')}"
                            target_mac_prefix = os.path.splitext(base_name)[0].lower()
                            for m in meta:
                                if norm_mac(m).replace(':', '-').lower() == target_mac_prefix:
                                    meta[m]['photo'] = b64
                                    images_found += 1
                                    break
            else:
                b = json.loads(f.read().decode('utf-8'))
        else:
            b = request.get_json(force=True)

        _validate_backup(b)
        diff = _diff_backup(b)
        return jsonify({'status': 'success', 'diff': diff, 'backup': b, 'images_count': images_found})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@bp.route('/api/backup/apply', methods=['POST'])
def api_backup_apply():
    body = request.get_json(force=True) or {}
    b = body.get('backup')
    opts = body.get('options') or {}
    try:
        _validate_backup(b)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
    done = []
    cfg = D['load_config']()
    bc = b.get('config', {})

    if opts.get('config'):
        old_routers = cfg.get('routers', [])
        new_routers = json.loads(json.dumps(bc.get('routers', [])))
        for r in new_routers:  # conservar contraseñas actuales si la copia no las trae
            if not r.get('password'):
                prev = next((o for o in old_routers if o.get('id') == r.get('id') or (o.get('ip') == r.get('ip') and o.get('type') == r.get('type'))), None)
                if prev:
                    r['password'] = prev.get('password', '')
        cfg['routers'] = new_routers
        for k in ('adguard_url', 'adguard_user'):
            if bc.get(k):
                cfg[k] = bc[k]
        if bc.get('adguard_pass'):
            cfg['adguard_pass'] = bc['adguard_pass']
        done.append(f'{len(new_routers)} routers y conexión con AdGuard')
    if opts.get('alerts') and bc.get('alerts'):
        a = dict(bc['alerts'])
        if not a.get('telegram_token'):
            a['telegram_token'] = (cfg.get('alerts') or {}).get('telegram_token', '')
        if not a.get('smtp_pass'):
            a['smtp_pass'] = (cfg.get('alerts') or {}).get('smtp_pass', '')
        cfg['alerts'] = a
        done.append('alertas')
    if opts.get('names'):
        names = dict(cfg.get('custom_service_names') or {})
        names.update(bc.get('custom_service_names') or {})
        cfg['custom_service_names'] = names
        done.append(f'{len(bc.get("custom_service_names") or {})} nombres de servicios')
    if opts.get('config') or opts.get('names') or opts.get('alerts'):
        D['save_config_raw'](cfg)

    if opts.get('meta'):
        n = 0
        for mac, m in (b.get('device_meta') or {}).items():
            mac = norm_mac(mac)
            if not valid_mac(mac):
                continue
            if not db_query('SELECT mac FROM devices WHERE mac=?', (mac,)):
                db_exec('INSERT INTO devices (mac, first_seen, known) VALUES (?,?,1)', (mac, now_ts()))
            db_exec('UPDATE devices SET notes=?, room=?, tags=?, known=?, photo=COALESCE(?, photo) WHERE mac=?',
                    (m.get('notes') or '', m.get('room') or '', json.dumps(m.get('tags') or []), 1 if m.get('known', True) else 0, m.get('photo'), mac))
            n += 1
        done.append(f'fichas de {n} dispositivos')

    if opts.get('topology', True):
        topo_b = b.get('topology_custom_positions') or b.get('topology_layout')
        if topo_b and isinstance(topo_b, dict) and len(topo_b) > 0:
            kv_set('topology_custom_positions', topo_b)
            done.append(f'distribución de topología ({len(topo_b)} nodos)')

    if opts.get('leases'):
        replace = opts.get('leases_mode') == 'replace'
        bk = [{'mac': norm_mac(l['mac']), 'ip': l['ip'], 'hostname': l.get('hostname') or ''} for l in b.get('static_leases', [])]
        bk_macs = {l['mac'] for l in bk}
        bk_ips = {l['ip'] for l in bk}
        D['run_sudo'](['docker', 'stop', 'adguardhome'])
        try:
            data = D['read_leases']()
            kept = []
            for l in data.get('leases', []):
                m = norm_mac(l.get('mac'))
                if m in bk_macs or (l.get('ip') in bk_ips):
                    continue
                if replace and l.get('static'):
                    continue
                kept.append(l)
            for l in bk:
                kept.append({'expires': '', 'ip': l['ip'], 'hostname': l['hostname'], 'mac': l['mac'], 'static': True})
            data['leases'] = kept
            D['write_leases'](data)
        finally:
            D['run_sudo'](['docker', 'start', 'adguardhome'])
        done.append(f'{len(bk)} IPs estáticas ({"reemplazo total" if replace else "fusión"})')

    return jsonify({'status': 'success', 'message': 'Importación completada: ' + (', '.join(done) if done else 'nada seleccionado') + '.'})


# =====================================================================
#  Inicialización
# =====================================================================
def init_app(app, deps):
    global DB_PATH
    D.update(deps)
    data_dir = os.environ.get('DHCP_PANEL_DATA_DIR') or os.path.dirname(deps['CONFIG_PATH'])
    os.makedirs(data_dir, exist_ok=True)
    global PHOTOS_DIR
    DB_PATH = os.path.join(data_dir, 'panel.db')
    PHOTOS_DIR = os.path.join(data_dir, 'photos')
    os.makedirs(PHOTOS_DIR, exist_ok=True)
    init_db()
    app.register_blueprint(bp)
    if os.environ.get('DHCP_PANEL_NO_MONITOR') != '1':
        threading.Thread(target=monitor_loop, daemon=True, name='panel-monitor').start()

@bp.route('/api/topology/positions', methods=['GET', 'POST'])
def api_topology_positions():
    if request.method == 'POST':
        data = request.get_json(force=True) or {}
        if isinstance(data, dict):
            kv_set('topology_custom_positions', data)
            return jsonify({'status': 'success', 'count': len(data)})
        return jsonify({'status': 'error', 'message': 'Formato no válido'}), 400
    pos = kv_get('topology_custom_positions', {}) or {}
    return jsonify({'status': 'success', 'positions': pos})
