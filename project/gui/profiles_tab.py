import os, json, tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
from ..config.config import DEVICES
from ..utils.adb_utils import exec_adb, run_in_thread
from ..utils.gui_utils import gui_log
from ..utils.net_utils import find_ip_from_mac
from ..gui.theme import force_dark

perfiles = {}
profile_listbox = None
detail_text = None

def create_profiles_tab(notebook):
    global profile_listbox, detail_text

    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Perfiles")

    # --- Frames principales ---
    per_left = ttk.Frame(tab, padding=8)
    per_left.grid(row=0, column=0, sticky="nsew")
    per_right = ttk.Frame(tab, padding=8)
    per_right.grid(row=0, column=1, sticky="nsew")

    tab.rowconfigure(0, weight=1)
    tab.columnconfigure(0, weight=3)
    tab.columnconfigure(1, weight=1)

    # --- Lista de perfiles ---
    list_frame = ttk.Frame(per_left)
    list_frame.grid(row=0, column=0, sticky="nsew")
    
    profile_listbox = tk.Listbox(list_frame, activestyle="dotbox")
    profile_listbox.grid(row=0, column=0, sticky="nsew")
    force_dark(profile_listbox)

    profile_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=profile_listbox.yview, style="Vertical.TScrollbar")
    #profile_scroll.grid(row=0, column=1, sticky="ns")
    profile_listbox.config(yscrollcommand=profile_scroll.set)

    list_frame.rowconfigure(0, weight=1)
    list_frame.columnconfigure(0, weight=1)
    per_left.rowconfigure(0, weight=1)
    per_left.columnconfigure(0, weight=1)

    # --- Detalle del perfil ---
    detail_label = ttk.Label(per_right, text="Detalles del perfil", font=(None, 10, "bold"))
    detail_label.grid(row=0, column=0, sticky="nw", pady=(0, 6))

    detail_text = tk.Text(per_right, width=30, height=10, state=tk.DISABLED, wrap=tk.WORD)
    detail_text.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
    force_dark(detail_text)

    # --- Botones ---
    button_frame = ttk.Frame(per_right)
    button_frame.grid(row=2, column=0, sticky="ew")
    button_frame.columnconfigure(0, weight=1)

    botones = [
        ("Añadir", lambda: prompt_add_profile()),
        ("Editar", lambda: edit_profile(get_selected_profile())),
        ("Borrar", lambda: delete_profile(get_selected_profile())),
        ("Conectar", lambda: connect_profile(get_selected_profile())),
        ("Desconectar", lambda: disconnect_profile(get_selected_profile())),
        ("Exportar", export_profiles),
        ("Importar", import_profiles),
    ]
    for i, (txt, cmd) in enumerate(botones):
        ttk.Button(button_frame, text=txt, command=cmd).grid(row=i, column=0, sticky="ew", pady=6)

    per_right.rowconfigure(1, weight=1)
    per_right.columnconfigure(0, weight=1)

    # --- Eventos ---
    profile_listbox.bind("<<ListboxSelect>>", lambda e: show_profile_details())

    load_profiles()
    refresh_profiles_list()
    return tab

# --- Lógica perfiles ---
def load_profiles():
    global perfiles
    if os.path.exists(DEVICES):
        try:
            with open(DEVICES, "r", encoding="utf-8") as f:
                perfiles = json.load(f)
        except Exception:
            perfiles = {}
    else:
        perfiles = {}

def save_profiles():
    try:
        with open(DEVICES, "w", encoding="utf-8") as f:
            json.dump(perfiles, f, indent=4, ensure_ascii=False)
    except Exception as e:
        gui_log(f"Error guardando perfiles: {e}", level="error")

def add_profile(name, mac, port=5555, ip=None, notes=None, color=None):
    perfiles[name] = {"mac": mac, "port": port, "ip": ip, "notes": notes, "color": color}
    save_profiles()
    refresh_profiles_list()
    gui_log(f"Perfil guardado: {name}")

def edit_profile(name):
    if not name or name not in perfiles:
        return
    perfil = perfiles[name]
    new_mac = simpledialog.askstring("Editar perfil", "MAC address:", initialvalue=perfil.get("mac", ""))
    if not new_mac: return
    new_port = simpledialog.askinteger("Editar perfil", "Puerto:", initialvalue=perfil.get("port", 5555))
    new_ip = simpledialog.askstring("Editar perfil", "IP fija:", initialvalue=perfil.get("ip", ""))
    new_notes = simpledialog.askstring("Editar perfil", "Notas:", initialvalue=perfil.get("notes", ""))
    perfiles[name].update({"mac": new_mac, "port": new_port, "ip": new_ip, "notes": new_notes})
    save_profiles()
    refresh_profiles_list()
    gui_log(f"Perfil '{name}' editado")

def delete_profile(name):
    if not name or name not in perfiles: return
    if messagebox.askyesno("Borrar perfil", f"¿Seguro que quieres borrar '{name}'?"):
        perfiles.pop(name)
        save_profiles()
        refresh_profiles_list()
        gui_log(f"Perfil '{name}' borrado")

def connect_profile(name):
    if not name or name not in perfiles: return
    perfil = perfiles[name]
    ip = perfil.get("ip") or find_ip_from_mac(perfil.get("mac"))
    if not ip:
        gui_log(f"No se encontró IP para {perfil.get('mac')}", level="error")
        return
    port = perfil.get("port", 5555)
    run_in_thread(lambda: exec_adb(["connect", f"{ip}:{port}"]))

def disconnect_profile(name):
    if not name or name not in perfiles: return
    perfil = perfiles[name]
    ip = perfil.get("ip") or find_ip_from_mac(perfil.get("mac"))
    if not ip:
        gui_log(f"No se encontró IP para {perfil.get('mac')}", level="error")
        return
    port = perfil.get("port", 5555)
    run_in_thread(lambda: exec_adb(["disconnect", f"{ip}:{port}"]))
    gui_log(f"Desconectando {name} ({ip}:{port})")

def export_profiles():
    if not perfiles: return
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON","*.json")])
    if not path: return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(perfiles, f, indent=4, ensure_ascii=False)
    gui_log(f"Perfiles exportados a {path}")

def import_profiles():
    path = filedialog.askopenfilename(filetypes=[("JSON","*.json")])
    if not path: return
    try:
        with open(path, "r", encoding="utf-8") as f:
            perfiles.update(json.load(f))
        save_profiles()
        refresh_profiles_list()
        gui_log("Perfiles importados.")
    except Exception as e:
        gui_log(f"Error importando: {e}", level="error")

# --- UI helpers ---
def prompt_add_profile():
    name = simpledialog.askstring("Nuevo perfil", "Nombre del perfil:")
    if not name: return
    mac = simpledialog.askstring("Nuevo perfil", "MAC address:")
    if not mac: return
    port = simpledialog.askinteger("Nuevo perfil", "Puerto:", initialvalue=5555)
    ip = simpledialog.askstring("Nuevo perfil", "IP fija:")
    notes = simpledialog.askstring("Nuevo perfil", "Notas:")
    add_profile(name, mac, port, ip, notes)

def get_selected_profile():
    sel = profile_listbox.curselection()
    return profile_listbox.get(sel[0]) if sel else None

def refresh_profiles_list():
    profile_listbox.delete(0, tk.END)
    for name in perfiles:
        profile_listbox.insert(tk.END, name)

def show_profile_details():
    name = get_selected_profile()
    detail_text.config(state=tk.NORMAL)
    detail_text.delete(1.0, tk.END)
    if name and name in perfiles:
        p = perfiles[name]
        txt = f"Nombre: {name}\nMAC: {p.get('mac')}\nIP: {p.get('ip')}\nPuerto: {p.get('port')}\nNotas: {p.get('notes','')}\n"
        detail_text.insert(tk.END, txt)
    detail_text.config(state=tk.DISABLED)
