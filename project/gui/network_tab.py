import platform
import re
import subprocess
import tkinter as tk
from tkinter import ttk

from ..utils.gui_utils import gui_log

_network_tab = None
_interface_combo = None
_interface_var = None
_interface_details_var = None
_interface_entries = []


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
    if not _interface_entries or _interface_var is None or _interface_details_var is None:
        return
    selected = _interface_var.get()
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
        _interface_combo["values"] = []
        _interface_var.set("")
        _interface_details_var.set("No se detectaron interfaces con IPv4.")
        return

    _interface_entries = [(f"{name} ({ip})", ip) for name, ip in interfaces]
    values = [entry[0] for entry in _interface_entries]
    _interface_combo["values"] = values
    if _interface_var.get() not in values:
        _interface_var.set(values[0])
    _update_interface_details()


def refresh_available_list_incremental():
    refresh_interfaces()


def on_tab_change(event):
    if _network_tab is None:
        return
    notebook = event.widget
    current = notebook.nametowidget(notebook.select())
    if current is _network_tab:
        refresh_interfaces()


def create_network_tab(notebook):
    global _network_tab, _interface_combo, _interface_var, _interface_details_var

    tab = ttk.Frame(notebook, padding=8)
    notebook.add(tab, text="Red")
    _network_tab = tab

    header = ttk.Label(tab, text="Red", font=(None, 11, "bold"))
    header.grid(row=0, column=0, sticky="w", pady=(0, 8))

    selector_frame = ttk.Frame(tab)
    selector_frame.grid(row=1, column=0, sticky="ew")
    selector_frame.columnconfigure(1, weight=1)

    ttk.Label(selector_frame, text="Interfaz:").grid(row=0, column=0, sticky="w")
    _interface_var = tk.StringVar()
    _interface_combo = ttk.Combobox(selector_frame, textvariable=_interface_var, state="readonly")
    _interface_combo.grid(row=0, column=1, sticky="ew", padx=(6, 6))
    _interface_combo.bind("<<ComboboxSelected>>", lambda event: _update_interface_details())

    ttk.Button(selector_frame, text="Refrescar", command=refresh_interfaces).grid(row=0, column=2, sticky="e")

    _interface_details_var = tk.StringVar(value="Selecciona una interfaz de red")
    ttk.Label(tab, textvariable=_interface_details_var).grid(row=2, column=0, sticky="w", pady=(8, 0))

    tab.columnconfigure(0, weight=1)

    refresh_interfaces()
    return tab
