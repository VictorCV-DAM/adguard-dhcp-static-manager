/**
 * Diccionario Internacional de Traducciones (i18n)
 * Gestor Directo de IPs Estáticas — AdGuard Home
 * 
 * Idiomas:
 *   - 'es': Español (Nativo)
 *   - 'en': English (Complete)
 */
const TRANSLATIONS = {
    es: {
    "header_title": "Gestor Directo de IPs Estáticas — AdGuard Home",
    "header_subtitle": "Reasigna IPs estáticas purgando la concesión previa al instante sin reducir tus 12 horas de estabilidad.",
    "badge_adguard_active": "🟢 AdGuard Activo",
    "badge_adguard_error": "🔴 Error AdGuard",
    "badge_adguard_checking": "🟡 Conectando...",
    "btn_network_equip": "🌐 Equipos de Red ▾",
    "network_menu_title": "Interfaces de Gestión de Red",
    "network_menu_loading": "Cargando equipos...",
    "btn_alerts": "🔔 Alertas",
    "btn_export_import": "💾 Exportar / Importar",
    "btn_columns": "📊 Columnas",
    "btn_static_order": "📌 Orden de Fijadas",
    "btn_mac_hunter": "🔍 Cazador de MAC",
    "mac_hunter_tooltip": "Cazador forense de dispositivos por MAC",
    "btn_settings": "⚙️ Configuraciones (AdGuard / Routers)",
    "user_menu_security": "🔐 Seguridad y contraseña",
    "user_menu_logout_all": "📵 Cerrar sesión en otros dispositivos",
    "user_menu_logout": "🚪 Cerrar sesión",
    "tab_devices": "📱 Dispositivos de Red",
    "tab_services": "🌐 Servicios y Aplicaciones Web",
    "tab_ipmap": "🗺️ Mapa de IPs (1-254)",
    "tab_topology": "🕸️ Topología de Red",
    "tab_timeline": "⏱️ Línea Temporal",
    "tab_wifirf": "⚡ Expulsión Forzosa Wi-Fi",
    "tab_diagnostics": "⚠️ Diagnóstico",
    "card_assign_title": "✏️ Asignar / Cambiar IP Estática",
    "card_assign_hostname": "Nombre del dispositivo (Hostname)",
    "card_assign_hostname_ph": "Ej. enchufe-carga-oukitel",
    "card_assign_mac": "Dirección MAC",
    "card_assign_mac_ph": "a8:80:55:d2:df:80",
    "card_assign_ip": "Dirección IP (192.168.1.X)",
    "card_assign_free_btn": "🔍 Libre",
    "card_assign_force_router": "Forzar por Router / Mesh (DHCPNAK)",
    "card_assign_force_rf": "Expulsión Forzosa por Radiofrecuencia (RF)",
    "card_assign_submit": "Guardar Nombre / Aplicar IP",
    "card_dhcp_title": "Estado del Servidor DHCP",
    "card_dhcp_lease_time": "Tiempo de concesión actual:",
    "card_dhcp_ghosts": "Entradas fantasma (ee:ee:ee:ee:ee:ee):",
    "card_dhcp_expired": "Caducadas:",
    "card_dhcp_stable": "Estable (12 horas)",
    "card_dhcp_1h": "1 hora",
    "card_dhcp_5m": "5 min",
    "card_dhcp_custom": "Personalizado:",
    "card_dhcp_unit_hour": "Hora",
    "card_dhcp_unit_hours": "Horas",
    "card_dhcp_unit_min": "Minutos",
    "card_dhcp_apply": "Aplicar",
    "card_dhcp_purge": "🧹 Purgar Concesiones Fantasma y Caducadas",
    "card_order_title": "📌 Orden de Fijación de IPs",
    "card_order_subtitle": "Histórico cronológico de reservas estáticas fijas en el servidor DHCP",
    "card_order_first": "1ª FIJADA:",
    "card_order_last": "ÚLTIMA FIJADA:",
    "card_order_view_list": "📋 Ver Lista Numerada (1 → N)",
    "card_order_sort_table": "🔢 Ordenar Tabla",
    "search_placeholder": "Buscar por nombre, IP, puerto (ej. 8080, :80, 0123), servicio, MAC...",
    "filter_status_label": "ESTADO:",
    "filter_status_all": "Todos",
    "filter_status_active": "Activos",
    "filter_status_inactive": "Inactivos",
    "filter_medium_label": "MEDIO:",
    "filter_medium_all": "Todos",
    "filter_medium_wifi": "Wi-Fi",
    "filter_medium_cable": "Cable",
    "filter_iptype_label": "TIPO IP:",
    "filter_iptype_all": "Todos",
    "filter_iptype_static": "Fijas",
    "filter_iptype_dynamic": "Dinámicas",
    "filter_order_pct": "% Orden de Fijadas (1 → N)",
    "filter_services_label": "SERVICIOS:",
    "filter_services_all": "Todos",
    "filter_services_active": "Con Servicios Activos",
    "btn_reset_width": "↔ Restablecer Ancho",
    "btn_reset_filters": "✕ Restablecer Filtros",
    "btn_refresh": "🔄 Actualizar",
    "updated_just_now": "Actualizado hace un momento",
    "updated_ago": "Actualizado hace {s} segundos",
    "th_status": "ESTADO",
    "th_hostname": "NOMBRE (HOSTNAME)",
    "th_ip": "DIRECCIÓN IP",
    "th_mac": "DIRECCIÓN MAC",
    "th_vendor": "FABRICANTE / MODELO",
    "th_medium": "MEDIO",
    "th_node": "PUNTO DE CONEXIÓN",
    "th_services": "SERVICIOS WEB / PUERTOS",
    "th_remaining": "TIEMPO RESTANTE",
    "th_traffic": "HISTORIAL / TRÁFICO",
    "th_actions": "ACCIONES",
    "badge_online": "Online",
    "badge_offline": "Offline",
    "badge_static": "Estática",
    "badge_dynamic": "Dinámica",
    "badge_blocked": "Bloqueado",
    "action_edit": "Editar",
    "action_view_sheet": "Ficha Técnica",
    "action_make_static": "Fijar IP",
    "action_release": "Liberar a Dinámica",
    "action_purge": "Purgar Concesión",
    "action_wake_on_lan": "Wake on LAN",
    "action_disconnect": "Expulsar Wi-Fi",
    "no_devices_found": "No se encontraron dispositivos que coincidan con los filtros.",
    "topo_title": "Topología de Red",
    "topo_btn_style": "🎨 Estilo:",
    "topo_btn_plexus": "Efecto Plexus",
    "topo_btn_telemetry": "⚡ Tráfico Real",
    "topo_btn_show_offline": "👁️ Inactivos",
    "topo_btn_auto_organize": "✨ Autoorganizar",
    "topo_btn_fit": "📐 Ajustar Vista",
    "topo_btn_undo": "↺ Deshacer",
    "topo_btn_fullscreen": "🔲 Pantalla Completa",
    "topo_search_placeholder": "Buscar nodo en topología (nombre, IP, MAC)...",
    "topo_exact_match": "Coincidencia exacta",
    "topo_legend_core": "Router / Pasarela",
    "topo_legend_hub": "Punto de Acceso / Mesh",
    "topo_legend_static": "IP Estática",
    "topo_legend_dynamic": "IP Dinámica",
    "topo_legend_offline": "Desconectado",
    "topo_legend_blocked": "Bloqueado",
    "topo_tooltip_drag": "Arrastra libremente para organizar.",
    "topo_tooltip_ctrl_drag": "Ctrl + Arrastre: mueve toda la rama de clientes.",
    "services_title": "Servicios y Aplicaciones Web Detectadas",
    "services_subtitle": "Accesos directos rápidos a los paneles de administración, APIs y servidores web de tu red local.",
    "services_btn_scan_all": "🔍 Escanear Puertos de Toda la Red",
    "services_btn_scan_local": "💻 Escanear Servidor Local (Raspberry)",
    "services_filter_all": "Todos los Servicios",
    "services_filter_web": "Web (80, 443, 8080...)",
    "services_filter_admin": "Paneles de Control",
    "services_filter_db": "Bases de Datos",
    "services_no_services": "No se han detectado servicios web aún. Pulsa en 'Escanear Puertos' para descubrirlos.",
    "ipmap_title": "Mapa Visual de Direcciones IP (1-254)",
    "ipmap_subtitle": "Haz clic en cualquier celda para ver el dispositivo asignado o reservar una IP libre inmediatamente.",
    "ipmap_free": "Libre",
    "ipmap_static": "Estática (Fijada)",
    "ipmap_dynamic": "Dinámica (Lease)",
    "ipmap_gateway": "Puerta de Enlace / Servidor",
    "timeline_title": "Línea Temporal de Eventos de Red",
    "timeline_subtitle": "Registro cronológico en tiempo real de conexiones, desconexiones y cambios de IP.",
    "timeline_btn_clear": "🗑️ Limpiar Historial",
    "timeline_col_time": "HORA",
    "timeline_col_event": "EVENTO",
    "timeline_col_device": "DISPOSITIVO",
    "timeline_col_ip": "IP",
    "timeline_col_mac": "MAC",
    "timeline_no_events": "No hay eventos registrados recientemente.",
    "wifirf_title": "Expulsión Forzosa por Radiofrecuencia (Deautenticación Wi-Fi)",
    "wifirf_subtitle": "Fuerza la desconexión inmediata de dispositivos enviando tramas 802.11 Deauth desde tu adaptador inalámbrico.",
    "wifirf_warning": "⚠️ Utiliza esta función únicamente en tu propia red local para forzar a dispositivos rebeldes a renovar DHCP.",
    "wifirf_col_target": "Dispositivo Destino",
    "wifirf_col_ap": "Punto de Acceso / BSSID",
    "wifirf_col_packets": "Tramas Deauth",
    "wifirf_btn_deauth": "⚡ Expulsar por RF",
    "diag_title": "Diagnóstico y Pruebas de Red",
    "diag_subtitle": "Comprueba la salud de AdGuard Home, latencia de la pasarela y resolución DNS.",
    "diag_btn_run": "🩺 Ejecutar Diagnóstico Completo",
    "diag_ping_gw": "Ping a Pasarela (Router)",
    "diag_dns_res": "Resolución DNS Local",
    "diag_adguard_api": "API AdGuard Home",
    "modal_security_title": "🔐 Seguridad y contraseña",
    "modal_security_user": "Nombre de usuario actual:",
    "modal_security_new_user": "Nuevo nombre de usuario (opcional):",
    "modal_security_new_pass": "Nueva contraseña:",
    "modal_security_confirm_pass": "Confirmar nueva contraseña:",
    "modal_security_save": "Guardar Cambios",
    "modal_security_cancel": "Cancelar",
    "modal_settings_title": "⚙️ Configuraciones del Sistema",
    "modal_settings_adguard": "AdGuard Home",
    "modal_settings_routers": "Routers / Repetidores",
    "modal_settings_mesh": "Red Mesh",
    "modal_settings_ports": "Escaneo de Puertos",
    "modal_settings_ha": "Home Assistant",
    "modal_settings_save": "Guardar Configuraciones",
    "modal_settings_close": "Cerrar",
    "modal_backup_title": "💾 Copias de Seguridad y Migración",
    "modal_backup_export": "Exportar Configuración",
    "modal_backup_export_desc": "Descarga un archivo JSON con todas las asignaciones fijas, apodos y fotos.",
    "modal_backup_btn_download": "📥 Descargar Backup (JSON)",
    "modal_backup_btn_csv": "📊 Exportar a Excel (CSV)",
    "modal_backup_import": "Restaurar Copia de Seguridad",
    "modal_backup_import_desc": "Restaura tus asignaciones e historial desde una copia previa.",
    "modal_backup_btn_restore": "📤 Restaurar Copia",
    "modal_alerts_title": "🔔 Centro de Alertas y Notificaciones",
    "modal_alerts_clear": "Limpiar Todo",
    "modal_alerts_smtp_title": "Notificaciones por Correo (SMTP / Gmail)",
    "modal_alerts_smtp_enable": "Activar alertas por correo electrónico",
    "modal_alerts_smtp_server": "Servidor SMTP (ej. smtp.gmail.com)",
    "modal_alerts_smtp_port": "Puerto SMTP (587 o 465)",
    "modal_alerts_smtp_user": "Usuario / Correo remitente:",
    "modal_alerts_smtp_pass": "Contraseña o App Password:",
    "modal_alerts_smtp_dest": "Correo de destino:",
    "modal_alerts_smtp_test": "✉️ Enviar Correo de Prueba",
    "modal_machunter_title": "🔍 Cazador Forense de Dispositivos por MAC",
    "modal_machunter_subtitle": "Identifica cualquier dirección MAC desconocida consultando bases de datos OUI mundiales y trazas de red.",
    "modal_machunter_placeholder": "Introduce una MAC (ej. a8:80:55:d2:df:80)...",
    "modal_machunter_btn_search": "Buscar Fabricante",
    "modal_machunter_btn_scan": "Escanear Toda la Subred",
    "modal_columns_title": "📊 Visibilidad de Columnas",
    "modal_columns_subtitle": "Marca o desmarca las columnas que deseas visualizar en la tabla de dispositivos.",
    "modal_columns_save": "Guardar Columnas",
    "modal_columns_restore": "Restablecer Predeterminadas",
    "modal_static_order_title": "📌 Histórico Cronológico de Orden de Fijadas",
    "modal_static_order_subtitle": "Listado exacto del orden en que se reservaron las IPs en el servidor DHCP.",
    "modal_static_order_export": "Exportar Listado",
    "msg_ip_assigned": "IP estática asignada con éxito a {dev} ({ip}).",
    "msg_purged_success": "Concesiones fantasma y caducadas purgadas con éxito.",
    "msg_settings_saved": "Configuraciones guardadas correctamente.",
    "msg_backup_restored": "Copia de seguridad restaurada con éxito.",
    "msg_session_expired": "Sesión caducada. Inicia sesión de nuevo.",
    "msg_conn_error": "Error de comunicación con el servidor.",
    "msg_undo_success": "Paso deshecho correctamente.",
    "msg_redo_success": "Paso rehecho correctamente."
},
    en: {
    "header_title": "Direct Static IP Manager — AdGuard Home",
    "header_subtitle": "Reassign static IPs instantly purging previous lease without reducing your 12-hour stability.",
    "badge_adguard_active": "🟢 AdGuard Active",
    "badge_adguard_error": "🔴 AdGuard Error",
    "badge_adguard_checking": "🟡 Connecting...",
    "btn_network_equip": "🌐 Network Devices ▾",
    "network_menu_title": "Network Management Interfaces",
    "network_menu_loading": "Loading devices...",
    "btn_alerts": "🔔 Alerts",
    "btn_export_import": "💾 Export / Import",
    "btn_columns": "📊 Columns",
    "btn_static_order": "📌 Pinning Order",
    "btn_mac_hunter": "🔍 MAC Hunter",
    "mac_hunter_tooltip": "Forensic device investigator by MAC",
    "btn_settings": "⚙️ Settings (AdGuard / Routers)",
    "user_menu_security": "🔐 Security & Password",
    "user_menu_logout_all": "📵 Sign out of other devices",
    "user_menu_logout": "🚪 Sign out",
    "tab_devices": "📱 Network Devices",
    "tab_services": "🌐 Web Services & Apps",
    "tab_ipmap": "🗺️ IP Map (1-254)",
    "tab_topology": "🕸️ Network Topology",
    "tab_timeline": "⏱️ Timeline",
    "tab_wifirf": "⚡ Forced Wi-Fi Disconnect",
    "tab_diagnostics": "⚠️ Diagnostics",
    "card_assign_title": "✏️ Assign / Change Static IP",
    "card_assign_hostname": "Device Name (Hostname)",
    "card_assign_hostname_ph": "E.g. living-room-plug",
    "card_assign_mac": "MAC Address",
    "card_assign_mac_ph": "a8:80:55:d2:df:80",
    "card_assign_ip": "IP Address (192.168.1.X)",
    "card_assign_free_btn": "🔍 Free",
    "card_assign_force_router": "Force via Router / Mesh (DHCPNAK)",
    "card_assign_force_rf": "Forced Radiofrequency Disconnect (RF)",
    "card_assign_submit": "Save Name / Apply IP",
    "card_dhcp_title": "DHCP Server Status",
    "card_dhcp_lease_time": "Current lease time:",
    "card_dhcp_ghosts": "Ghost entries (ee:ee:ee:ee:ee:ee):",
    "card_dhcp_expired": "Expired:",
    "card_dhcp_stable": "Stable (12 hours)",
    "card_dhcp_1h": "1 hour",
    "card_dhcp_5m": "5 min",
    "card_dhcp_custom": "Custom:",
    "card_dhcp_unit_hour": "Hour",
    "card_dhcp_unit_hours": "Hours",
    "card_dhcp_unit_min": "Minutes",
    "card_dhcp_apply": "Apply",
    "card_dhcp_purge": "🧹 Purge Ghost & Expired Leases",
    "card_order_title": "📌 IP Pinning Order",
    "card_order_subtitle": "Chronological history of fixed static reservations in the DHCP server",
    "card_order_first": "1st PINNED:",
    "card_order_last": "LAST PINNED:",
    "card_order_view_list": "📋 View Numbered List (1 → N)",
    "card_order_sort_table": "🔢 Sort Table",
    "search_placeholder": "Search by name, IP, port (e.g. 8080, :80, 0123), service, MAC...",
    "filter_status_label": "STATUS:",
    "filter_status_all": "All",
    "filter_status_active": "Active",
    "filter_status_inactive": "Inactive",
    "filter_medium_label": "MEDIUM:",
    "filter_medium_all": "All",
    "filter_medium_wifi": "Wi-Fi",
    "filter_medium_cable": "Wired",
    "filter_iptype_label": "IP TYPE:",
    "filter_iptype_all": "All",
    "filter_iptype_static": "Static",
    "filter_iptype_dynamic": "Dynamic",
    "filter_order_pct": "% Pinning Order (1 → N)",
    "filter_services_label": "SERVICES:",
    "filter_services_all": "All",
    "filter_services_active": "With Active Services",
    "btn_reset_width": "↔ Reset Width",
    "btn_reset_filters": "✕ Reset Filters",
    "btn_refresh": "🔄 Refresh",
    "updated_just_now": "Updated just now",
    "updated_ago": "Updated {s} seconds ago",
    "th_status": "STATUS",
    "th_hostname": "NAME (HOSTNAME)",
    "th_ip": "IP ADDRESS",
    "th_mac": "MAC ADDRESS",
    "th_vendor": "VENDOR / MODEL",
    "th_medium": "MEDIUM",
    "th_node": "CONNECTION POINT",
    "th_services": "WEB SERVICES / PORTS",
    "th_remaining": "REMAINING TIME",
    "th_traffic": "HISTORY / TRAFFIC",
    "th_actions": "ACTIONS",
    "badge_online": "Online",
    "badge_offline": "Offline",
    "badge_static": "Static",
    "badge_dynamic": "Dynamic",
    "badge_blocked": "Blocked",
    "action_edit": "Edit",
    "action_view_sheet": "Technical Sheet",
    "action_make_static": "Set Static IP",
    "action_release": "Release to Dynamic",
    "action_purge": "Purge Lease",
    "action_wake_on_lan": "Wake on LAN",
    "action_disconnect": "Kick Wi-Fi",
    "no_devices_found": "No devices match the current filters.",
    "topo_title": "Network Topology",
    "topo_btn_style": "🎨 Style:",
    "topo_btn_plexus": "Plexus Effect",
    "topo_btn_telemetry": "⚡ Live Traffic",
    "topo_btn_show_offline": "👁️ Inactive",
    "topo_btn_auto_organize": "✨ Auto-Organize",
    "topo_btn_fit": "📐 Fit View",
    "topo_btn_undo": "↺ Undo",
    "topo_btn_fullscreen": "🔲 Fullscreen",
    "topo_search_placeholder": "Search node in topology (name, IP, MAC)...",
    "topo_exact_match": "Exact match",
    "topo_legend_core": "Router / Gateway",
    "topo_legend_hub": "Access Point / Mesh",
    "topo_legend_static": "Static IP",
    "topo_legend_dynamic": "Dynamic IP",
    "topo_legend_offline": "Disconnected",
    "topo_legend_blocked": "Blocked",
    "topo_tooltip_drag": "Drag freely to reposition.",
    "topo_tooltip_ctrl_drag": "Ctrl + Drag: moves the whole branch of clients.",
    "services_title": "Detected Web Services & Applications",
    "services_subtitle": "Quick shortcuts to local admin dashboards, APIs, and web servers.",
    "services_btn_scan_all": "🔍 Scan Entire Network Ports",
    "services_btn_scan_local": "💻 Scan Local Server (Raspberry)",
    "services_filter_all": "All Services",
    "services_filter_web": "Web (80, 443, 8080...)",
    "services_filter_admin": "Admin Dashboards",
    "services_filter_db": "Databases",
    "services_no_services": "No web services detected yet. Click 'Scan Ports' to discover them.",
    "ipmap_title": "Visual IP Address Map (1-254)",
    "ipmap_subtitle": "Click any cell to inspect the device or assign a free IP immediately.",
    "ipmap_free": "Free",
    "ipmap_static": "Static (Pinned)",
    "ipmap_dynamic": "Dynamic (Leased)",
    "ipmap_gateway": "Gateway / Server",
    "timeline_title": "Network Event Timeline",
    "timeline_subtitle": "Real-time chronological log of connections, disconnections, and IP reassignments.",
    "timeline_btn_clear": "🗑️ Clear History",
    "timeline_col_time": "TIME",
    "timeline_col_event": "EVENT",
    "timeline_col_device": "DEVICE",
    "timeline_col_ip": "IP",
    "timeline_col_mac": "MAC",
    "timeline_no_events": "No network events recorded recently.",
    "wifirf_title": "Forced Radiofrequency Disconnect (802.11 Deauth)",
    "wifirf_subtitle": "Force immediate disconnection of devices by transmitting 802.11 Deauth frames from your wireless adapter.",
    "wifirf_warning": "⚠️ Use this function strictly on your own authorized network to force stubborn devices to renew DHCP.",
    "wifirf_col_target": "Target Device",
    "wifirf_col_ap": "Access Point / BSSID",
    "wifirf_col_packets": "Deauth Frames",
    "wifirf_btn_deauth": "⚡ Kick via RF",
    "diag_title": "Network Health & Diagnostics",
    "diag_subtitle": "Check AdGuard Home status, gateway latency, and DNS resolution.",
    "diag_btn_run": "🩺 Run Full Diagnostics",
    "diag_ping_gw": "Gateway (Router) Ping",
    "diag_dns_res": "Local DNS Resolution",
    "diag_adguard_api": "AdGuard Home API",
    "modal_security_title": "🔐 Security & Password",
    "modal_security_user": "Current username:",
    "modal_security_new_user": "New username (optional):",
    "modal_security_new_pass": "New password:",
    "modal_security_confirm_pass": "Confirm new password:",
    "modal_security_save": "Save Changes",
    "modal_security_cancel": "Cancel",
    "modal_settings_title": "⚙️ System Settings",
    "modal_settings_adguard": "AdGuard Home",
    "modal_settings_routers": "Routers / Extenders",
    "modal_settings_mesh": "Mesh Network",
    "modal_settings_ports": "Port Scanning",
    "modal_settings_ha": "Home Assistant",
    "modal_settings_save": "Save Settings",
    "modal_settings_close": "Close",
    "modal_backup_title": "💾 Backups & Migration",
    "modal_backup_export": "Export Configuration",
    "modal_backup_export_desc": "Download a JSON file containing all fixed static IPs, custom names, and photos.",
    "modal_backup_btn_download": "📥 Download Backup (JSON)",
    "modal_backup_btn_csv": "📊 Export to Excel (CSV)",
    "modal_backup_import": "Restore Backup",
    "modal_backup_import_desc": "Restore your assignments and device history from a previous file.",
    "modal_backup_btn_restore": "📤 Restore Backup",
    "modal_alerts_title": "🔔 Alerts & Notifications Center",
    "modal_alerts_clear": "Clear All",
    "modal_alerts_smtp_title": "Email Notifications (SMTP / Gmail)",
    "modal_alerts_smtp_enable": "Enable email notifications",
    "modal_alerts_smtp_server": "SMTP Server (e.g. smtp.gmail.com)",
    "modal_alerts_smtp_port": "SMTP Port (587 or 465)",
    "modal_alerts_smtp_user": "Sender Email / User:",
    "modal_alerts_smtp_pass": "Password or App Password:",
    "modal_alerts_smtp_dest": "Recipient Email:",
    "modal_alerts_smtp_test": "✉️ Send Test Email",
    "modal_machunter_title": "🔍 Forensic MAC Device Hunter",
    "modal_machunter_subtitle": "Identify unknown MAC addresses by querying worldwide OUI databases and local ARP traces.",
    "modal_machunter_placeholder": "Enter a MAC address (e.g. a8:80:55:d2:df:80)...",
    "modal_machunter_btn_search": "Search Vendor",
    "modal_machunter_btn_scan": "Scan Entire Subnet",
    "modal_columns_title": "📊 Column Visibility",
    "modal_columns_subtitle": "Check or uncheck the columns you want displayed in the network devices table.",
    "modal_columns_save": "Save Columns",
    "modal_columns_restore": "Restore Defaults",
    "modal_static_order_title": "📌 Chronological IP Pinning Order",
    "modal_static_order_subtitle": "Exact chronological order in which static IP reservations were pinned in the DHCP server.",
    "modal_static_order_export": "Export List",
    "msg_ip_assigned": "Static IP assigned successfully to {dev} ({ip}).",
    "msg_purged_success": "Ghost and expired leases purged successfully.",
    "msg_settings_saved": "Settings saved successfully.",
    "msg_backup_restored": "Backup restored successfully.",
    "msg_session_expired": "Session expired. Please log in again.",
    "msg_conn_error": "Communication error with the server.",
    "msg_undo_success": "Action undone successfully.",
    "msg_redo_success": "Action redone successfully."
}
};

// Idioma activo (por defecto 'es', o el guardado en localStorage)
window.currentLang = localStorage.getItem('ag_panel_lang') || 'es';

/**
 * Obtener texto traducido por clave
 */
window.t = function(key, fallback = '') {
    const lang = window.currentLang || 'es';
    if (TRANSLATIONS[lang] && TRANSLATIONS[lang][key] !== undefined) {
        return TRANSLATIONS[lang][key];
    }
    if (TRANSLATIONS['es'] && TRANSLATIONS['es'][key] !== undefined) {
        return TRANSLATIONS['es'][key];
    }
    return fallback || key;
};

/**
 * Desplegable de idiomas en la cabecera
 */
window.toggleLangMenu = function(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const menu = document.getElementById('lang-menu-dropdown');
    if (!menu) return;
    const isHidden = menu.style.display === 'none' || !menu.style.display;
    document.querySelectorAll('.dropdown-menu-custom').forEach(d => d.style.display = 'none');
    menu.style.display = isHidden ? 'block' : 'none';
};

// Cerrar desplegables al hacer clic fuera
document.addEventListener('click', function(e) {
    const langWrapper = document.getElementById('lang-selector-wrapper');
    if (langWrapper && !langWrapper.contains(e.target)) {
        const menu = document.getElementById('lang-menu-dropdown');
        if (menu) menu.style.display = 'none';
    }
});

/**
 * Cambiar idioma activo de toda la aplicación
 */
window.setLanguage = function(lang, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (lang !== 'es' && lang !== 'en') lang = 'es';
    window.currentLang = lang;
    try {
        localStorage.setItem('ag_panel_lang', lang);
    } catch (e) {}

    document.documentElement.lang = lang;

    // Actualizar etiqueta del botón selector
    const label = document.getElementById('current-lang-label');
    if (label) {
        label.textContent = (lang === 'en') ? '🇬🇧 EN' : '🇪🇸 ES';
    }

    const menu = document.getElementById('lang-menu-dropdown');
    if (menu) menu.style.display = 'none';

    // Aplicar traducciones en todos los elementos marcados con data-i18n
    window.applyTranslations(lang);

    // Re-renderizar componentes dinámicos
    if (typeof renderTable === 'function') renderTable();
    if (typeof updateRefreshTimestamp === 'function') updateRefreshTimestamp();
    if (typeof updateStaticOrderWidgets === 'function') updateStaticOrderWidgets();
    if (typeof updateTopoLegendUI === 'function') updateTopoLegendUI();
    if (typeof renderServicesCards === 'function') renderServicesCards();
    if (typeof renderTimelineRows === 'function') renderTimelineRows();
    if (typeof renderIpMap === 'function') renderIpMap();
    if (typeof renderGlobalNetworkMenu === 'function') renderGlobalNetworkMenu();

    if (typeof showMessage === 'function') {
        const toastMsg = (lang === 'en') 
            ? 'Language changed to English.' 
            : 'Idioma cambiado a Español.';
        showMessage(toastMsg);
    }
};

/**
 * Recorrer el DOM y traducir todos los elementos data-i18n
 */
window.applyTranslations = function(lang) {
    if (!lang) lang = window.currentLang || 'es';
    const dict = TRANSLATIONS[lang] || TRANSLATIONS['es'];

    // 1. Textos directos
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key] !== undefined) {
            // Preservar insignias o contadores hijos si existen
            const badge = el.querySelector('.badge, .tab-badge');
            if (badge) {
                const badgeHtml = badge.outerHTML;
                el.innerHTML = dict[key] + ' ' + badgeHtml;
            } else {
                el.innerHTML = dict[key];
            }
        }
    });

    // 2. Placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key] !== undefined) {
            el.placeholder = dict[key];
        }
    });

    // 3. Títulos / Tooltips
    document.querySelectorAll('[data-i18n-title]').forEach(el => {
        const key = el.getAttribute('data-i18n-title');
        if (dict[key] !== undefined) {
            el.title = dict[key];
        }
    });
};

// Ejecutar al cargar el documento
document.addEventListener('DOMContentLoaded', function() {
    const savedLang = localStorage.getItem('ag_panel_lang') || 'es';
    const label = document.getElementById('current-lang-label');
    if (label) {
        label.textContent = (savedLang === 'en') ? '🇬🇧 EN' : '🇪🇸 ES';
    }
    window.applyTranslations(savedLang);
});
