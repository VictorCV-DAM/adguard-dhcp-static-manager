#!/usr/bin/env python3
"""
send_nak.py - Inyector L2 de paquetes DHCPNAK y purga ARP para reasignación forzada de IPs.
Uso: sudo python3 send_nak.py <MAC> [SERVER_IP] [OLD_IP] [IFACE]
"""
import sys
import socket
import struct
import time
import subprocess

def send_dhcp_nak(mac_str, server_ip="192.168.1.249", old_ip=None, iface="eth0"):
    mac_clean = mac_str.replace(':', '').replace('-', '').lower()
    if len(mac_clean) != 12:
        print(f"MAC inválida: {mac_str}", file=sys.stderr)
        return False

    mac_bytes = bytes.fromhex(mac_clean)

    # Si se proporciona la IP anterior, purgar su entrada ARP del kernel
    if old_ip:
        try:
            subprocess.run(['ip', 'neigh', 'del', old_ip, 'dev', iface], capture_output=True)
        except Exception:
            pass

    # 1. Construir paquete DHCP NAK (RFC 2131)
    # Magic cookie DHCP: 0x63, 0x82, 0x53, 0x63
    xid = b'\x3a\x7f\x11\x20'
    secs = b'\x00\x00'
    flags = b'\x80\x00'  # Broadcast flag activo para que llegue a través de switches y APs
    ciaddr = b'\x00\x00\x00\x00'
    yiaddr = b'\x00\x00\x00\x00'
    siaddr = socket.inet_aton(server_ip)
    giaddr = b'\x00\x00\x00\x00'
    chaddr = mac_bytes + b'\x00' * 10
    sname = b'\x00' * 64
    file_bytes = b'\x00' * 128
    magic_cookie = b'\x63\x82\x53\x63'

    opt_msg_type = b'\x35\x01\x06'  # Type 6 = DHCPNAK
    opt_server_id = b'\x36\x04' + socket.inet_aton(server_ip)
    opt_msg = b'\x38\x12Reassigning static'  # Option 56: Message
    opt_end = b'\xff'

    dhcp_payload = (
        b'\x02\x01\x06\x00' +
        xid + secs + flags +
        ciaddr + yiaddr + siaddr + giaddr +
        chaddr + sname + file_bytes +
        magic_cookie + opt_msg_type + opt_server_id + opt_msg + opt_end
    )

    if len(dhcp_payload) < 300:
        dhcp_payload += b'\x00' * (300 - len(dhcp_payload))

    # 2. Encabezado UDP (puerto origen 67 -> destino 68)
    udp_len = 8 + len(dhcp_payload)
    udp_hdr = struct.pack('!HHHH', 67, 68, udp_len, 0)

    # 3. Encabezado IPv4 (server_ip -> 255.255.255.255)
    ip_ihl_ver = (4 << 4) | 5
    ip_tos = 0
    ip_tot_len = 20 + udp_len
    ip_id = 54321
    ip_frag_off = 0
    ip_ttl = 128
    ip_proto = 17  # UDP
    ip_saddr = socket.inet_aton(server_ip)
    ip_daddr = socket.inet_aton("255.255.255.255")

    def checksum(msg):
        s = 0
        if len(msg) % 2 == 1:
            msg += b'\x00'
        for i in range(0, len(msg), 2):
            w = (msg[i] << 8) + msg[i+1]
            s += w
        while s >> 16:
            s = (s & 0xffff) + (s >> 16)
        return ~s & 0xffff

    ip_hdr_no_chk = struct.pack('!BBHHHBBH4s4s', ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl, ip_proto, 0, ip_saddr, ip_daddr)
    ip_check = checksum(ip_hdr_no_chk)
    ip_hdr = struct.pack('!BBHHHBBH4s4s', ip_ihl_ver, ip_tos, ip_tot_len, ip_id, ip_frag_off, ip_ttl, ip_proto, ip_check, ip_saddr, ip_daddr)

    # 4. Encabezado Ethernet L2 (Broadcast a ff:ff:ff:ff:ff:ff)
    eth_dst = b'\xff\xff\xff\xff\xff\xff'
    import uuid
    eth_src = bytes.fromhex(hex(uuid.getnode())[2:].zfill(12))
    eth_type = struct.pack('!H', 0x0800)
    eth_hdr = eth_dst + eth_src + eth_type

    full_packet = eth_hdr + ip_hdr + udp_hdr + dhcp_payload

    try:
        raw_sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW)
        raw_sock.bind((iface, 0))
        for _ in range(4):
            raw_sock.send(full_packet)
            time.sleep(0.05)
        raw_sock.close()
        print(f"OK: Enviados 4 paquetes DHCPNAK a {mac_str} vía {iface}")
        return True
    except Exception as e:
        print(f"Error enviando DHCPNAK: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Uso: python3 send_nak.py <MAC> [SERVER_IP] [OLD_IP] [IFACE]")
        sys.exit(1)
    target_mac = sys.argv[1]
    sip = sys.argv[2] if len(sys.argv) > 2 else "192.168.1.249"
    oip = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != '-' else None
    ifa = sys.argv[4] if len(sys.argv) > 4 else "eth0"
    success = send_dhcp_nak(target_mac, sip, oip, ifa)
    sys.exit(0 if success else 1)
