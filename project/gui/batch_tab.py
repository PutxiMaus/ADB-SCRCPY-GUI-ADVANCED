import os
import subprocess
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from ..utils.adb_utils import run_in_thread
from ..utils.gui_utils import gui_log
from ..config.config import PROJECT_ROOT

BATCH_DIR = PROJECT_ROOT / "utils" / "batch"

def create_batch_tab(notebook):
    tab_batch = ttk.Frame(notebook)
    notebook.add(tab_batch, text="Batch")

    batch_frame = ttk.Frame(tab_batch, padding=12)
    batch_frame.grid(row=0, column=0, sticky="nsew")

    tab_batch.rowconfigure(0, weight=1)
    tab_batch.columnconfigure(0, weight=1)

    batch_frame.rowconfigure(2, weight=1)
    batch_frame.columnconfigure(0, weight=1)

    # --- ComboBox ---
    batch_var = tk.StringVar()
    batch_combobox = ttk.Combobox(batch_frame, textvariable=batch_var, state="readonly", width=60)
    batch_combobox.grid(row=0, column=0, columnspan=6, padx=6, pady=6, sticky="ew")

    batch_note = ttk.Label(batch_frame, text="Añade .bat en 'project/utils/batch' si quieres añadirlos manualmente.", font=(None, 8))
    batch_note.grid(row=1, column=0, columnspan=6, pady=(0,6), sticky="w")

    # --- Editor ---
    editor = tk.Text(batch_frame, wrap="word", background="#202225", foreground="#ffffff", font=("Consolas",10))
    editor.grid(row=2, column=0, columnspan=6, sticky="nsew", padx=6, pady=6)

    scroll_editor = ttk.Scrollbar(batch_frame, orient=tk.VERTICAL, command=editor.yview)
    editor.config(yscrollcommand=scroll_editor.set)
    # scroll_editor.grid(row=2, column=6, sticky="ns")  # Si quieres invisible

    # --- Funciones internas ---
    def refresh_batch_files():
        try:
            files = [f for f in os.listdir(BATCH_DIR) if f.lower().endswith('.bat')]
        except Exception:
            files = []
        batch_combobox['values'] = files
        if files:
            batch_combobox.current(0)
            load_batch()
        else:
            editor.delete("1.0","end")

    def load_batch():
        file = batch_var.get()
        if not file: return
        path = os.path.join(BATCH_DIR, file)
        if not os.path.exists(path): return
        with open(path,"r",encoding="utf-8", errors="ignore") as f:
            editor.delete("1.0","end")
            editor.insert("1.0", f.read())

    def save_batch():
        file = batch_var.get()
        if not file:
            gui_log("Selecciona un archivo o crea uno nuevo", level="error")
            return
        path = os.path.join(BATCH_DIR,file)
        with open(path,"w",encoding="utf-8") as f:
            f.write(editor.get("1.0","end"))
        gui_log(f"Guardado: {file}", level="info")

    def create_batch():
        name = simpledialog.askstring("Nuevo .bat","Nombre del archivo (sin .bat):")
        if not name: return
        if not name.lower().endswith(".bat"):
            name += ".bat"
        path = os.path.join(BATCH_DIR,name)
        if os.path.exists(path) and not messagebox.askyesno("Sobrescribir", f"{name} ya existe. ¿Sobrescribir?"):
            return
        with open(path,"w",encoding="utf-8") as f:
            f.write(":: Nuevo archivo batch\n")
        refresh_batch_files()
        batch_var.set(name)
        load_batch()
        gui_log(f"Creado: {name}", level="info")

    def delete_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        if not messagebox.askyesno("Borrar", f"¿Borrar {file}?"):
            return
        path = os.path.join(BATCH_DIR,file)
        try: os.remove(path)
        except Exception as e:
            gui_log(f"Error borrando {file}: {e}", level="error")
        refresh_batch_files()
        gui_log(f"Borrado: {file}", level="info")

    def run_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        path = os.path.join(BATCH_DIR,file)
        if not os.path.exists(path):
            gui_log("El batch seleccionado no existe", level="error")
            return
        gui_log(f"▶️ Ejecutando batch: {file}", level="cmd")

        def worker():
            try:
                proc = subprocess.Popen(path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate()
                if out: gui_log(out.strip(), level="info")
                if err: gui_log(err.strip(), level="error")
            except Exception as e:
                gui_log(f"Error ejecutando batch: {e}", level="error")

        run_in_thread(worker)

    # --- Botones ---
    btn_texts = [("Ejecutar", run_batch), ("Refrescar", refresh_batch_files), ("Guardar", save_batch), ("Crear", create_batch), ("Borrar", delete_batch)]

    for i, (txt, cmd) in enumerate(btn_texts):
        ttk.Button(batch_frame, text=txt, command=cmd).grid(row=3, column=i, padx=4, pady=4, sticky="ew")
        batch_frame.columnconfigure(i, weight=1)

    # Inicializar
    refresh_batch_files()
    return tab_batch
