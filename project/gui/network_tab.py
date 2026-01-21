# network_tab.py
import ipaddress
import platform
import re
import socket
import subprocess
import tkinter as tk
from tkinter import ttk, simpledialog

from ..utils.adb_utils import exec_adb, run_in_thread
from ..utils.gui_utils import gui_log
from ..utils.net_utils import find_ip_from_mac, _get_local_ipv4_and_prefix, _ping_sweep_cold
from .profiles_tab import add_profile


# =========================
# Estado (globals simples)
# =========================
_network_tab = None
_tab_initialized = False

_interface_combo = None
_interface_var = None
_interface_details_var = None
_interface_entries = []  # [(label, ip)]

_available_list = None

AUTO_INTERFACE_LABEL = "Red local"


# =========================
# Interfaces (tu versión, funcionando)
# =========================
def _list_windows_interfaces():
    try:
        output = subprocess.check_output(
            ["ipconfig"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        gui_log(f"No se pudo ejecutar ipconfig: {exc}", level="error")
        return []

    interfaces = []
    current_name = None
    current_ip = None

    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if line and not line.startswith(" "):
            if current_name and current_ip:
                interfaces.append((current_name, current_ip))
            current_name = line.strip().rstrip(":")
            current_ip = None
            continue

        if current_name:
            match = re.search(r"(IPv4 Address|Direcci[oó]n IPv4).+?:\s*(.+)$", line)
            if match:
                ip = match.group(2).strip()
                ip = ip.replace("(Preferred)", "").strip()
                current_ip = ip

    if current_name and current_ip:
        interfaces.append((current_name, current_ip))

    return interfaces


def _list_unix_interfaces():
    interfaces = []
    # Preferir 'ip' si existe
    try:
        output = subprocess.check_output(
            ["ip", "-o", "-4", "addr", "show"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                name = parts[1]
                address = parts[3].split("/")[0]
                if address != "127.0.0.1":
                    interfaces.append((name, address))
        if interfaces:
            return interfaces
    except Exception:
        pass

    # Fallback a ifconfig
    try:
        output = subprocess.check_output(
            ["ifconfig"],
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except Exception as exc:
        gui_log(f"No se pudo detectar interfaces: {exc}", level="error")
        return []

    current_name = None
    for line in output.splitlines():
        if line and not line.startswith(" "):
            current_name = line.split(":", 1)[0]
            continue
        if current_name:
            match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
            if match:
                address = match.group(1)
                if address != "127.0.0.1":
                    interfaces.append((current_name, address))

    return interfaces


def _list_network_interfaces():
    system = platform.system().lower()
    if system == "windows":
        return _list_windows_interfaces()
    return _list_unix_interfaces()


def _update_interface_details():
    if not _interface_var or not _interface_details_var:
        return
    selected = _interface_var.get()
    if selected == AUTO_INTERFACE_LABEL:
        local_ip, _ = _get_local_ipv4_and_prefix()
        if local_ip:
            _interface_details_var.set(f"IP local (auto): {local_ip}")
        else:
            _interface_details_var.set("No se pudo detectar IP local.")
        return

    selected_ip = ""
    for label, ip in _interface_entries:
        if label == selected:
            selected_ip = ip
            break

    if selected_ip:
        _interface_details_var.set(f"IP local: {selected_ip}")
    else:
        _interface_details_var.set("Selecciona una interfaz de red")


def refresh_interfaces():
    global _interface_entries
    if _interface_combo is None or _interface_var is None or _interface_details_var is None:
        return

    interfaces = _list_network_interfaces()
    if not interfaces:
        _interface_entries = []
        _interface_combo["values"] = [AUTO_INTERFACE_LABEL]
        _interface_var.set(AUTO_INTERFACE_LABEL)
        _interface_details_var.set("No se detectaron interfaces con IPv4.")
        return

    _interface_entries = [(f"{name} ({ip})", ip) for name, ip in interfaces]
    values = [AUTO_INTERFACE_LABEL] + [entry[0] for entry in _interface_entries]
    _interface_combo["values"] = values

    if _interface_var.get() not in values:
        _interface_var.set(AUTO_INTERFACE_LABEL)

    _update_interface_details()


def _resolve_interface_ip():
    """Devuelve IP seleccionada o IP auto si aplica."""
    if _interface_var is None:
        return None
    selected = _interface_var.get()
    if not selected or selected == AUTO_INTERFACE_LABEL:
        local_ip, _ = _get_local_ipv4_and_prefix()
        return local_ip

    for label, ip in _interface_entries:
        if label == selected:
            return ip
    return None


# =========================
# ARP / Escaneo (lo "bueno" del tab de red)
# =========================
def _parse_arp_tables(output: str):
    """
    Windows suele incluir líneas tipo:
      Interface: 192.168.1.10 --- 0x9
      192.168.1.1           00-11-22-33-44-55   dynamic
    Linux/mac puede variar; aquí capturamos lo típico: IP + MAC.
    """
    tables = {}
    current_interface = None

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Windows: "Interface: 192.168.1.10 --- 0x..."
        if line.lower().startswith("interface:"):
            parts = line.split()
            # parts[1] suele ser la IP
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
    Lee `arp -a` y por cada (ip, mac) llama callback(ip, mac, adb_open).
    """
    try:
        out = subprocess.getoutput("arp -a")
        tables = _parse_arp_tables(out)

        local_ip, prefix = _get_local_ipv4_and_prefix()
        prefix = prefix or 24

        target_ip = _resolve_interface_ip() or local_ip
        entries = _entries_for_interface(tables, target_ip, prefix=prefix)

        if not entries:
            gui_log("No se encontraron dispositivos en la red seleccionada.", level="error")
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

    except Exception as exc:
        gui_log(f"Error escaneando red (arp): {exc}", level="error")


def refresh_available_list_incremental():
    """Escaneo rápido: lee ARP y mete filas una a una (no bloquea GUI)."""
    if _available_list is None:
        return

    _available_list.delete(*_available_list.get_children())
    refresh_interfaces()

    def insert_item(ip, mac, adb_open):
        _available_list.after(0, lambda: _insert(ip, mac, adb_open))

    def _insert(ip, mac, adb_open):
        item = _available_list.insert("", "end", values=(ip, mac), tags=("darkrow",))
        if adb_open:
            _available_list.item(item, tags=("adb_on",))

    run_in_thread(lambda: scan_network_with_adb_status_callback(callback=insert_item))


def refresh_available_list_full():
    """Se usa tras ping sweep: rellena toda la tabla de golpe (rápido)."""
    if _available_list is None:
        return

    refresh_interfaces()
    items = []

    def collect(ip, mac, adb_open):
        items.append((ip, mac, adb_open))

    scan_network_with_adb_status_callback(callback=collect)

    def do_insert_batch():
        try:
            _available_list.delete(*_available_list.get_children())
            for ip, mac, adb_open in items:
                item = _available_list.insert("", "end", values=(ip, mac), tags=("darkrow",))
                if adb_open:
                    _available_list.item(item, tags=("adb_on",))
        except Exception as exc:
            gui_log(f"Error insertando batch en GUI: {exc}", level="error")

    _available_list.after(0, do_insert_batch)


def connect_selected_available():
    if _available_list is None:
        return
    sel = _available_list.selection()
    if not sel:
        gui_log("No hay IP seleccionada", level="error")
        return
    ip = _available_list.item(sel[0], "values")[0]
    run_in_thread(lambda: exec_adb(["connect", f"{ip}:5555"]))
    gui_log(f"Intentando conectar a {ip}:5555", level="info")


def add_selected_as_profile():
    if _available_list is None:
        return
    sel = _available_list.selection()
    if not sel:
        gui_log("No hay dispositivo seleccionado", level="error")
        return
    ip, mac = _available_list.item(sel[0], "values")
    name = simpledialog.askstring("Nuevo perfil", f"Nombre para el perfil {ip}?")
    if not name:
        return
    add_profile(name=name, mac=mac, ip=ip)
    gui_log(f"Perfil '{name}' creado desde red", level="info")


def _full_scan_then_populate():
    """
    Ping sweep (bloqueante) en background para poblar ARP.
    Luego: refresh_available_list_full()
    """
    try:
        gui_log("Iniciando escaneo completo de red (ping sweep)...", level="info")

        # Esto ayuda a poblar ARP en algunos flujos previos
        try:
            find_ip_from_mac()
        except Exception:
            pass

        local_ip, _ = _get_local_ipv4_and_prefix()
        target_ip = _resolve_interface_ip() or local_ip
        if not target_ip:
            gui_log("No se pudo detectar la IP local para escanear la red.", level="error")
            return

        base_parts = target_ip.split(".")
        if len(base_parts) >= 3:
            base = ".".join(base_parts[0:3])
            _ping_sweep_cold(base)
        else:
            gui_log("IP local inválida para ping sweep.", level="error")
            return

        gui_log("Ping sweep completado, actualizando tabla.", level="info")
        if _network_tab is not None:
            _network_tab.after(0, refresh_available_list_full)

    except Exception as exc:
        gui_log(f"Error durante escaneo completo de red: {exc}", level="error")


def on_tab_change(event):
    global _tab_initialized
    if _network_tab is None:
        return
    notebook = event.widget
    current = notebook.nametowidget(notebook.select())

    if current is _network_tab:
        refresh_interfaces()
        if not _tab_initialized:
            _tab_initialized = True
            run_in_thread(_full_scan_then_populate)


# =========================
# UI
# =========================
def create_network_tab(notebook):
    global _network_tab, _interface_combo, _interface_var, _interface_details_var, _available_list

    tab = ttk.Frame(notebook, padding=10)
    notebook.add(tab, text="Red")
    _network_tab = tab

    # Selector de interfaz
    selector = ttk.Frame(tab)
    selector.pack(fill=tk.X, pady=(0, 8))
    selector.columnconfigure(1, weight=1)

    ttk.Label(selector, text="Interfaz:").grid(row=0, column=0, sticky="w")
    _interface_var = tk.StringVar(value=AUTO_INTERFACE_LABEL)
    _interface_combo = ttk.Combobox(selector, textvariable=_interface_var, state="readonly", width=40)
    _interface_combo.grid(row=0, column=1, sticky="ew", padx=(6, 6))
    _interface_combo.bind("<<ComboboxSelected>>", lambda _e: _update_interface_details())

    ttk.Button(selector, text="Refrescar interfaces", command=refresh_interfaces).grid(row=0, column=2, sticky="e")

    _interface_details_var = tk.StringVar(value="Selecciona una interfaz de red")
    ttk.Label(tab, textvariable=_interface_details_var).pack(anchor="w", pady=(0, 8))

    # Tabla IP/MAC
    _available_list = ttk.Treeview(tab, columns=("IP", "MAC"), show="headings", height=10)
    _available_list.heading("IP", text="IP")
    _available_list.heading("MAC", text="MAC")
    _available_list.column("IP", width=200)
    _available_list.column("MAC", width=320)
    _available_list.pack(fill=tk.BOTH, expand=True)

    scroll = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=_available_list.yview)
    _available_list.configure(yscrollcommand=scroll.set)
    scroll.place(in_= _available_list, relx=1.0, rely=0, relheight=1.0, anchor="ne")

    _available_list.tag_configure("darkrow")
    _available_list.tag_configure("adb_on", background="#003300", foreground="#00ff00")

    # Botones
    btns = ttk.Frame(tab)
    btns.pack(fill=tk.X, pady=(8, 0))
    ttk.Button(btns, text="Escanear red", command=refresh_available_list_incremental).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text="Conectar", command=connect_selected_available).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text="Añadir como perfil", command=add_selected_as_profile).pack(side=tk.LEFT, padx=4)

    # Inicialización
    refresh_interfaces()
    refresh_available_list_incremental()

    # Importante: bind una sola vez en tu app general si puedes.
    notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    return tab
