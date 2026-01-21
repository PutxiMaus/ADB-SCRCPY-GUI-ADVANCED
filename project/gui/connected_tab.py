import subprocess, re, tkinter as tk
from tkinter import ttk
from ..utils.adb_utils import exec_adb, run_in_thread
from ..config.config import ADB_PATH, TOOLS_DIR
from ..utils.gui_utils import gui_log
from ..utils.net_utils import find_ip_from_mac

# referencias globales
connected_list = None
connected_search_var = None

def list_connected_devices():
    """Devuelve [(serial/ip, info)] desde adb devices -l"""
    try:
        result = subprocess.run(
            [str(ADB_PATH), "devices", "-l"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(TOOLS_DIR),
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
                    cwd=str(TOOLS_DIR),
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
    filter_connected_list()


def filter_connected_list():
    if connected_list is None or connected_search_var is None:
        return
    search = connected_search_var.get().lower().strip()
    for item in connected_list.get_children():
        serial, info = connected_list.item(item)["values"]
        serial_text = str(serial).lower()
        info_text = str(info).lower()
        if not search or search in serial_text or search in info_text:
            connected_list.reattach(item, "", "end")
        else:
            connected_list.detach(item)


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


def copy_selected_serial():
    sel = connected_list.selection()
    if not sel:
        gui_log("No hay dispositivo seleccionado", level="error")
        return
    serial = connected_list.item(sel[0], "values")[0]
    try:
        connected_list.clipboard_clear()
        connected_list.clipboard_append(serial)
        gui_log(f"Serial/IP copiado: {serial}", level="info")
    except Exception as e:
        gui_log(f"No se pudo copiar el serial/IP: {e}", level="error")


def create_connected_tab(notebook, refresh_available_callback=None):
    # --- Tab Conectados ---
    tab_connected = ttk.Frame(notebook)
    notebook.add(tab_connected, text="Conectados")
    frame_connected = ttk.Frame(tab_connected, padding=12, style="Dark.TFrame")
    frame_connected.pack(fill=tk.BOTH, expand=True)

    search_row = ttk.Frame(frame_connected, style="Dark.TFrame")
    search_row.pack(fill=tk.X, pady=(0, 6))
    tk.Label(search_row, text="Buscar:", bg="#1e1f22", fg="#b8ffb8").pack(side=tk.LEFT, padx=(0, 6))
    global connected_search_var
    connected_search_var = tk.StringVar()
    connected_search_entry = tk.Entry(search_row, textvariable=connected_search_var)
    connected_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

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

    connected_search_var.trace_add("write", lambda *_args: filter_connected_list())
    connected_list.bind("<Double-1>", lambda _event: shell_selected_device())

    btn_frame_connected = ttk.Frame(frame_connected, style="Dark.TFrame")
    btn_frame_connected.pack(fill=tk.X, pady=4)
    def refresh_all():
        refresh_connected_list()
        if refresh_available_callback:
            refresh_available_callback()

    ttk.Button(
        btn_frame_connected,
        text="Refrescar",
        command=refresh_all,
    ).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_connected, text="Desconectar", command=disconnect_selected_device).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_connected, text="Abrir Shell", command=shell_selected_device).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_frame_connected, text="Copiar Serial/IP", command=copy_selected_serial).pack(side=tk.LEFT, padx=4)

    return tab_connected
