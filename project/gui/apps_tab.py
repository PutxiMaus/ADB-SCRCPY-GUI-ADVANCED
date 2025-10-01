import subprocess, tempfile, threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from ..utils.adb_utils import exec_adb, run_in_thread, run_adb
from ..utils.gui_utils import gui_log
from ..config.config import TOOLS_DIR

# cache y flag global
label_cache = {}
stop_flag = False


# =====================
# FUNCIONES NIVEL SUPERIOR
# =====================
def get_app_label(package, is_user_app=False):
    if package in label_cache:
        return label_cache[package]

    label = package  # por defecto

    if is_user_app:
        try:
            output = run_adb(["shell", "pm", "path", package]).strip()
            if output.startswith("package:"):
                apk_path = output.replace("package:", "")
                temp_dir = Path(tempfile.gettempdir())
                local_apk = temp_dir / f"temp_{package.replace('.', '_')}.apk"

                run_adb(["pull", apk_path, str(local_apk)])

                aapt_path = TOOLS_DIR / "aapt.exe"
                result = subprocess.run(
                    [str(aapt_path), "dump", "badging", str(local_apk)],
                    capture_output=True, text=True, encoding="utf-8", errors="ignore"
                )
                for line in result.stdout.splitlines():
                    if "application-label:" in line:
                        cleaned = ''.join(
                            c for c in line.split("application-label:")[1]
                            if c.isalpha() or c.isspace()
                        ).strip()
                        if cleaned:
                            label = cleaned
                            break
        except Exception as e:
            print(f"Error aapt para {package}: {e}")
        finally:
            if 'local_apk' in locals() and local_apk.exists():
                local_apk.unlink()

    label_cache[package] = label
    return label

def listar_paquetes(tree_widget):
    global stop_flag
    stop_flag = False
    tree_widget.delete(*tree_widget.get_children())

    system_output = run_adb(["shell", "pm", "list", "packages", "-s"])
    user_output = run_adb(["shell", "pm", "list", "packages", "-3"])
    system_packages = [p.replace("package:", "").strip() for p in system_output.splitlines()]
    user_packages = [p.replace("package:", "").strip() for p in user_output.splitlines()]
    paquetes = user_packages + system_packages

    for paquete in paquetes:
        tag = "system" if paquete in system_packages else "user"
        if tag == "user":
            tree_widget.insert("", "end", values=(paquete, "Cargando..."), tags=(tag,))
        else:
            tree_widget.insert("", "end", values=(paquete, paquete), tags=(tag,))

    def update_labels():
        for iid in tree_widget.get_children():
            if stop_flag:
                break
            paquete = tree_widget.item(iid)["values"][0]
            is_user = "user" in tree_widget.item(iid)["tags"]
            if is_user:
                label = get_app_label(paquete, is_user_app=True)
                tree_widget.item(iid, values=(paquete, label))
            tree_widget.update_idletasks()

    threading.Thread(target=update_labels, daemon=True).start()

def run_listar_paquetes(tree):
    threading.Thread(target=listar_paquetes, args=(tree,), daemon=True).start()

def detener_busqueda():
    global stop_flag
    stop_flag = True

def open_app(package):
    run_in_thread(lambda: exec_adb([
        "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"
    ]))

def close_app(package):
    def task():
        exec_adb(["shell", "am", "force-stop", package])
        exec_adb(["shell", "am", "kill", package])
        exec_adb(["shell", "cmd", "activity", "clear-recent-apps"])
    run_in_thread(task)

def open_selected_app(tree):
    selected = tree.selection()
    if selected:
        pkg = tree.item(selected[0])["values"][0]
        open_app(pkg)

def close_selected_app(tree):
    selected = tree.selection()
    if selected:
        pkg = tree.item(selected[0])["values"][0]
        close_app(pkg)

def copy_base_apk_path(tree, tab_apps):
    selected = tree.selection()
    if not selected:
        gui_log("Selecciona una app primero", level="error")
        return
    pkg = tree.item(selected[0])["values"][0]
    path_output = run_adb(["shell", "pm", "path", pkg]).strip()
    apk_paths = [line.replace("package:", "") for line in path_output.splitlines()]
    base_apk = next((p for p in apk_paths if p.endswith("base.apk")), None)

    if base_apk:
        tab_apps.clipboard_clear()
        tab_apps.clipboard_append(base_apk)
        gui_log(f"Ruta base.apk copiada: {base_apk}", level="info")
    else:
        gui_log("No se encontró base.apk para esta app", level="error")

# =====================
# FUNCION PRINCIPAL
# =====================
def create_apps_tab(notebook):
    global stop_flag
    tab_apps = ttk.Frame(notebook)
    notebook.add(tab_apps, text="Apps del dispositivo")

    # --- Treeview para listar apps ---
    tree = ttk.Treeview(tab_apps, columns=("package", "label"), show="headings")
    tree.heading("package", text="Paquete")
    tree.heading("label", text="Nombre")
    tree.pack(fill="both", expand=True, padx=10, pady=10)
    tree.tag_configure("system", background="#483334", foreground="white")
    tree.tag_configure("user", background="#3a4535", foreground="white")

    # =====================
    # BOTONES
    # =====================
    btn_frame = ttk.Frame(tab_apps)
    btn_frame.pack(fill="x", pady=5)

    ttk.Button(btn_frame, text="Buscar Apps", command=lambda: run_listar_paquetes(tree)).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Abrir App Seleccionada", command=lambda: open_selected_app(tree)).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Cerrar Apps", command=lambda: close_selected_app(tree)).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Detener Busqueda", command=detener_busqueda).pack(side="left", padx=5)
    ttk.Button(btn_frame, text="Copiar Ruta", command=lambda: copy_base_apk_path(tree, tab_apps)).pack(side="left", padx=5)

    return tab_apps
