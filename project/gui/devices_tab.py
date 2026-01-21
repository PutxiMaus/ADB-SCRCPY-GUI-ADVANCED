import ipaddress
import subprocess, re, socket, tkinter as tk
from tkinter import ttk, simpledialog
from ..utils.adb_utils import exec_adb, run_in_thread
from ..config.config import ADB_PATH
from ..utils.gui_utils import gui_log
from .profiles_tab import add_profile
from ..utils.net_utils import find_ip_from_mac, _get_local_ipv4_and_prefix, _ping_sweep_cold

# referencias globales
available_list = None
connected_list = None
tab_initialized = {}
interface_var = None
interface_combo = None

AUTO_INTERFACE_LABEL = "Auto (red local)"

# =========================
# Funciones de gestión
# =========================
def list_connected_devices():
    """Devuelve [(serial/ip, info)] desde adb devices -l"""
    try:
        result = subprocess.run(
            [str(ADB_PATH), "devices", "-l"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace"
        )
        devices = []
        for line in result.stdout.splitlines():
            if line.strip() and not line.startswith("List") and "device" in line:
                parts = line.split()
                serial = parts[0]
                info = " ".join(parts[1:])
                devices.append((serial, info))
        return devices
    except Exception as e:
        gui_log(f"Error listando dispositivos: {e}", level="error")
        return []

def refresh_connected_list():
    """Rellena la pestaña Conectados con Serial/IP + info"""
    if connected_list is None:
        return
    connected_list.delete(*connected_list.get_children())
    for serial, info in list_connected_devices():
        ip_display = serial
        # Si el serial no es ya una IP, intentar resolverla
        if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", serial):
            try:
                result = subprocess.run(
                    [
                        str(ADB_PATH),
                        "-s",
                        serial,
                        "shell",
                        "ip",
                        "-f",
                        "inet",
                        "addr",
                        "show",
                        "wlan0",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=2,
                )
                for line in result.stdout.splitlines():
                    if "inet " in line:
                        ip_display = line.strip().split()[1].split("/")[0]
                        break
            except Exception:
                # fallback a ARP
                maybe_ip = find_ip_from_mac(serial)
                if maybe_ip:
                    ip_display = maybe_ip
        connected_list.insert("", "end", values=(ip_display, info), tags=("darkrow",))

def disconnect_selected_device():
    sel = connected_list.selection()
    if not sel:
        gui_log("No hay dispositivo seleccionado", level="error")
        return
    serial = connected_list.item(sel[0], "values")[0]
    run_in_thread(lambda: exec_adb(["disconnect", serial]))
    gui_log(f"Desconectando {serial}", level="info")

def shell_selected_device():
    sel = connected_list.selection()
    if not sel:
        gui_log("No hay dispositivo seleccionado", level="error")
        return
    serial = connected_list.item(sel[0], "values")[0]
    run_in_thread(lambda: exec_adb(["-s", serial, "shell"]))

# =========================
# Escaneo y helpers ARP
# =========================
def _parse_arp_tables(output):
    tables = {}
    current_interface = None
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.lower().startswith("interface:"):
            parts = line.split()
            if len(parts) >= 2:
                current_interface = parts[1]
                tables.setdefault(current_interface, [])
            continue
        parts = line.split()
        if len(parts) >= 2 and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", parts[0]):
            ip = parts[0]
            mac = parts[1]
            if current_interface:
                tables.setdefault(current_interface, []).append((ip, mac))
            else:
                tables.setdefault("unknown", []).append((ip, mac))
    return tables

def _get_interface_candidates():
    try:
        out = subprocess.getoutput("arp -a")
    except Exception as e:
        gui_log(f"Error leyendo arp -a: {e}", level="error")
        return []
    tables = _parse_arp_tables(out)
    return sorted([ip for ip in tables.keys() if ip != "unknown"])

def _resolve_interface_ip():
    if interface_var is None:
        return None
    selected = interface_var.get()
    if not selected or selected == AUTO_INTERFACE_LABEL:
        local_ip, _ = _get_local_ipv4_and_prefix()
        return local_ip
    return selected

def _entries_for_interface(tables, interface_ip, prefix=24):
    if not interface_ip:
        return []
    if interface_ip in tables:
        return tables.get(interface_ip, [])
    try:
        net = ipaddress.ip_network(f"{interface_ip}/{prefix}", strict=False)
    except ValueError:
        return []
    entries = []
    for values in tables.values():
        for ip, mac in values:
            try:
                if ipaddress.ip_address(ip) in net:
                    entries.append((ip, mac))
            except ValueError:
                continue
    return entries

def scan_network_with_adb_status_callback(callback=None):
    """
    Escanea la salida de `arp -a` y para cada línea válida llama callback(ip, mac, adb_open).
    Esta función es síncrona y relativamente rápida; la ejecución prolongada viene del ping sweep.
    """
    try:
        out = subprocess.getoutput("arp -a")
        tables = _parse_arp_tables(out)
        interface_ip = _resolve_interface_ip()
        local_ip, prefix = _get_local_ipv4_and_prefix()
        prefix = prefix or 24
        target_ip = interface_ip or local_ip
        entries = _entries_for_interface(tables, target_ip, prefix=prefix)
        if not entries:
            gui_log("No se encontraron dispositivos en la red local seleccionada.", level="error")
            return
        for ip, mac in entries:
            adb_open = False
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.2)
                if s.connect_ex((ip, 5555)) == 0:
                    adb_open = True
                s.close()
            except Exception:
                pass
            if callback:
                callback(ip, mac, adb_open)
    except Exception as e:
        gui_log(f"Error escaneando red (arp): {e}", level="error")

# =========================
# Rellenado incremental (botón Refrescar) - uno a uno
# =========================
def refresh_available_list_incremental():
    """Limpia y escanea en segundo plano para rellenar la tabla uno a uno (no bloquea GUI)."""
    if available_list is None:
        return
    available_list.delete(*available_list.get_children())

    def insert_item(ip, mac, adb_open):
        # schedule insertion en hilo principal
        available_list.after(0, lambda: _insert(ip, mac, adb_open))

    def _insert(ip, mac, adb_open):
        item = available_list.insert("", "end", values=(ip, mac), tags=("darkrow",))
        if adb_open:
            available_list.item(item, tags=("adb_on",))

    run_in_thread(lambda: scan_network_with_adb_status_callback(callback=insert_item))

# =========================
# Rellenado completo (poblado una vez tras ping sweep) - rellena toda la tabla
# =========================
def refresh_available_list_full():
    """
    Rellena la tabla leyendo arp -a y añadiendo todos los elementos de golpe.
    Diseñado para usarse después de que _ping_sweep_cold() haya terminado.
    """
    if available_list is None:
        return
    items = []

    def collect(ip, mac, adb_open):
        items.append((ip, mac, adb_open))

    # Recolectar de arp -a
    scan_network_with_adb_status_callback(callback=collect)

    # Ahora insertar todo en el hilo principal (un único batch, aunque se insertan uno a uno rápido)
    def do_insert_batch():
        try:
            available_list.delete(*available_list.get_children())
            for ip, mac, adb_open in items:
                item = available_list.insert("", "end", values=(ip, mac), tags=("darkrow",))
                if adb_open:
                    available_list.item(item, tags=("adb_on",))
        except Exception as e:
            gui_log(f"Error insertando batch en GUI: {e}", level="error")

    available_list.after(0, do_insert_batch)

# =========================
# Acciones sobre elementos
# =========================
def connect_selected_available():
    sel = available_list.selection()
    if not sel:
        gui_log("No hay IP seleccionada", level="error")
        return
    ip = available_list.item(sel[0], "values")[0]
    run_in_thread(lambda: exec_adb(["connect", f"{ip}:5555"]))
    gui_log(f"Intentando conectar a {ip}:5555", level="info")

def add_selected_as_profile():
    sel = available_list.selection()
    if not sel:
        gui_log("No hay dispositivo seleccionado", level="error")
        return
    ip, mac = available_list.item(sel[0], "values")
    name = simpledialog.askstring("Nuevo perfil", f"Nombre para el perfil {ip}?")
    if not name:
        return
    add_profile(name=name, mac=mac, ip=ip)
    gui_log(f"Perfil '{name}' creado desde red", level="info")

# =========================
# Manejo de pestaña: al entrar rellenar la ARP con todo (como conectar perfil)
# =========================
def on_tab_change(event):
    try:
        tab_id = event.widget.select()
        tab_text = event.widget.tab(tab_id, "text")
    except Exception as e:
        gui_log(f"Evento de cambio de pestaña inválido: {e}", level="error")
        return

    if tab_text == "Red local":
        # Si ya inicializamos antes, no volver a lanzar el ping sweep automático
        if tab_initialized.get("red_local"):
            # Si ya inicializada, simplemente refrescamos mostrando incremental si quieres,
            # aquí dejamos que el usuario use el botón Refrescar para incremental.
            return

        tab_initialized["red_local"] = True

        def do_full_scan_then_populate():
            """
            Ejecuta las funciones de net_utils que llenan la ARP (find_ip_from_mac, prefix, ping sweep).
            Cuando terminan, llama a refresh_available_list_full() para poblar la tabla completa.
            Todo esto en background para no bloquear.
            """
            try:
                gui_log("Iniciando escaneo completo de red (ping sweep)...", level="info")
                # Ejecutar las funciones que emplea 'Conectar perfil' para poblar ARP
                find_ip_from_mac()
                interface_ip = _resolve_interface_ip()
                local_ip, _ = _get_local_ipv4_and_prefix()
                target_ip = interface_ip or local_ip
                if not target_ip:
                    gui_log("No se pudo detectar la IP local para escanear la red.", level="error")
                    return
                base_parts = target_ip.split(".")
                if len(base_parts) >= 3:
                    base = ".".join(base_parts[0:3])
                    _ping_sweep_cold(base)  # **bloqueante**: hace el ping sweep y rellena la ARP cache
                else:
                    gui_log("IP local inválida para ping sweep.", level="error")
                    return
                gui_log("Ping sweep completado, actualizando tabla ARP completa.", level="info")
                # Al terminar, actualizar la tabla con todo lo que haya en ARP
                # Usar after en hilo principal para insertar
                event.widget.after(0, refresh_available_list_full)
                # También refrescar la lista de conectados por si hay cambios
                event.widget.after(0, refresh_connected_list)
            except Exception as e:
                gui_log(f"Error durante escaneo completo de red: {e}", level="error")

        run_in_thread(do_full_scan_then_populate)

# =========================
# Construcción de pestañas
# =========================
def create_devices_tabs(notebook):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TFrame")
    style.configure("Treeview")
    style.configure("Treeview.Heading")
    style.configure("TButton")
    style.configure("Vertical.TScrollbar")

    # --- Tab Red local ---
    tab_network = ttk.Frame(notebook)
    notebook.add(tab_network, text="Red local")
    frame_network = ttk.Frame(tab_network, padding=12, style="Dark.TFrame")
    frame_network.pack(fill=tk.BOTH, expand=True)

    global available_list, interface_var, interface_combo
    interface_row = ttk.Frame(frame_network, style="Dark.TFrame")
    interface_row.pack(fill=tk.X, pady=(0, 6))
    tk.Label(interface_row, text="Interfaz:", bg="#1e1f22", fg="#b8ffb8").pack(side=tk.LEFT, padx=(0, 6))
    interface_var = tk.StringVar(value=AUTO_INTERFACE_LABEL)
    interface_combo = ttk.Combobox(
        interface_row,
        textvariable=interface_var,
        state="readonly",
        values=[AUTO_INTERFACE_LABEL] + _get_interface_candidates(),
        width=28,
    )
    interface_combo.pack(side=tk.LEFT)
    ttk.Button(
        interface_row,
        text="Actualizar interfaces",
        command=lambda: interface_combo.configure(values=[AUTO_INTERFACE_LABEL] + _get_interface_candidates()),
    ).pack(side=tk.LEFT, padx=6)

    global available_list
    available_list = ttk.Treeview(frame_network, columns=("IP", "MAC"), show="headings", height=8)
    available_list.heading("IP", text="IP")
    available_list.heading("MAC", text="MAC")
    available_list.column("IP", width=200)
    available_list.column("MAC", width=300)
    available_list.pack(fill=tk.BOTH, expand=True, pady=(0,6))
    scroll_network = ttk.Scrollbar(frame_network, orient=tk.VERTICAL,
                                   command=available_list.yview, style="Vertical.TScrollbar")
    available_list.config(yscrollcommand=scroll_network.set)
    available_list.tag_configure("darkrow")
    available_list.tag_configure("adb_on", background="#003300", foreground="#00ff00")

    btn_frame_network = ttk.Frame(frame_network, style="Dark.TFrame")
    btn_frame_network.pack(fill=tk.X, pady=4)
    ttk.Button(btn_frame_network, text="Escanear", command=refresh_available_list_incremental).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_network, text="Conectar", command=connect_selected_available).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_network, text="Añadir como perfil", command=add_selected_as_profile).pack(side=tk.LEFT, padx=4)

    # --- Tab Conectados ---
    tab_connected = ttk.Frame(notebook)
    notebook.add(tab_connected, text="Conectados")
    frame_connected = ttk.Frame(tab_connected, padding=12, style="Dark.TFrame")
    frame_connected.pack(fill=tk.BOTH, expand=True)

    global connected_list
    connected_list = ttk.Treeview(frame_connected, columns=("Serial", "Info"), show="headings", height=8)
    connected_list.heading("Serial", text="Serial/IP")
    connected_list.heading("Info", text="Información")
    connected_list.column("Serial", width=200)
    connected_list.column("Info", width=400)
    connected_list.pack(fill=tk.BOTH, expand=True, pady=(0,6))
    scroll_connected = ttk.Scrollbar(frame_connected, orient=tk.VERTICAL,
                                     command=connected_list.yview, style="Vertical.TScrollbar")
    connected_list.config(yscrollcommand=scroll_connected.set)
    connected_list.tag_configure("darkrow")

    btn_frame_connected = ttk.Frame(frame_connected, style="Dark.TFrame")
    btn_frame_connected.pack(fill=tk.X, pady=4)
    ttk.Button(
        btn_frame_connected,
        text="Refrescar",
        command=lambda: (refresh_connected_list(), refresh_available_list_incremental())
    ).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_connected, text="Desconectar", command=disconnect_selected_device).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_connected, text="Abrir Shell", command=shell_selected_device).pack(side=tk.LEFT, padx=4)

    # inicializar listas básicas (rápidas)
    refresh_connected_list()
    refresh_available_list_incremental()

    # ligar evento de cambio de pestaña
    notebook.bind("<<NotebookTabChanged>>", on_tab_change)
