/**
 * Diccionario Internacional de Traducciones (i18n)
 * Gestor Directo de IPs Estáticas — AdGuard Home
 * 
 * Idiomas soportados:
 *   - 'es': Español (Nativo)
 *   - 'en': English (100% Complete)
 */
const TRANSLATIONS = {
    "es": {
        "header_title": "Gestor Directo de IPs Estáticas — AdGuard Home",
        "header_subtitle": "Reasigna IPs estáticas purgando la concesión previa al instante sin reducir tus 12 horas de estabilidad.",
        "badge_adguard_active": "🟢 AdGuard Activo",
        "badge_adguard_error": "🔴 Error AdGuard",
        "badge_adguard_checking": "🟡 Conectando...",
        "badge_adguard_title": "Comprobando conexión con AdGuard Home...",
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
        "user_menu_security": "🔑 Seguridad y contraseña",
        "user_menu_logout_all": "📵 Cerrar sesión en otros dispositivos",
        "user_menu_logout": "🚪 Cerrar sesión",
        "user_menu_title": "Sesión y seguridad",
        "lang_selector_title": "Cambiar idioma / Change language",
        "tab_devices": "📱 Dispositivos de Red",
        "tab_services": "🌐 Servicios y Aplicaciones Web",
        "tab_ipmap": "🗺️ Mapa de IPs (1-254)",
        "tab_topology": "🕸️ Topología de Red",
        "tab_timeline": "⏱️ Línea Temporal",
        "tab_wifirf": "⚡ Expulsión Forzosa Wi-Fi",
        "tab_diagnostics": "⚠️ Diagnóstico",
        "tab_drag_hint": "Arrastra para reordenar esta pestaña",
        "card_assign_title": "✏️ Asignar / Cambiar IP Estática",
        "card_assign_hostname": "Nombre del dispositivo (Hostname)",
        "card_assign_hostname_ph": "Ej. enchufe-carga-oukitel",
        "card_assign_mac": "Dirección MAC",
        "card_assign_mac_ph": "a8:80:55:d2:df:80",
        "card_assign_ip": "Dirección IP (192.168.1.X)",
        "card_assign_ip_ph": "192.168.1.X",
        "card_assign_free_btn": "🔍 Libre",
        "card_assign_free_btn_title": "Sugerir automáticamente la siguiente IP fija libre fuera del pool DHCP",
        "card_assign_force_router": "Forzar por Router / Mesh (DHCPNAK)",
        "card_assign_force_router_title": "Envía un paquete DHCPNAK por red local y solicita desasociación al Router o nodos Mesh si está soportado",
        "card_assign_force_rf": "Expulsión Forzosa por Radiofrecuencia (RF)",
        "card_assign_force_rf_title": "Envía tramas de desautenticación WiFi 802.11 por el aire usando la antena monitor de la Raspberry Pi",
        "card_assign_submit": "Guardar Nombre / Aplicar IP",
        "card_dhcp_title": "Estado del Servidor DHCP",
        "card_dhcp_lease_time": "Tiempo de concesión actual:",
        "card_dhcp_ghosts": "Entradas fantasma (ee:ee:ee:ee:ee:ee):",
        "card_dhcp_expired": "Caducadas:",
        "card_dhcp_stable": "Estable IoT (12 horas)",
        "card_dhcp_1h": "1 hora",
        "card_dhcp_5m": "5 min",
        "card_dhcp_custom": "Personalizado:",
        "card_dhcp_unit_min": "Min",
        "card_dhcp_unit_hours": "Horas",
        "card_dhcp_unit_days": "Días",
        "card_dhcp_apply_btn": "⚡ Aplicar",
        "card_dhcp_apply_btn_title": "Aplicar tiempo de concesión personalizado",
        "card_dhcp_clean_btn": "🧹 Purgar Concesiones Fantasma y Caducadas",
        "card_static_order_title": "📌 Orden de Asignación Fija",
        "card_static_order_desc": "Secuencia cronológica en la que se fijaron tus IPs estáticas en AdGuard Home:",
        "card_static_order_first": "🥇 1ª Fijada:",
        "card_static_order_last": "🏁 Última Fijada:",
        "card_static_order_btn_view": "📋 Ver y Editar Orden Completo",
        "card_static_order_btn_sort": "🔢 Ordenar Tabla por este Orden",
        "search_placeholder": "Buscar por nombre, IP, puerto (ej: 8086, :80, 8123), servicio, MAC...",
        "lbl_table_width_expand": "Ampliar Ancho",
        "lbl_table_width_standard": "Ancho Estándar",
        "btn_table_width_title": "Ampliar la caja de la tabla horizontalmente a pantalla ancha o restaurar",
        "btn_reset_filters": "🔄 Restablecer Filtros",
        "btn_refresh_text": "Actualizar",
        "btn_refresh_title": "Actualizar inmediatamente dispositivos y puertos",
        "last_updated_just_now": "Actualizado hace un momento",
        "filter_status_label": "Estado:",
        "filter_status_all": "Todos",
        "filter_status_online": "🟢 Activos",
        "filter_status_offline": "⚪ Inactivos",
        "filter_medium_label": "Medio:",
        "filter_medium_all": "Todos",
        "filter_medium_wifi": "📶 Wi-Fi",
        "filter_medium_cable": "🔌 Cable",
        "filter_type_label": "Tipo IP:",
        "filter_type_all": "Todos",
        "filter_type_static": "📌 Fijas",
        "filter_type_dynamic": "⏳ Dinámicas",
        "filter_static_order_btn": "🔢 Orden Fijadas",
        "filter_static_order_title": "Ordenar la tabla por orden cronológico de fijación (#1 primera fijada, #N última)",
        "filter_services_label": "Servicios:",
        "filter_services_all": "Todos",
        "filter_services_active": "🌐 Con Servicios Activos",
        "col_hostname": "Dispositivo",
        "col_prediction": "Predicción / Clase",
        "col_hunter": "Cazador / HA",
        "col_medium": "Medio",
        "col_router": "Router / Conexión",
        "col_ip": "IP en AdGuard",
        "col_arp": "IP Activa (ARP)",
        "col_latency": "Latencia / SO",
        "col_seen": "Visto / Ubicación",
        "col_mac": "MAC",
        "col_type": "Tipo / Nº Fija",
        "col_actions": "Acciones",
        "badge_online": "Conectado",
        "badge_offline": "Desconectado",
        "badge_static": "Estática",
        "badge_dynamic": "Dinámica",
        "badge_dynamic_expired": "Dinámica (Caducada)",
        "badge_blocked": "Bloqueado",
        "badge_pending_dhcp": "Pendiente DHCP",
        "tip_pending_dhcp": "Pendiente de renovación DHCP",
        "tip_static_reservation": "Reserva fija en AdGuard",
        "tip_no_dhcp_request": "El dispositivo todavía no ha solicitado concesión DHCP con la nueva IP",
        "btn_edit": "Editar",
        "btn_edit_fix": "Editar / Fijar",
        "btn_fix_ip": "Fijar IP",
        "btn_deauth_rf": "Expulsar (RF)",
        "btn_release_ip": "Liberar",
        "btn_block_dns": "Bloquear",
        "btn_unblock_dns": "Desbloquear",
        "btn_device_sheet": "📄 Ficha",
        "btn_locate_topo": "🗺️ Mapa",
        "btn_watch_alert": "🔔 Avisar",
        "btn_ping": "⚡ Ping",
        "btn_delete_lease": "Borrar",
        "no_devices_found": "No se encontraron dispositivos con los filtros seleccionados.",
        "svc_subtab_lan": "🌐 Servicios de Red (LAN)",
        "svc_subtab_localhost": "💻 Servicios Locales (Host)",
        "svc_search_placeholder": "Buscar servicio por nombre, puerto (ej: 8086, :8123), descripción, IP o host...",
        "svc_filter_all": "Todos",
        "svc_filter_http": "🌐 Web / HTTP",
        "svc_filter_domotica": "🏠 Domótica & IoT",
        "svc_filter_infra": "⚙️ Infraestructura",
        "svc_filter_multimedia": "🎬 Multimedia",
        "svc_filter_up": "🟢 Activos",
        "svc_filter_down": "🔴 Caídos",
        "svc_filter_local_only": "🔒 Solo Local (127.0.0.1)",
        "svc_filter_lan_only": "🌐 Red LAN (0.0.0.0)",
        "svc_btn_open": "Abrir Servicio",
        "svc_btn_edit": "Personalizar",
        "svc_empty": "No se han detectado servicios web con los filtros seleccionados.",
        "ipmap_title": "🗺️ Mapa Visual de Subred",
        "ipmap_desc": "Visualización en cuadrícula de las 254 direcciones IP posibles de tu red local.",
        "ipmap_legend_free": "Libre",
        "ipmap_legend_static": "Estática activa",
        "ipmap_legend_dynamic": "Dinámica",
        "ipmap_legend_manual": "Manual fuera DHCP",
        "ipmap_legend_conflict": "Conflicto",
        "ipmap_legend_dhcp_range": "Borde inferior ámbar = Rango dinámico DHCP",
        "topo_search_ph": "Buscar nodo, host, IP o MAC...",
        "topo_btn_exact": "Exacto",
        "topo_btn_exact_title": "Alternar coincidencia exacta de IP / Host / MAC",
        "topo_btn_options": "📱 Opciones",
        "topo_btn_autoorganize_title": "Auto-organizar topología equilibradamente",
        "topo_btn_cascade_title": "Disparar onda de sinapsis neuronal",
        "topo_btn_style": "Estilo:",
        "topo_style_plexus": "Zigzag Flotante",
        "topo_style_straight": "Líneas Rectas",
        "topo_style_synapse": "Impulsos Rayo",
        "topo_mesh_title": "Configuración de la tela de araña: Entramado (-/+), Tono y Opacidad",
        "topo_telemetry_title": "Alternar entre impulsos ambientales simulados o flujo continuo de Tráfico Real DNS + Ping",
        "topo_telemetry_label": "Lógica:",
        "topo_telemetry_sim": "Simulada",
        "topo_telemetry_real": "Tráfico Real",
        "topo_freq_title": "Frecuencia y velocidad de impulsos (- / +)",
        "topo_fx_title": "Activar/desactivar animación flotante",
        "topo_offline_title": "Mostrar u ocultar inactivos",
        "topo_label_title": "Texto mostrado en los nodos",
        "topo_label_name": "Nombre",
        "topo_label_name_ip": "Nombre + IP",
        "topo_label_mac": "MAC",
        "topo_fit_title": "Centrar y encuadrar mapa",
        "topo_cards_title": "Mostrar/ocultar listado de tarjetas",
        "topo_export_title": "Descargar posiciones JSON",
        "topo_import_title": "Restaurar posiciones JSON",
        "topo_reset_box_title": "Restablecer la caja al ancho y centrado original",
        "topo_fullscreen_title": "Pantalla completa (F)",
        "topo_shortcuts_hint": "Atajos: Ctrl+Z revertir / Ctrl+Y rehacer / Ctrl+Arrastrar mueve solo el nodo",
        "topo_legend_core": "Router Principal / Core",
        "topo_legend_ap": "APs / Nodos Mesh",
        "topo_legend_static": "Fijas activas",
        "topo_legend_dynamic": "Dinámicas",
        "topo_legend_offline": "Inactivos",
        "topo_legend_controls": "🖱️ Rueda: Zoom · Arrastrar: Mover · Clic: Ficha",
        "timeline_title": "⏱️ Línea Temporal de Presencia",
        "timeline_desc": "Tramos en verde = conectado. Ideal para detectar desconexiones nocturnas o microcortes en dispositivos IoT.",
        "timeline_search_ph": "Filtrar dispositivo...",
        "timeline_btn_6h": "6h",
        "timeline_btn_24h": "24h",
        "timeline_btn_72h": "3 días",
        "timeline_btn_168h": "7 días",
        "wifirf_title": "Expulsión Forzosa por Radiofrecuencia (Wi-Fi 802.11 Deauth)",
        "wifirf_btn_refresh_diag": "🔄 Actualizar Diagnóstico",
        "wifirf_btn_disable_plugin": "❌ Desactivar Plugin",
        "wifirf_btn_install": "Instalar Herramientas (aircrack-ng, iw)",
        "wifirf_btn_monitor": "Activar Modo Monitor",
        "wifirf_btn_normal": "Volver a Modo Normal",
        "wifirf_btn_scan": "Escanear Redes Wi-Fi en el Aire",
        "wifirf_filter_label": "Filtrar:",
        "wifirf_filter_my_net": "🏠 Solo mi Red",
        "wifirf_filter_all": "📡 Todos en el aire",
        "wifirf_auto_bssid_lbl": "BSSID del Router / Punto de Acceso (MAC AP):",
        "wifirf_auto_client_lbl": "MAC del Cliente Objetivo:",
        "wifirf_btn_auto_deauth": "⚡ Expulsar Inmediatamente (Auto)",
        "wifirf_manual_bssid_lbl": "BSSID del Router / AP:",
        "wifirf_manual_client_lbl": "MAC Cliente:",
        "wifirf_manual_channel_lbl": "Canal:",
        "wifirf_btn_manual_deauth": "🔥 Lanzar Ráfaga Manual",
        "wifirf_terminal_title": "📟 Terminal de Diagnóstico Wi-Fi (RF)",
        "wifirf_terminal_clear": "Limpiar Salida",
        "diag_title": "⚠️ Diagnóstico Automático de Red y DHCP",
        "diag_desc": "Analiza conflictos de IP en ARP, reservas estáticas dentro del pool DHCP, servicios caídos, MACs aleatorias y concesiones huérfanas.",
        "diag_btn_scan": "🔍 Analizar Ahora",
        "ds_title": "Ficha de Dispositivo",
        "ds_btn_watch": "🔔 Aviso Conexión",
        "ds_btn_watch_title": "Recibir un correo electrónico cuando este dispositivo se conecte a la red",
        "ds_btn_export": "📥 Exportar Ficha",
        "ds_btn_export_title": "Descargar copia JSON de este dispositivo",
        "ds_btn_import": "📤 Importar Ficha",
        "ds_btn_import_title": "Restaurar configuración JSON para este dispositivo",
        "ds_btn_delete": "🗑️ Eliminar Ficha",
        "ds_btn_delete_title": "Eliminar reserva fija de AdGuard Home y purgar ficha",
        "ds_act_forensic": "🔍 Análisis Forense",
        "ds_act_unblock_dns": "🟢 Desbloquear Internet (DNS)",
        "ds_act_block_dns": "🔴 Cortar Internet (Bloquear DNS)",
        "ds_act_wol": "⚡ Wake-on-LAN (Encender)",
        "ds_act_ping": "📶 Hacer Ping",
        "ds_act_edit_dhcp": "✏️ Editar Concesión DHCP",
        "photo_modal_title": "Foto del Dispositivo",
        "photo_modal_desc": "Opciones para cambiar o actualizar la imagen:",
        "photo_btn_camera": "Hacer Foto (Usar Cámara)",
        "photo_btn_apps": "Elegir App (Google Fotos, Archivos, Drive...)",
        "photo_btn_apps_title": "Muestra el menú del smartphone con todas las aplicaciones disponibles",
        "photo_btn_gallery": "Galería Multimedia del Smartphone",
        "photo_btn_delete": "Eliminar Foto Actual",
        "photo_btn_cancel": "Cancelar",
        "settings_title": "⚙️ Configuraciones de AdGuard Home y Routers / Puntos de Acceso",
        "settings_wifi_plugin_enable": "Activar Expulsión Forzosa Wi-Fi",
        "settings_ag_url": "URL de AdGuard Home",
        "settings_ag_user": "Usuario de AdGuard Home",
        "settings_ag_pass": "Contraseña de AdGuard Home",
        "settings_routers_discover": "🔍 Autodetectar Routers en la Red",
        "settings_routers_discover_title": "Escanear la red local para identificar routers/puntos de acceso automáticamente",
        "settings_routers_add": "➕ Añadir Nuevo Router / AP",
        "settings_ha_enable": "Activar Plugin Home Assistant",
        "settings_localhost_enable": "Detectar Servicios Locales (localhost:puerto)",
        "settings_localhost_title": "Escanea y muestra en la barra superior los puertos y aplicaciones en escucha en este ordenador",
        "settings_ha_title": "Instancias de Home Assistant Configuradas",
        "settings_ha_discover": "🔍 Autodetectar en la Red",
        "settings_ha_add": "➕ Añadir Instancia",
        "settings_btn_save": "💾 Guardar y Probar Configuración",
        "settings_btn_close": "Cerrar",
        "sec_title": "🔑 Seguridad y contraseña",
        "sec_user": "Usuario",
        "sec_new_pass": "Nueva contraseña (vacío = no cambiar)",
        "sec_repeat_pass": "Repite la nueva contraseña",
        "sec_curr_pass": "Contraseña actual *",
        "sec_btn_cancel": "Cancelar",
        "sec_btn_save": "💾 Guardar",
        "rename_title": "Personalizar Nombre de Servicio",
        "rename_host": "Dispositivo host:",
        "rename_original": "Detectado original:",
        "rename_custom_lbl": "Nombre personalizado:",
        "rename_ph": "Ej. InfluxDB, Node-RED, Mi Domótica...",
        "rename_btn_reset": "Quitar nombre personalizado y volver al original",
        "rename_btn_cancel": "Cancelar",
        "rename_btn_save": "💾 Guardar Nombre",
        "columns_title": "📊 Personalizar Columnas y Pestañas",
        "columns_reset_tabs": "Restablecer Pestañas",
        "columns_reset_tabs_title": "Restablecer el orden original de las pestañas principales",
        "columns_reset_cols": "Restablecer Columnas",
        "columns_reset_cols_title": "Restablecer visibilidad y orden de columnas",
        "columns_desc": "Activa, desactiva o arrastra para ordenar las columnas de la tabla y las pestañas superiores.",
        "alerts_title": "🔔 Configuración de Alertas y Notificaciones",
        "alerts_tab_email": "Correo Electrónico (Gmail SMTP)",
        "alerts_tab_webhooks": "Webhooks y Bots (Telegram / Discord / ntfy)",
        "alerts_tab_events": "Eventos Notificables",
        "alerts_email_user": "Tu cuenta de Gmail (remitente)",
        "alerts_email_pass": "Contraseña de Aplicación (16 letras)",
        "alerts_email_pass_link": "Obtener ↗",
        "alerts_email_to": "Correo Destinatario (donde recibir avisos)",
        "alerts_email_host": "Servidor SMTP / Puerto",
        "alerts_email_new_dev": "Enviar email al conectarse un nuevo dispositivo a la red",
        "alerts_email_dev_connect": "Enviar email cuando cualquier dispositivo se reconecte",
        "alerts_btn_test_smtp": "📧 Probar Envío de Correo Ahora",
        "alerts_ntfy_url": "URL ntfy (ej. https://ntfy.sh/mi-red)",
        "alerts_tg_token": "Telegram Bot Token",
        "alerts_tg_chat": "Telegram Chat ID",
        "alerts_webhook": "Webhook URL (Home Assistant / Discord)",
        "alerts_ev_new_dev": "Nuevo dispositivo en la red",
        "alerts_ev_connect": "Dispositivo inicia sesión / se conecta",
        "alerts_ev_svc_down": "Servicio web caído (tras 10 min caído)",
        "alerts_ev_svc_up": "Servicio web recuperado",
        "alerts_ev_watched": "Dispositivo vigilado desconectado",
        "alerts_watched_macs": "MACs vigiladas (separadas por coma — avisa si se desconectan)",
        "alerts_btn_test": "🔔 Enviar Alerta de Prueba",
        "alerts_btn_save": "💾 Guardar Alertas",
        "backup_title": "💾 Exportar e Importar Configuración / Copias",
        "backup_desc": "Guarda todas las IPs estáticas de AdGuard, routers, nombres de servicios personalizados, favoritos, notas/habitaciones y alertas.",
        "backup_inc_secrets": "Incluir contraseñas de routers/AdGuard y tokens en el JSON",
        "backup_btn_download_json": "📥 Descargar Copia Completa (.JSON)",
        "backup_btn_export_csv": "📊 Exportar Tabla a Excel (.CSV)",
        "backup_import_title": "Restaurar Copia de Seguridad",
        "backup_import_desc": "Restaura tu configuración desde un archivo .JSON o .ZIP exportado previamente.",
        "order_modal_title": "📌 Secuencia Cronológica de Fijación de IPs",
        "order_modal_desc": "Visualiza y gestiona la secuencia cronológica en la que se fijaron tus IPs estáticas en AdGuard Home.",
        "order_modal_btn_close": "Cerrar",
        "hunter_title": "🔍 Cazador Forense de Dispositivos por MAC",
        "hunter_desc": "Rastrea en tiempo real la presencia física de cualquier MAC en switches, routers y antenas Wi-Fi.",
        "hunter_search_ph": "Introduce dirección MAC a rastrear...",
        "hunter_btn_search": "Rastrear MAC",
        "btn_close": "Cerrar",
        "btn_cancel": "Cancelar",
        "btn_save": "Guardar",
        "btn_apply": "Aplicar",
        "btn_delete": "Eliminar",
        "btn_accept": "Aceptar",
        "popup_info_title": "Información",
        "popup_confirm_title": "Confirmación"
    },
    "en": {
        "header_title": "Direct Static IP Manager — AdGuard Home",
        "header_subtitle": "Reassign static IPs by instantly purging the prior lease without reducing your 12-hour stability.",
        "badge_adguard_active": "🟢 AdGuard Active",
        "badge_adguard_error": "🔴 AdGuard Error",
        "badge_adguard_checking": "🟡 Connecting...",
        "badge_adguard_title": "Checking connection with AdGuard Home...",
        "btn_network_equip": "🌐 Network Devices ▾",
        "network_menu_title": "Network Management Interfaces",
        "network_menu_loading": "Loading devices...",
        "btn_alerts": "🔔 Alerts",
        "btn_export_import": "💾 Export / Import",
        "btn_columns": "📊 Columns",
        "btn_static_order": "📌 Static Order",
        "btn_mac_hunter": "🔍 MAC Hunter",
        "mac_hunter_tooltip": "Forensic device hunter by MAC",
        "btn_settings": "⚙️ Settings (AdGuard / Routers)",
        "user_menu_security": "🔑 Security & Password",
        "user_menu_logout_all": "📵 Log out other devices",
        "user_menu_logout": "🚪 Log out",
        "user_menu_title": "Session and security",
        "lang_selector_title": "Change language / Cambiar idioma",
        "tab_devices": "📱 Network Devices",
        "tab_services": "🌐 Web Services & Apps",
        "tab_ipmap": "🗺️ IP Map (1-254)",
        "tab_topology": "🕸️ Network Topology",
        "tab_timeline": "⏱️ Presence Timeline",
        "tab_wifirf": "⚡ Wi-Fi Force Deauth",
        "tab_diagnostics": "⚠️ Diagnostics",
        "tab_drag_hint": "Drag to reorder this tab",
        "card_assign_title": "✏️ Assign / Change Static IP",
        "card_assign_hostname": "Device Name (Hostname)",
        "card_assign_hostname_ph": "E.g. livingroom-smart-plug",
        "card_assign_mac": "MAC Address",
        "card_assign_mac_ph": "a8:80:55:d2:df:80",
        "card_assign_ip": "IP Address (192.168.1.X)",
        "card_assign_ip_ph": "192.168.1.X",
        "card_assign_free_btn": "🔍 Free",
        "card_assign_free_btn_title": "Automatically suggest the next free static IP outside the DHCP pool",
        "card_assign_force_router": "Force via Router / Mesh (DHCPNAK)",
        "card_assign_force_router_title": "Sends a DHCPNAK packet over the local network and requests disassociation from the Router or Mesh nodes if supported",
        "card_assign_force_rf": "Radiofrequency Force Deauth (RF)",
        "card_assign_force_rf_title": "Sends 802.11 Wi-Fi deauth frames over the air using Raspberry Pi monitor antenna",
        "card_assign_submit": "Save Name / Apply IP",
        "card_dhcp_title": "DHCP Server Status",
        "card_dhcp_lease_time": "Current lease time:",
        "card_dhcp_ghosts": "Ghost entries (ee:ee:ee:ee:ee:ee):",
        "card_dhcp_expired": "Expired:",
        "card_dhcp_stable": "Stable IoT (12 hours)",
        "card_dhcp_1h": "1 hour",
        "card_dhcp_5m": "5 min",
        "card_dhcp_custom": "Custom:",
        "card_dhcp_unit_min": "Mins",
        "card_dhcp_unit_hours": "Hours",
        "card_dhcp_unit_days": "Days",
        "card_dhcp_apply_btn": "⚡ Apply",
        "card_dhcp_apply_btn_title": "Apply custom lease time",
        "card_dhcp_clean_btn": "🧹 Purge Ghost and Expired Leases",
        "card_static_order_title": "📌 Static Assignment Order",
        "card_static_order_desc": "Chronological sequence in which your static IPs were fixed in AdGuard Home:",
        "card_static_order_first": "🥇 1st Static:",
        "card_static_order_last": "🏁 Last Static:",
        "card_static_order_btn_view": "📋 View and Edit Full Order",
        "card_static_order_btn_sort": "🔢 Sort Table by this Order",
        "search_placeholder": "Search by name, IP, port (e.g.: 8086, :80, 8123), service, MAC...",
        "lbl_table_width_expand": "Expand Width",
        "lbl_table_width_standard": "Standard Width",
        "btn_table_width_title": "Expand the table box horizontally to widescreen or restore",
        "btn_reset_filters": "🔄 Reset Filters",
        "btn_refresh_text": "Refresh",
        "btn_refresh_title": "Immediately refresh devices and ports",
        "last_updated_just_now": "Updated just now",
        "filter_status_label": "Status:",
        "filter_status_all": "All",
        "filter_status_online": "🟢 Active",
        "filter_status_offline": "⚪ Inactive",
        "filter_medium_label": "Medium:",
        "filter_medium_all": "All",
        "filter_medium_wifi": "📶 Wi-Fi",
        "filter_medium_cable": "🔌 Cable",
        "filter_type_label": "IP Type:",
        "filter_type_all": "All",
        "filter_type_static": "📌 Static",
        "filter_type_dynamic": "⏳ Dynamic",
        "filter_static_order_btn": "🔢 Static Order",
        "filter_static_order_title": "Sort table chronologically by fixation order (#1 first fixed, #N last)",
        "filter_services_label": "Services:",
        "filter_services_all": "All",
        "filter_services_active": "🌐 With Active Services",
        "col_hostname": "Device",
        "col_prediction": "Prediction / Class",
        "col_hunter": "Hunter / HA",
        "col_medium": "Medium",
        "col_router": "Router / Connection",
        "col_ip": "IP in AdGuard",
        "col_arp": "Active IP (ARP)",
        "col_latency": "Latency / OS",
        "col_seen": "Seen / Location",
        "col_mac": "MAC",
        "col_type": "Type / Static #",
        "col_actions": "Actions",
        "badge_online": "Connected",
        "badge_offline": "Offline",
        "badge_static": "Static",
        "badge_dynamic": "Dynamic",
        "badge_dynamic_expired": "Dynamic (Expired)",
        "badge_blocked": "Blocked",
        "badge_pending_dhcp": "Pending DHCP",
        "tip_pending_dhcp": "Pending DHCP renewal",
        "tip_static_reservation": "Static reservation in AdGuard",
        "tip_no_dhcp_request": "Device has not yet requested DHCP lease with new IP",
        "btn_edit": "Edit",
        "btn_edit_fix": "Edit / Fix",
        "btn_fix_ip": "Fix IP",
        "btn_deauth_rf": "Deauth (RF)",
        "btn_release_ip": "Release",
        "btn_block_dns": "Block",
        "btn_unblock_dns": "Unblock",
        "btn_device_sheet": "📄 Details",
        "btn_locate_topo": "🗺️ Map",
        "btn_watch_alert": "🔔 Alert",
        "btn_ping": "⚡ Ping",
        "btn_delete_lease": "Delete",
        "no_devices_found": "No devices found matching the selected filters.",
        "svc_subtab_lan": "🌐 Network Services (LAN)",
        "svc_subtab_localhost": "💻 Localhost Services (Host)",
        "svc_search_placeholder": "Search service by name, port (e.g.: 8086, :8123), description, IP or host...",
        "svc_filter_all": "All",
        "svc_filter_http": "🌐 Web / HTTP",
        "svc_filter_domotica": "🏠 Smart Home & IoT",
        "svc_filter_infra": "⚙️ Infrastructure",
        "svc_filter_multimedia": "🎬 Multimedia",
        "svc_filter_up": "🟢 Online",
        "svc_filter_down": "🔴 Offline",
        "svc_filter_local_only": "🔒 Local Only (127.0.0.1)",
        "svc_filter_lan_only": "🌐 LAN Network (0.0.0.0)",
        "svc_btn_open": "Open Service",
        "svc_btn_edit": "Customize",
        "svc_empty": "No web services detected with the selected filters.",
        "ipmap_title": "🗺️ Subnet Visual Map",
        "ipmap_desc": "Grid overview of all 254 possible IP addresses on your local network.",
        "ipmap_legend_free": "Free",
        "ipmap_legend_static": "Active Static",
        "ipmap_legend_dynamic": "Dynamic",
        "ipmap_legend_manual": "Manual outside DHCP",
        "ipmap_legend_conflict": "Conflict",
        "ipmap_legend_dhcp_range": "Amber bottom border = DHCP dynamic range",
        "topo_search_ph": "Search node, host, IP or MAC...",
        "topo_btn_exact": "Exact",
        "topo_btn_exact_title": "Toggle exact match for IP / Host / MAC",
        "topo_btn_options": "📱 Options",
        "topo_btn_autoorganize_title": "Auto-organize topology evenly",
        "topo_btn_cascade_title": "Trigger neural synapse cascade",
        "topo_btn_style": "Style:",
        "topo_style_plexus": "Floating Zigzag",
        "topo_style_straight": "Straight Lines",
        "topo_style_synapse": "Lightning Pulses",
        "topo_mesh_title": "Spiderweb setup: Lattice (-/+), Tone and Opacity",
        "topo_telemetry_title": "Toggle between simulated ambient pulses or live DNS + Ping traffic",
        "topo_telemetry_label": "Logic:",
        "topo_telemetry_sim": "Simulated",
        "topo_telemetry_real": "Live Traffic",
        "topo_freq_title": "Pulse frequency and speed (- / +)",
        "topo_fx_title": "Toggle floating animation",
        "topo_offline_title": "Show or hide offline nodes",
        "topo_label_title": "Text shown on nodes",
        "topo_label_name": "Name",
        "topo_label_name_ip": "Name + IP",
        "topo_label_mac": "MAC",
        "topo_fit_title": "Center and frame map",
        "topo_cards_title": "Show/hide cards list",
        "topo_export_title": "Download JSON positions",
        "topo_import_title": "Restore JSON positions",
        "topo_reset_box_title": "Reset box to original width and centering",
        "topo_fullscreen_title": "Fullscreen (F)",
        "topo_shortcuts_hint": "Shortcuts: Ctrl+Z undo / Ctrl+Y redo / Ctrl+Drag moves only node",
        "topo_legend_core": "Main Router / Core",
        "topo_legend_ap": "APs / Mesh Nodes",
        "topo_legend_static": "Active Static",
        "topo_legend_dynamic": "Dynamic",
        "topo_legend_offline": "Offline",
        "topo_legend_controls": "🖱️ Wheel: Zoom · Drag: Pan · Click: Details",
        "timeline_title": "⏱️ Presence Timeline",
        "timeline_desc": "Green segments = connected. Ideal for detecting nighttime disconnects or IoT micro-cuts.",
        "timeline_search_ph": "Filter device...",
        "timeline_btn_6h": "6h",
        "timeline_btn_24h": "24h",
        "timeline_btn_72h": "3 days",
        "timeline_btn_168h": "7 days",
        "wifirf_title": "Radiofrequency Force Deauth (Wi-Fi 802.11 Deauth)",
        "wifirf_btn_refresh_diag": "🔄 Refresh Diagnostics",
        "wifirf_btn_disable_plugin": "❌ Disable Plugin",
        "wifirf_btn_install": "Install Tools (aircrack-ng, iw)",
        "wifirf_btn_monitor": "Activate Monitor Mode",
        "wifirf_btn_normal": "Return to Normal Mode",
        "wifirf_btn_scan": "Scan Air Wi-Fi Networks",
        "wifirf_filter_label": "Filter:",
        "wifirf_filter_my_net": "🏠 My Network Only",
        "wifirf_filter_all": "📡 All in the air",
        "wifirf_auto_bssid_lbl": "Router / Access Point BSSID (AP MAC):",
        "wifirf_auto_client_lbl": "Target Client MAC:",
        "wifirf_btn_auto_deauth": "⚡ Deauth Immediately (Auto)",
        "wifirf_manual_bssid_lbl": "Router / AP BSSID:",
        "wifirf_manual_client_lbl": "Client MAC:",
        "wifirf_manual_channel_lbl": "Channel:",
        "wifirf_btn_manual_deauth": "🔥 Launch Manual Burst",
        "wifirf_terminal_title": "📟 Wi-Fi (RF) Diagnostic Terminal",
        "wifirf_terminal_clear": "Clear Output",
        "diag_title": "⚠️ Automated Network & DHCP Diagnostics",
        "diag_desc": "Analyzes ARP IP conflicts, static reservations in DHCP pool, down services, randomized MACs and orphaned leases.",
        "diag_btn_scan": "🔍 Analyze Now",
        "ds_title": "Device Details",
        "ds_btn_watch": "🔔 Connection Alert",
        "ds_btn_watch_title": "Receive an email alert when this device connects to the network",
        "ds_btn_export": "📥 Export Sheet",
        "ds_btn_export_title": "Download JSON backup of this device",
        "ds_btn_import": "📤 Import Sheet",
        "ds_btn_import_title": "Restore JSON configuration for this device",
        "ds_btn_delete": "🗑️ Delete Sheet",
        "ds_btn_delete_title": "Delete static reservation from AdGuard Home and purge sheet",
        "ds_act_forensic": "🔍 Forensic Analysis",
        "ds_act_unblock_dns": "🟢 Unblock Internet (DNS)",
        "ds_act_block_dns": "🔴 Cut Internet (Block DNS)",
        "ds_act_wol": "⚡ Wake-on-LAN (Power on)",
        "ds_act_ping": "📶 Ping Device",
        "ds_act_edit_dhcp": "✏️ Edit DHCP Lease",
        "photo_modal_title": "Device Photo",
        "photo_modal_desc": "Options to change or update the image:",
        "photo_btn_camera": "Take Photo (Use Camera)",
        "photo_btn_apps": "Choose App (Google Photos, Files, Drive...)",
        "photo_btn_apps_title": "Shows smartphone menu with all available applications",
        "photo_btn_gallery": "Smartphone Gallery",
        "photo_btn_delete": "Delete Current Photo",
        "photo_btn_cancel": "Cancel",
        "settings_title": "⚙️ AdGuard Home & Router / Access Point Settings",
        "settings_wifi_plugin_enable": "Enable Wi-Fi Force Deauth",
        "settings_ag_url": "AdGuard Home URL",
        "settings_ag_user": "AdGuard Home User",
        "settings_ag_pass": "AdGuard Home Password",
        "settings_routers_discover": "🔍 Auto-detect Routers on Network",
        "settings_routers_discover_title": "Scan local network to auto-identify routers/access points",
        "settings_routers_add": "➕ Add New Router / AP",
        "settings_ha_enable": "Enable Home Assistant Plugin",
        "settings_localhost_enable": "Detect Localhost Services (localhost:port)",
        "settings_localhost_title": "Scans and displays in the top bar listening ports and applications on this host",
        "settings_ha_title": "Configured Home Assistant Instances",
        "settings_ha_discover": "🔍 Auto-detect on Network",
        "settings_ha_add": "➕ Add Instance",
        "settings_btn_save": "💾 Save and Test Configuration",
        "settings_btn_close": "Close",
        "sec_title": "🔑 Security & Password",
        "sec_user": "Username",
        "sec_new_pass": "New password (empty = keep current)",
        "sec_repeat_pass": "Repeat new password",
        "sec_curr_pass": "Current password *",
        "sec_btn_cancel": "Cancel",
        "sec_btn_save": "💾 Save",
        "rename_title": "Customize Service Name",
        "rename_host": "Host device:",
        "rename_original": "Original detected:",
        "rename_custom_lbl": "Custom name:",
        "rename_ph": "E.g. InfluxDB, Node-RED, Home Automation...",
        "rename_btn_reset": "Remove custom name and revert to original",
        "rename_btn_cancel": "Cancel",
        "rename_btn_save": "💾 Save Name",
        "columns_title": "📊 Customize Columns & Tabs",
        "columns_reset_tabs": "Reset Tabs",
        "columns_reset_tabs_title": "Reset original order of main tabs",
        "columns_reset_cols": "Reset Columns",
        "columns_reset_cols_title": "Reset column visibility and order",
        "columns_desc": "Enable, disable or drag to reorder table columns and top tabs.",
        "alerts_title": "🔔 Alerts & Notifications Settings",
        "alerts_tab_email": "Email (Gmail SMTP)",
        "alerts_tab_webhooks": "Webhooks & Bots (Telegram / Discord / ntfy)",
        "alerts_tab_events": "Notifiable Events",
        "alerts_email_user": "Your Gmail account (sender)",
        "alerts_email_pass": "App Password (16 letters)",
        "alerts_email_pass_link": "Get ↗",
        "alerts_email_to": "Recipient Email (where to receive alerts)",
        "alerts_email_host": "SMTP Server / Port",
        "alerts_email_new_dev": "Send email when a new device connects to network",
        "alerts_email_dev_connect": "Send email when any device reconnects",
        "alerts_btn_test_smtp": "📧 Test Email Sending Now",
        "alerts_ntfy_url": "ntfy URL (e.g. https://ntfy.sh/my-net)",
        "alerts_tg_token": "Telegram Bot Token",
        "alerts_tg_chat": "Telegram Chat ID",
        "alerts_webhook": "Webhook URL (Home Assistant / Discord)",
        "alerts_ev_new_dev": "New device on network",
        "alerts_ev_connect": "Device connects / reconnects",
        "alerts_ev_svc_down": "Web service down (after 10 min down)",
        "alerts_ev_svc_up": "Web service recovered",
        "alerts_ev_watched": "Watched device disconnected",
        "alerts_watched_macs": "Watched MACs (comma-separated — alerts if disconnected)",
        "alerts_btn_test": "🔔 Send Test Alert",
        "alerts_btn_save": "💾 Save Alerts",
        "backup_title": "💾 Export and Import Settings / Backups",
        "backup_desc": "Saves all AdGuard static IPs, routers, custom service names, favorites, notes/rooms and alerts.",
        "backup_inc_secrets": "Include router/AdGuard passwords and tokens in JSON",
        "backup_btn_download_json": "📥 Download Full Backup (.JSON)",
        "backup_btn_export_csv": "📊 Export Table to Excel (.CSV)",
        "backup_import_title": "Restore Backup",
        "backup_import_desc": "Restore your configuration from a previously exported .JSON or .ZIP file.",
        "order_modal_title": "📌 Chronological Static IP Sequence",
        "order_modal_desc": "View and manage the chronological sequence in which your static IPs were fixed in AdGuard Home.",
        "order_modal_btn_close": "Close",
        "hunter_title": "🔍 Forensic Device Hunter by MAC",
        "hunter_desc": "Track physical presence of any MAC across switches, routers and Wi-Fi antennas in real-time.",
        "hunter_search_ph": "Enter MAC address to track...",
        "hunter_btn_search": "Track MAC",
        "btn_close": "Close",
        "btn_cancel": "Cancel",
        "btn_save": "Save",
        "btn_apply": "Apply",
        "btn_delete": "Delete",
        "btn_accept": "Accept",
        "popup_info_title": "Information",
        "popup_confirm_title": "Confirmation"
    }
};

window.currentLang = localStorage.getItem('ag_panel_lang') || 'es';

/**
 * Función global de traducción con fallback
 */
window.t = function(key, fallback) {
    const lang = window.currentLang || localStorage.getItem('ag_panel_lang') || 'es';
    const dict = (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS[lang]) ? TRANSLATIONS[lang] : (typeof TRANSLATIONS !== 'undefined' ? TRANSLATIONS['es'] : null);
    if (dict && dict[key] !== undefined) {
        return dict[key];
    }
    if (fallback !== undefined) return fallback;
    if (typeof TRANSLATIONS !== 'undefined' && TRANSLATIONS['es'] && TRANSLATIONS['es'][key] !== undefined) {
        return TRANSLATIONS['es'][key];
    }
    return key;
};

/**
 * Alternar el menú desplegable de idiomas
 */
window.toggleLangMenu = function(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('lang-menu-dropdown');
    if (!menu) return;
    const isShowing = menu.style.display === 'block';
    // Cerrar otros menús desplegables
    const userMenu = document.getElementById('user-menu-dropdown');
    if (userMenu) userMenu.style.display = 'none';
    const netMenu = document.getElementById('network-menu-dropdown');
    if (netMenu) netMenu.style.display = 'none';
    menu.style.display = isShowing ? 'none' : 'block';
};

// Cerrar el menú al hacer clic fuera
document.addEventListener('click', function(e) {
    const menu = document.getElementById('lang-menu-dropdown');
    const btn = document.getElementById('lang-selector-btn');
    if (menu && menu.style.display === 'block') {
        if (!menu.contains(e.target) && (!btn || !btn.contains(e.target))) {
            menu.style.display = 'none';
        }
    }
});

/**
 * Cambiar idioma activo y persistir
 */
window.setLanguage = function(lang, e) {
    if (e) e.preventDefault();
    if (lang !== 'es' && lang !== 'en') lang = 'es';
    window.currentLang = lang;
    localStorage.setItem('ag_panel_lang', lang);

    const menu = document.getElementById('lang-menu-dropdown');
    if (menu) menu.style.display = 'none';

    window.applyTranslations(lang);

    if (typeof showMessage === 'function') {
        const toastMsg = (lang === 'en') 
            ? 'Language switched to English.' 
            : 'Idioma cambiado a Español.';
        showMessage(toastMsg);
    }
};

/**
 * Recorrer el DOM y traducir todos los elementos data-i18n, placeholders y títulos
 */
window.applyTranslations = function(lang) {
    if (!lang) lang = window.currentLang || localStorage.getItem('ag_panel_lang') || 'es';
    window.currentLang = lang;
    const dict = TRANSLATIONS[lang] || TRANSLATIONS['es'];

    // 1. Textos directos
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key] !== undefined) {
            const badge = el.querySelector('.badge, .tab-badge, .pill-count');
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

    // 4. Etiqueta del botón de idioma superior
    const label = document.getElementById('current-lang-label');
    if (label) {
        label.textContent = (lang === 'en') ? '🇬🇧 EN' : '🇪🇸 ES';
    }

    // 5. Botones dinámicos especiales
    const lblWidth = document.getElementById('lbl-table-width');
    if (lblWidth) {
        const box = document.getElementById('table-outer-box');
        const isExp = box && box.classList.contains('is-expanded-width');
        lblWidth.textContent = isExp ? window.t('lbl_table_width_standard') : window.t('lbl_table_width_expand');
    }
    const refreshTxt = document.getElementById('refresh-text');
    if (refreshTxt) {
        refreshTxt.textContent = window.t('btn_refresh_text');
    }

    // 6. Re-renderizar componentes dinámicos activos
    if (typeof renderTable === 'function') renderTable();
    if (typeof renderServicesCards === 'function') renderServicesCards();
    if (typeof renderTimelineRows === 'function') renderTimelineRows();
    if (typeof renderIpMap === 'function') renderIpMap();
    if (typeof renderGlobalNetworkMenu === 'function') renderGlobalNetworkMenu();
    if (typeof renderColumnManager === 'function') renderColumnManager();
    if (typeof renderStaticOrderList === 'function') renderStaticOrderList();
    if (typeof syncTopoControlsUI === 'function') syncTopoControlsUI();
};

// Ejecutar al cargar el documento
document.addEventListener('DOMContentLoaded', function() {
    const savedLang = localStorage.getItem('ag_panel_lang') || 'es';
    window.currentLang = savedLang;
    const label = document.getElementById('current-lang-label');
    if (label) {
        label.textContent = (savedLang === 'en') ? '🇬🇧 EN' : '🇪🇸 ES';
    }
    window.applyTranslations(savedLang);
});
