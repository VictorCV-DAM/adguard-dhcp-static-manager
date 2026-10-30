# -*- coding: utf-8 -*-
"""
Advanced features for AdGuard Home DHCP Panel:
  - SQLite persistence: presence history, known services, uptime checks, event log
  - Background monitor (ping latency, TTL/OS fingerprinting, real service status, presence)
  - Alerts (ntfy, Telegram Bot, generic Webhook / Home Assistant / Discord)
  - Configuration Export / Import with interactive diff preview
  - Visual IP Subnet Map (1-254), Network Diagnostics, Device Detail Sheet, Presence Timeline
  - Device Actions: Block/Unblock Internet (AdGuard DNS), Wake-on-LAN, TCP Port Scanner
"""
import os
import re
import json
import time
import socket
import sqlite3
import secrets
import threading
import subprocess
import urllib.request
import urllib.parse
import http.cookiejar
from collections import Counter
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

from flask import Blueprint, request, jsonify, Response

bp = Blueprint('extras', __name__)

D = {}                    # dependencies injected from app.py
DB_PATH = None
_DB_LOCK = threading.Lock()
_PING = {}                # ip -> {'ts', 'ms', 'ttl', 'alive'}
_MONITOR_STATE = {'last_run': 0, 'running': False, 'last_error': '', 'cycles': 0}
_SCAN_JOBS = {}           # job_id -> {...}
MONITOR_INTERVAL = int(os.environ.get('DHCP_PANEL_MONITOR_INTERVAL', '60'))
SERVICE_DOWN_THRESHOLD = 2   # consecutive failed checks before marking service down
OFFLINE_GRACE_SEC = 300      # seconds without seeing a device before marking it offline

DEFAULT_ALERTS = {
    'enabled': False,
    'ntfy_url': '',
    'telegram_token': '',
    'telegram_chat_id': '',
    'webhook_url': '',
    'notify_new_device': True,
    'notify_service_down': True,
    'notify_service_up': True,
    'notify_watched_offline': True,
    'watched_macs': [],
}


# =====================================================================
#  Utilities
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
#  Database
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
        con.commit()
        con.close()


def kv_get(k, default=None):
    r = db_query('SELECT v FROM kv WHERE k=?', (k,))
    return json.loads(r[0]['v']) if r else default


def kv_set(k, v):
    db_exec('INSERT OR REPLACE INTO kv (k, v) VALUES (?, ?)', (k, json.dumps(v)))


# =====================================================================
#  Ping / Latency / TTL Fingerprinting
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
    if ttl <= 64:
        if any(k in c for k in ['iphone', 'ipad', 'apple']):
            return 'iOS / macOS'
        if any(k in c for k in ['smartphone', 'mobile', 'android']):
            return 'Android'
        if any(k in c for k in ['iot', 'plug', 'bulb', 'sensor', 'esp', 'smart', 'lighting']):
            return 'IoT Firmware (RTOS/Linux)'
        return 'Linux / Android / Unix'
    if ttl <= 128:
        return 'Windows'
    return 'Network Gear (Cisco/Router)'


def tcp_latency(ip, port, timeout=1.5):
    t0 = time.time()
    try:
        s = socket.create_connection((ip, int(port)), timeout=timeout)
        s.close()
        return True, round((time.time() - t0) * 1000, 1)
    except Exception:
        return False, None


# =====================================================================
#  Alerts
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


def send_alert(title, message, kind='info', force=False, cfg_override=None):
    """Logs the event and dispatches it through configured alert channels."""
    a = cfg_override or get_alerts_cfg()
    results = []
    sent = 0
    if a.get('enabled') or force:
        prio = {'new_device': 'high', 'service_down': 'high', 'offline': 'default'}.get(kind, 'default')
        tag = {'new_device': 'rotating_light', 'service_down': 'red_circle', 'service_up': 'green_circle',
               'offline': 'warning', 'online': 'white_check_mark', 'test': 'bell'}.get(kind, 'bell')
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
        sent = 1 if any(r[1] for r in results) else 0
    db_exec('INSERT INTO events_log (ts, kind, title, message, sent) VALUES (?,?,?,?,?)',
            (now_ts(), kind, title, message, sent))
    return results


# =====================================================================
#  Background Monitor
# =====================================================================
def monitor_cycle():
    state = D['build_state'](False)
    devices = state.get('devices', [])
    ts = now_ts()
    alerts = get_alerts_cfg()

    # --- Concurrent ping to active devices (latency + TTL) ---
    ips = sorted({d['ip'] for d in devices if d.get('live_ips') and valid_ipv4(d.get('ip'))})
    with ThreadPoolExecutor(max_workers=32) as pool:
        for ip, r in zip(ips, pool.map(ping_detail, ips)):
            _PING[ip] = r

    # --- Device presence tracking ---
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
                send_alert('🚨 New Device on Network',
                           f"{d.get('hostname') or '(Unnamed)'} · {d.get('ip')} · {mac}\n"
                           f"{d.get('dev_vendor') or ''} — {d.get('dev_class') or ''}", 'new_device')
            continue

        if online:
            db_exec('UPDATE devices SET last_seen=?, last_ip=?, hostname=?, latency_ms=COALESCE(?, latency_ms), ttl=COALESCE(?, ttl) WHERE mac=?',
                    (ts, d.get('ip'), d.get('hostname'), p.get('ms'), p.get('ttl'), mac))
            if not row['online']:
                db_exec('UPDATE devices SET online=1 WHERE mac=?', (mac,))
                db_exec('INSERT INTO device_events (ts, mac, ip, event) VALUES (?,?,?,?)', (ts, mac, d.get('ip'), 'online'))
                if mac in watched and alerts.get('notify_watched_offline', True):
                    send_alert('✅ Watched Device Online', f"{d.get('hostname')} ({d.get('ip')}) is back online.", 'online')
        else:
            last = row['last_seen'] or 0
            if row['online'] and ts - last > OFFLINE_GRACE_SEC:
                db_exec('UPDATE devices SET online=0 WHERE mac=?', (mac,))
                db_exec('INSERT INTO device_events (ts, mac, ip, event) VALUES (?,?,?,?)', (ts, mac, d.get('ip'), 'offline'))
                if mac in watched and alerts.get('notify_watched_offline', True):
                    send_alert('⚠️ Watched Device Offline',
                               f"{d.get('hostname')} ({d.get('ip')}) has not responded for {OFFLINE_GRACE_SEC // 60} min.", 'offline')

    # --- Services: currently detected + previously known ---
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
                send_alert('🟢 Service Recovered', f"{label} ({url}) is responding again.", 'service_up')
        else:
            fc = (r['fail_count'] or 0) + 1
            alerted = r['alerted_down']
            if fc >= SERVICE_DOWN_THRESHOLD and not alerted:
                alerted = 1
                if alerts.get('notify_service_down', True):
                    send_alert('🔴 Service Down', f"{label} ({url}) failed {fc} consecutive checks.", 'service_down')
            db_exec('UPDATE services SET last_check=?, up=?, fail_count=?, alerted_down=? WHERE url=?',
                    (ts, 0 if fc >= SERVICE_DOWN_THRESHOLD else 1, fc, alerted, url))
    if checks:
        db_exec('INSERT INTO service_checks (url, ts, up, ms) VALUES (?,?,?,?)', checks, many=True)

    # --- Daily pruning ---
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
#  Enrich /api/state with persistent data
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

    detected_urls = set()
    for d in state.get('devices', []):
        mac = norm_mac(d.get('mac'))
        row = devs.get(mac) or {}
        p = _PING.get(d.get('ip')) or {}
        ttl = p.get('ttl') or row.get('ttl')
        d['first_seen'] = iso(row.get('first_seen'))
        d['last_seen'] = iso(row.get('last_seen')) if not d.get('live_ips') else iso(now_ts())
        d['notes'] = row.get('notes') or ''
        d['room'] = row.get('room') or ''
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
        for l in d.get('web_links') or []:
            detected_urls.add(l['url'])
            sr = svc_rows.get(l['url']) or {}
            u = upt.get(l['url'])
            l['status'] = 'up' if sr.get('up', 1) else 'down'
            l['latency_ms'] = sr.get('latency_ms')
            l['uptime_24h'] = round(u['avg_up'] * 100, 1) if u and u['n'] else None
            l['history'] = (hist.get(l['url']) or [])[-40:]
            l['first_seen'] = iso(sr.get('first_seen'))

    # Previously known services that are no longer responding -> down
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
#  AdGuard Home API (DNS stats & client blocking)
# =====================================================================
def ag_opener():
    cfg = D['load_config']()
    url = (cfg.get('adguard_url') or '').rstrip('/')
    user = (cfg.get('adguard_user') or '').strip()
    pwd = (cfg.get('adguard_pass') or '').strip()
    if not url or not user or not pwd:
        raise RuntimeError('AdGuard Home credentials not configured (⚙️ Settings).')
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    req = urllib.request.Request(f'{url}/control/login', data=json.dumps({'name': user, 'password': pwd}).encode(),
                                 headers={'Content-Type': 'application/json'}, method='POST')
    op.open(req, timeout=5).read()
    return op, url


def ag_get(path):
    op, url = ag_opener()
    with op.open(f'{url}{path}', timeout=8) as r:
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
    return {
        'total': len(entries),
        'blocked_total': sum(blocked.values()),
        'top_domains': domains.most_common(15),
        'top_blocked': blocked.most_common(10),
        'oldest': entries[-1].get('time') if entries else None,
    }


# =====================================================================
#  DHCP Pool Range
# =====================================================================
def dhcp_range():
    try:
        yaml_path = D.get('YAML_PATH') or D['load_config']().get('yaml_path', '/opt/adguardhome/conf/AdGuardHome.yaml')
        res = D['run_sudo'](['cat', yaml_path])
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


# ---------- Services ----------
@bp.route('/api/services/forget', methods=['POST'])
def api_services_forget():
    url = (request.json or {}).get('url') or ''
    db_exec('DELETE FROM services WHERE url=?', (url,))
    db_exec('DELETE FROM service_checks WHERE url=?', (url,))
    return jsonify({'status': 'success', 'message': 'Service forgotten. If it comes back online, it will be rediscovered.'})


# ---------- Alerts ----------
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
    return jsonify({'status': 'success', 'message': 'Alert configuration saved.', 'alerts': a})


@bp.route('/api/alerts/test', methods=['POST'])
def api_alerts_test():
    body = request.json or {}
    a = get_alerts_cfg()
    a.update({k: v for k, v in body.items() if k in DEFAULT_ALERTS})
    if not (a.get('ntfy_url') or (a.get('telegram_token') and a.get('telegram_chat_id')) or a.get('webhook_url')):
        return jsonify({'status': 'error', 'message': 'No notification channel configured (ntfy, Telegram, or Webhook).'})
    res = send_alert('🔔 Alert Test', 'If you see this message, DHCP Panel notifications are working.', 'test',
                     force=True, cfg_override=a)
    ok = [r[0] for r in res if r[1]]
    ko = [f'{r[0]}: {r[2]}' for r in res if not r[1]]
    msg = (f'Successfully sent via: {", ".join(ok)}. ' if ok else '') + (f'Failed → {" | ".join(ko)}' if ko else '')
    return jsonify({'status': 'success' if ok else 'error', 'message': msg or 'No results.'})


@bp.route('/api/events')
def api_events():
    limit = min(int(request.args.get('limit', 100)), 500)
    rows = db_query('SELECT * FROM events_log ORDER BY ts DESC LIMIT ?', (limit,))
    for r in rows:
        r['time'] = iso(r['ts'])
    return jsonify({'status': 'success', 'events': rows})


# ---------- Device Detail Sheet ----------
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
        return jsonify({'status': 'error', 'message': 'Invalid MAC address.'}), 400
    body = request.json or {}
    if not db_query('SELECT mac FROM devices WHERE mac=?', (mac,)):
        db_exec('INSERT INTO devices (mac, first_seen, known) VALUES (?,?,1)', (mac, now_ts()))
    fields, vals = [], []
    if 'notes' in body:
        fields.append('notes=?'); vals.append(str(body['notes'])[:2000])
    if 'room' in body:
        fields.append('room=?'); vals.append(str(body['room'])[:60])
    if 'tags' in body and isinstance(body['tags'], list):
        fields.append('tags=?'); vals.append(json.dumps([str(t)[:30] for t in body['tags']][:15]))
    if 'known' in body:
        fields.append('known=?'); vals.append(1 if body['known'] else 0)
    if fields:
        db_exec(f'UPDATE devices SET {", ".join(fields)} WHERE mac=?', (*vals, mac))
    return jsonify({'status': 'success', 'message': 'Device details saved.'})


# ---------- Presence Timeline ----------
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


# ---------- Visual IP Map ----------
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


# ---------- Network Diagnostics ----------
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

    arp = D['get_arp_table']()
    ip_macs = {}
    for m, ips in arp.items():
        for ip in ips:
            ip_macs.setdefault(ip, set()).add(m)
    for ip, macs in ip_macs.items():
        if len(macs) > 1:
            add('critical', 'Conflict', f'Duplicate IP {ip}', f'Multiple MACs responding on the same IP: {", ".join(sorted(macs))}', ip=ip)

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
            add('warning', 'Leases', 'Multiple leases for the same device',
                f'{m} has leases on {", ".join(sorted(ips))}', mac=m, fix='Delete stale leases from the table.')
    for ip, macs in by_ip.items():
        if len(macs) > 1:
            add('critical', 'Conflict', f'IP {ip} assigned to multiple MACs in AdGuard', ', '.join(sorted(macs)), ip=ip)

    for d in devices:
        ip, mac, host = d.get('ip'), d.get('mac'), d.get('hostname') or ''
        n = ip_last(ip or '')
        if d.get('static') and not d.get('manual_static') and rs > 0 and rs <= n <= re_:
            add('warning', 'DHCP', f'Static IP inside dynamic pool ({ip})',
                f'{host}: IP {ip} is inside dynamic pool {rng["start"]}–{rng["end"]}. AdGuard may hand it out to another device.',
                mac=mac, ip=ip, fix='Assign an IP outside the dynamic range (use the 🗺️ IP Map).')
        if d.get('mismatch_ip'):
            add('warning', 'Mismatch', f'{host} is using a different IP than assigned',
                f'Assigned {ip}, but responding at {d.get("mismatch_ip")}. It may not have renewed its lease yet.',
                mac=mac, ip=ip, fix='Use "⚡ Save + Force AP Reconnect" or reboot the device.')
        if is_lam(mac) and d.get('static'):
            add('info', 'Privacy', f'{host}: Randomized MAC with static IP',
                f'{mac} is a locally administered/randomized MAC; if rotated, the static reservation will stop matching.',
                mac=mac, ip=ip, fix='Disable "Private Wi-Fi Address" for your home SSID on this device.')
        if re.fullmatch(r'(\(unnamed\)|\(sin nombre\)|192-168-1-\d+|android-[0-9a-f]+|esp_[0-9a-f]+|unknown.*|)', host.lower()):
            add('info', 'Identification', f'Device without descriptive name ({ip})',
                f'"{host}" · {d.get("dev_vendor") or ""}', mac=mac, ip=ip, fix='Set a hostname using "Edit / Pin".')
        if d.get('expired'):
            add('info', 'Leases', f'Expired lease: {host} ({ip})', 'Can be cleaned with "🧹 Purge".', mac=mac, ip=ip)

    if state.get('ghost_count'):
        add('info', 'Leases', f'{state["ghost_count"]} ghost entries (00:00:00:00:00:00)', 'Click "🧹 Purge".')

    for s in db_query('SELECT * FROM services WHERE up=0'):
        add('warning', 'Services', f'Service down: {s["label"]}', f'{s["url"]} · last seen online: {iso(s["last_seen_up"]) or "never"}', mac=s['mac'], ip=s['ip'])

    if _MONITOR_STATE['last_error']:
        add('warning', 'Panel', 'Background monitor error', _MONITOR_STATE['last_error'])

    order = {'critical': 0, 'warning': 1, 'info': 2}
    issues.sort(key=lambda i: order.get(i['severity'], 3))
    counts = Counter(i['severity'] for i in issues)
    score = max(0, 100 - counts.get('critical', 0) * 20 - counts.get('warning', 0) * 6 - counts.get('info', 0) * 1)
    return jsonify({'status': 'success', 'issues': issues, 'counts': dict(counts), 'score': score, 'range': rng})


# ---------- Device Actions ----------
@bp.route('/api/device/block', methods=['POST'])
def api_device_block():
    body = request.json or {}
    ip = (body.get('ip') or '').strip()
    block = bool(body.get('block'))
    if not valid_ipv4(ip):
        return jsonify({'status': 'error', 'message': 'Invalid IP address.'})
    if ip in ('192.168.1.249', '192.168.1.1', '127.0.0.1') and block:
        return jsonify({'status': 'error', 'message': 'Cannot block the local server or main gateway.'})
    try:
        set_client_blocked(ip, block)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'AdGuard Home: {e}'})
    send_alert('⛔ Internet Blocked' if block else '✅ Internet Restored', f'Client {ip}', 'info')
    return jsonify({'status': 'success', 'message': (
        f'⛔ {ip} blocked in AdGuard Home: DNS resolution is now disabled for this client.'
        if block else f'✅ {ip} unblocked: Internet access restored.')})


@bp.route('/api/wol', methods=['POST'])
def api_wol():
    mac = norm_mac((request.json or {}).get('mac'))
    if not valid_mac(mac):
        return jsonify({'status': 'error', 'message': 'Invalid MAC address.'})
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
        return jsonify({'status': 'error', 'message': 'Could not send Wake-on-LAN magic packet.'})
    return jsonify({'status': 'success', 'message': f'⚡ Wake-on-LAN magic packet sent to {mac}. If WoL is enabled in BIOS/NIC, the host will boot shortly.'})


COMMON_PORT_NAMES = {
    20: 'FTP-data', 21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS', 67: 'DHCP', 80: 'HTTP', 81: 'HTTP-alt',
    110: 'POP3', 111: 'RPC', 123: 'NTP', 135: 'MS-RPC', 139: 'NetBIOS', 143: 'IMAP', 161: 'SNMP', 443: 'HTTPS',
    445: 'SMB', 548: 'AFP', 554: 'RTSP', 631: 'IPP (Printer)', 853: 'DNS-over-TLS', 993: 'IMAPS', 995: 'POP3S',
    1080: 'SOCKS', 1194: 'OpenVPN', 1433: 'MSSQL', 1883: 'MQTT', 1900: 'UPnP', 1984: 'go2rtc', 2283: 'Immich',
    3000: 'Grafana/Node', 3306: 'MySQL', 3389: 'RDP', 4357: 'HA Observer', 5000: 'HTTP-alt', 5001: 'HTTP-alt',
    5353: 'mDNS', 5432: 'PostgreSQL', 5900: 'VNC', 6052: 'ESPHome', 6379: 'Redis', 6881: 'BitTorrent',
    8006: 'Proxmox', 8080: 'HTTP-proxy', 8086: 'InfluxDB', 8096: 'Jellyfin', 8123: 'Home Assistant', 8443: 'HTTPS-alt',
    8883: 'MQTT-TLS', 8888: 'HTTP-alt', 9000: 'Portainer', 9100: 'RAW Printer', 9443: 'Portainer-TLS',
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
        return jsonify({'status': 'error', 'message': 'Only local network IPs are allowed.'})
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
        return jsonify({'status': 'error', 'message': 'Scan job not found.'}), 404
    if request.method == 'DELETE':
        job['cancel'] = True
    return jsonify({'status': 'success', **{k: v for k, v in job.items() if k != 'cancel'}})


# ---------- Export / Import ----------
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
    leases = D['read_leases']().get('leases', [])
    static = [{'mac': norm_mac(l.get('mac')), 'ip': l.get('ip'), 'hostname': l.get('hostname') or ''}
              for l in leases if l.get('static') and norm_mac(l.get('mac')) != '00:00:00:00:00:00']
    meta = {}
    for r in db_query('SELECT mac, notes, room, tags, known FROM devices'):
        if r['notes'] or r['room'] or (r['tags'] and r['tags'] != '[]') or not r['known']:
            meta[r['mac']] = {'notes': r['notes'], 'room': r['room'], 'tags': json.loads(r['tags'] or '[]'), 'known': bool(r['known'])}
    return {
        'app': 'adguard-dhcp-panel', 'format_version': 1, 'exported_at': iso(now_ts()),
        'includes_secrets': bool(include_secrets),
        'config': c, 'static_leases': static, 'device_meta': meta, 'favorites': [],
    }


@bp.route('/api/backup/export')
def api_backup_export():
    inc = request.args.get('secrets') == '1'
    data = build_backup(inc)
    fname = f"dhcp-panel-backup-{datetime.now().strftime('%Y%m%d-%H%M')}{'-with-secrets' if inc else ''}.json"
    return Response(json.dumps(data, indent=2, ensure_ascii=False), mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="{fname}"'})


def _validate_backup(b):
    if not isinstance(b, dict) or b.get('app') != 'adguard-dhcp-panel':
        raise ValueError('File is not a valid AdGuard DHCP Panel backup.')
    if int(b.get('format_version', 0)) > 1:
        raise ValueError('Backup is from a newer version of the panel.')
    for l in b.get('static_leases', []):
        if not valid_mac(l.get('mac')) or not valid_ipv4(l.get('ip')):
            raise ValueError(f'Invalid lease in backup: {l}')


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
    }


@bp.route('/api/backup/preview', methods=['POST'])
def api_backup_preview():
    try:
        b = request.get_json(force=True)
        _validate_backup(b)
        return jsonify({'status': 'success', 'diff': _diff_backup(b)})
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
        for r in new_routers:
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
        done.append(f'{len(new_routers)} routers and AdGuard connection')
    if opts.get('alerts') and bc.get('alerts'):
        a = dict(bc['alerts'])
        if not a.get('telegram_token'):
            a['telegram_token'] = (cfg.get('alerts') or {}).get('telegram_token', '')
        cfg['alerts'] = a
        done.append('alerts')
    if opts.get('names'):
        names = dict(cfg.get('custom_service_names') or {})
        names.update(bc.get('custom_service_names') or {})
        cfg['custom_service_names'] = names
        done.append(f'{len(bc.get("custom_service_names") or {})} service names')
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
            db_exec('UPDATE devices SET notes=?, room=?, tags=?, known=? WHERE mac=?',
                    (m.get('notes') or '', m.get('room') or '', json.dumps(m.get('tags') or []), 1 if m.get('known', True) else 0, mac))
            n += 1
        done.append(f'metadata for {n} devices')

    if opts.get('leases'):
        replace = opts.get('leases_mode') == 'replace'
        bk = [{'mac': norm_mac(l['mac']), 'ip': l['ip'], 'hostname': l.get('hostname') or ''} for l in b.get('static_leases', [])]
        bk_macs = {l['mac'] for l in bk}
        bk_ips = {l['ip'] for l in bk}
        container = cfg.get('docker_container', 'adguardhome')
        D['run_sudo'](['docker', 'stop', container])
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
            D['run_sudo'](['docker', 'start', container])
        done.append(f'{len(bk)} static leases ({"full replace" if replace else "merged"})')

    return jsonify({'status': 'success', 'message': 'Import completed: ' + (', '.join(done) if done else 'nothing selected') + '.'})


# =====================================================================
#  Initialization
# =====================================================================
def init_app(app, deps):
    global DB_PATH
    D.update(deps)
    data_dir = os.environ.get('DHCP_PANEL_DATA_DIR') or os.path.dirname(deps['CONFIG_PATH'])
    os.makedirs(data_dir, exist_ok=True)
    DB_PATH = os.path.join(data_dir, 'panel.db')
    init_db()
    app.register_blueprint(bp)
    if os.environ.get('DHCP_PANEL_NO_MONITOR') != '1':
        threading.Thread(target=monitor_loop, daemon=True, name='panel-monitor').start()
