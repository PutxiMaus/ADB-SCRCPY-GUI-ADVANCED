import tkinter as tk
from tkinter import ttk

from ..utils.adb_utils import run_adb, run_in_thread
from ..utils.gui_utils import gui_log

_connected_tree = None
_status_var = None
_loading = False
_last_empty_notice = False


def _parse_device_detail(tokens):
    parsed = {}
    extra = []
    for token in tokens:
        if ":" in token:
            key, value = token.split(":", 1)
            parsed[key] = value
        else:
            extra.append(token)
    return parsed, " ".join(extra)


def _parse_adb_devices(output):
    devices = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue
        parts = line.split()
        serial = parts[0]
        status = parts[1] if len(parts) > 1 else ""
        detail_tokens = parts[2:] if len(parts) > 2 else []
        parsed, detail = _parse_device_detail(detail_tokens)
        model = parsed.get("model", "")
        device = parsed.get("device", "")
        transport = parsed.get("transport_id", "")
        devices.append((serial, status, model, device, transport, detail))
    return devices


def _update_connected_tree(devices):
    if _connected_tree is None:
        return
    _connected_tree.delete(*_connected_tree.get_children())
    for serial, status, model, device, transport, detail in devices:
        _connected_tree.insert("", "end", values=(serial, status, model, device, transport, detail))


def _set_status(message):
    if _status_var is not None:
        _status_var.set(message)


def _set_loading(state):
    global _loading
    _loading = state


def refresh_connected_list():
    global _last_empty_notice
    if _connected_tree is None:
        return

    if _loading:
        return
    _set_loading(True)
    _set_status("Cargando dispositivos ADB...")

    def worker():
        output = run_adb(["devices", "-l"])
        devices = _parse_adb_devices(output)
        has_error = "error" in output.lower() if output else True
        if has_error:
            _connected_tree.after(0, lambda: _set_status("No se pudo obtener la lista de dispositivos."))
        elif not devices:
            if not _last_empty_notice:
                gui_log("No hay dispositivos ADB conectados.", level="info")
                _last_empty_notice = True
            _connected_tree.after(0, lambda: _set_status("Sin dispositivos conectados."))
        else:
            _last_empty_notice = False
            _connected_tree.after(0, lambda: _set_status(f"{len(devices)} dispositivo(s) detectado(s)."))
        _connected_tree.after(0, lambda: _update_connected_tree(devices))
        _connected_tree.after(0, lambda: _set_loading(False))

    run_in_thread(worker)


def create_connected_tab(notebook, refresh_available_callback=None):
    global _connected_tree, _status_var

    tab = ttk.Frame(notebook, padding=8)
    notebook.add(tab, text="Conectados")

    header = ttk.Label(tab, text="Dispositivos conectados", font=(None, 11, "bold"))
    header.grid(row=0, column=0, sticky="w", pady=(0, 8))

    controls = ttk.Frame(tab)
    controls.grid(row=1, column=0, sticky="ew")
    controls.columnconfigure(0, weight=1)

    ttk.Button(controls, text="Refrescar", command=refresh_connected_list).grid(row=0, column=0, sticky="w")
    if refresh_available_callback:
        ttk.Button(controls, text="Actualizar red", command=refresh_available_callback).grid(row=0, column=1, sticky="w", padx=(6, 0))

    tree = ttk.Treeview(
        tab,
        columns=("serial", "status", "model", "device", "transport", "detail"),
        show="headings",
    )
    tree.heading("serial", text="Serial")
    tree.heading("status", text="Estado")
    tree.heading("model", text="Modelo")
    tree.heading("device", text="Device")
    tree.heading("transport", text="Transport")
    tree.heading("detail", text="Detalle")

    tree.column("serial", width=180, anchor="w")
    tree.column("status", width=80, anchor="center")
    tree.column("model", width=140, anchor="w")
    tree.column("device", width=140, anchor="w")
    tree.column("transport", width=90, anchor="center")
    tree.column("detail", width=240, anchor="w")

    tree.grid(row=2, column=0, sticky="nsew", pady=(8, 0))

    scrollbar = ttk.Scrollbar(tab, orient="vertical", command=tree.yview, style="Vertical.TScrollbar")
    tree.configure(yscrollcommand=scrollbar.set)
    scrollbar.grid(row=2, column=1, sticky="ns", pady=(8, 0))

    _status_var = tk.StringVar(value="")
    status_label = ttk.Label(tab, textvariable=_status_var)
    status_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

    tab.columnconfigure(0, weight=1)
    tab.rowconfigure(2, weight=1)

    _connected_tree = tree

    return tab
