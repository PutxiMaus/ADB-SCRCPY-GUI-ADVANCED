import os, tkinter as tk
from tkinter import ttk
from ..utils.adb_utils import exec_adb, run_in_thread
from ..utils.gui_utils import gui_log

# historiales de navegación
local_history = []
android_history = []

def create_explorer_tab(notebook):
    tab_explorer = ttk.Frame(notebook)
    notebook.add(tab_explorer, text="Explorador")

    exp_frame = ttk.Frame(tab_explorer, padding=8)
    exp_frame.pack(fill="both", expand=True)
    exp_frame.rowconfigure(0, weight=1)
    exp_frame.rowconfigure(1, weight=0)
    exp_frame.columnconfigure(0, weight=1)
    exp_frame.columnconfigure(1, weight=1)

    # =============================
    # PANEL IZQUIERDO (PC)
    # =============================
    left_frame = ttk.Frame(exp_frame, padding=6, style="Dark.TFrame")
    left_frame.grid(row=0, column=0, sticky="nsew")

    tk.Label(left_frame, text="PC - Sistema de archivos", background="#313338", foreground="#ffffff").pack(anchor="w")

    local_path_var = tk.StringVar(value=os.path.expanduser("~"))
    local_path_label = tk.Label(left_frame, text=local_path_var.get(), background="#313338", foreground="#ffffff")
    local_path_label.pack(fill="x")

    local_search_var = tk.StringVar()
    local_search_entry = tk.Entry(left_frame, textvariable=local_search_var)
    local_search_entry.pack(fill="x", pady=2)

    nav_frame_pc = ttk.Frame(left_frame)
    nav_frame_pc.pack(fill="x", pady=2)
    btn_back_local = ttk.Button(nav_frame_pc, text="Atrás")
    btn_up_local = ttk.Button(nav_frame_pc, text="Arriba")
    btn_back_local.pack(side="left", padx=2)
    btn_up_local.pack(side="left", padx=2)

    local_tree = ttk.Treeview(left_frame, columns=("name","type","size"), show="headings")
    local_tree.heading("name", text="Nombre")
    local_tree.heading("type", text="Tipo")
    local_tree.heading("size", text="Tamaño")
    local_tree.tag_configure('evenrow', background='#3a3a3a', foreground='#ffffff')
    local_tree.tag_configure('oddrow', background='#2e2e2e', foreground='#ffffff')
    local_tree.pack(fill="both", expand=True, side="left")

    scroll_y_local = ttk.Scrollbar(left_frame, orient="vertical", command=local_tree.yview)
    local_tree.configure(yscrollcommand=scroll_y_local.set)
    scroll_y_local.pack(side="right", fill="y")

    # =============================
    # PANEL DERECHO (ANDROID)
    # =============================
    right_frame = ttk.Frame(exp_frame, padding=6, style="Dark.TFrame")
    right_frame.grid(row=0, column=1, sticky="nsew")

    tk.Label(right_frame, text="Android - Sistema de archivos", background="#313338", foreground="#ffffff").pack(anchor="w")

    android_path_var = tk.StringVar(value="/sdcard")
    android_path_label = tk.Label(right_frame, text=android_path_var.get(), background="#313338", foreground="#ffffff")
    android_path_label.pack(fill="x")

    android_search_var = tk.StringVar()
    android_search_entry = tk.Entry(right_frame, textvariable=android_search_var)
    android_search_entry.pack(fill="x", pady=2)

    nav_frame_android = ttk.Frame(right_frame)
    nav_frame_android.pack(fill="x", pady=2)
    btn_back_android = ttk.Button(nav_frame_android, text="Atrás")
    btn_up_android = ttk.Button(nav_frame_android, text="Arriba")
    btn_back_android.pack(side="left", padx=2)
    btn_up_android.pack(side="left", padx=2)

    android_tree = ttk.Treeview(right_frame, columns=("name","type","size"), show="headings")
    android_tree.heading("name", text="Nombre")
    android_tree.heading("type", text="Tipo")
    android_tree.heading("size", text="Tamaño")
    android_tree.tag_configure('evenrow', background='#3a3a3a', foreground='#ffffff')
    android_tree.tag_configure('oddrow', background='#2e2e2e', foreground='#ffffff')
    android_tree.pack(fill="both", expand=True, side="left")

    scroll_y_android = ttk.Scrollbar(right_frame, orient="vertical", command=android_tree.yview)
    android_tree.configure(yscrollcommand=scroll_y_android.set)
    scroll_y_android.pack(side="right", fill="y")

    # =============================
    # FUNCIONES DE LISTADO
    # =============================
    def list_local(path):
        try:
            local_tree.delete(*local_tree.get_children())
            items = os.listdir(path)
            for i, name in enumerate(items):
                full = os.path.join(path, name)
                t = "Dir" if os.path.isdir(full) else "File"
                s = str(os.path.getsize(full)) if os.path.isfile(full) else ""
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                local_tree.insert("", "end", values=(name, t, s), tags=(tag,))
            local_path_label.config(text=path)
        except Exception as e:
            gui_log(f"Error listando local: {e}", level="error")

    def adb_list(path):
        try:
            out = exec_adb(["shell", "ls", "-1", "-p", path])
            android_tree.delete(*android_tree.get_children())
            for i, line in enumerate(out.splitlines()):
                t = "Dir" if line.endswith("/") else "File"
                name = line.rstrip("/")
                tag = 'evenrow' if i % 2 == 0 else 'oddrow'
                android_tree.insert("", "end", values=(name, t, ""), tags=(tag,))
            android_path_label.config(text=path)
        except Exception as e:
            gui_log(f"Error listando android: {e}", level="error")

    # =============================
    # TRANSFERENCIA
    # =============================
    def upload_to_device():
        sel = local_tree.selection()
        if not sel:
            gui_log("Selecciona un archivo local para subir", level="error")
            return
        name = local_tree.item(sel[0])["values"][0]
        src = os.path.join(local_path_var.get(), name)
        dst = android_path_var.get().rstrip("/") + "/" + name
        def worker():
            gui_log(f"SUBIENDO {src} -> {dst}", level="cmd")
            out = exec_adb(["push", src, dst])
            gui_log(out)
            adb_list(android_path_var.get())
        run_in_thread(worker)

    def download_from_device():
        sel = android_tree.selection()
        if not sel:
            gui_log("Selecciona un archivo del dispositivo para descargar", level="error")
            return
        name = android_tree.item(sel[0])["values"][0]
        src = android_path_var.get().rstrip("/") + "/" + name
        dst = os.path.join(local_path_var.get(), name)
        def worker():
            gui_log(f"DESCARGANDO {src} -> {dst}", level="cmd")
            out = exec_adb(["pull", src, dst])
            gui_log(out)
            list_local(local_path_var.get())
        run_in_thread(worker)

    # =============================
    # NAVEGACIÓN
    # =============================
    def open_local_dir(event):
        sel = local_tree.selection()
        if not sel: return
        name, t, _ = local_tree.item(sel[0])["values"]
        if t == "Dir":
            curr = local_path_var.get()
            local_history.append(curr)
            new_path = os.path.join(curr, name)
            local_path_var.set(new_path)
            list_local(new_path)

    def open_android_dir(event):
        sel = android_tree.selection()
        if not sel: return
        name, t, _ = android_tree.item(sel[0])["values"]
        if t == "Dir":
            curr = android_path_var.get().rstrip("/")
            android_history.append(curr)
            new_path = curr + "/" + name
            android_path_var.set(new_path)
            adb_list(new_path)

    local_tree.bind("<Double-1>", open_local_dir)
    android_tree.bind("<Double-1>", open_android_dir)

    def go_back_local():
        if local_history:
            prev = local_history.pop()
            local_path_var.set(prev)
            list_local(prev)

    def go_up_local():
        curr = local_path_var.get()
        parent = os.path.dirname(curr)
        if parent and parent != curr:
            local_history.append(curr)
            local_path_var.set(parent)
            list_local(parent)

    def go_back_android():
        if android_history:
            prev = android_history.pop()
            android_path_var.set(prev)
            adb_list(prev)

    def go_up_android():
        curr = android_path_var.get().rstrip("/")
        parent = "/".join(curr.split("/")[:-1])
        if parent:
            android_history.append(curr)
            android_path_var.set(parent)
            adb_list(parent)

    btn_back_local.config(command=go_back_local)
    btn_up_local.config(command=go_up_local)
    btn_back_android.config(command=go_back_android)
    btn_up_android.config(command=go_up_android)

    # =============================
    # BOTONES DE TRANSFERENCIA
    # =============================
    btns_frame = ttk.Frame(exp_frame, padding=6)
    btns_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

    ttk.Button(btns_frame, text="Refrescar PC", command=lambda: list_local(local_path_var.get())).grid(row=0, column=0, padx=5, pady=2, sticky="ew")
    ttk.Button(btns_frame, text="Subir →", command=upload_to_device).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
    ttk.Button(btns_frame, text="← Descargar", command=download_from_device).grid(row=0, column=2, padx=5, pady=2, sticky="ew")
    ttk.Button(btns_frame, text="Refrescar Android", command=lambda: adb_list(android_path_var.get())).grid(row=0, column=3, padx=5, pady=2, sticky="ew")

    for i in range(4):
        btns_frame.columnconfigure(i, weight=1)

    # =============================
    # BÚSQUEDA
    # =============================
    def filter_local(*args):
        search = local_search_var.get().lower()
        for item in local_tree.get_children():
            name = local_tree.item(item)["values"][0].lower()
            if search in name:
                local_tree.reattach(item, '', 'end')
            else:
                local_tree.detach(item)
    local_search_var.trace_add("write", filter_local)

    def filter_android(*args):
        search = android_search_var.get().lower()
        for item in android_tree.get_children():
            name = android_tree.item(item)["values"][0].lower()
            if search in name:
                android_tree.reattach(item, '', 'end')
            else:
                android_tree.detach(item)
    android_search_var.trace_add("write", filter_android)

    # =============================
    # ESTILOS
    # =============================
    style = ttk.Style()
    style.theme_use('clam')
    style.configure("Dark.TFrame")
    style.configure("Treeview")
    style.configure("Treeview.Heading")
    style.configure("TButton")
    style.configure("TEntry")

    local_search_entry.configure(background="#3a3a3a", foreground="#ffffff")
    android_search_entry.configure(background="#3a3a3a", foreground="#ffffff")

    # =============================
    # REFRESCO AL CAMBIAR DE PESTAÑA
    # =============================
    def on_tab_change(event):
        tab_id = event.widget.select()
        if event.widget.tab(tab_id, "text") == "Explorador":
            list_local(local_path_var.get())
            adb_list(android_path_var.get())

    notebook.bind("<<NotebookTabChanged>>", on_tab_change)

    return tab_explorer