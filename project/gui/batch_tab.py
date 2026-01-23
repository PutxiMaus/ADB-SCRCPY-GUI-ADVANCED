import os
import subprocess
import sys
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

    batch_frame.rowconfigure(3, weight=3)
    batch_frame.rowconfigure(5, weight=1)
    batch_frame.columnconfigure(0, weight=1)
    for col in range(1, 6):
        batch_frame.columnconfigure(col, weight=0)

    # --- ComboBox ---
    batch_var = tk.StringVar()
    batch_combobox = ttk.Combobox(batch_frame, textvariable=batch_var, state="readonly", width=60)
    batch_combobox.grid(row=0, column=0, columnspan=6, padx=6, pady=6, sticky="ew")

    # 🔹 Vincular selección al editor
    batch_combobox.bind("<<ComboboxSelected>>", lambda e: load_batch())

    batch_note = ttk.Label(batch_frame, text="Añade .bat en 'project/utils/batch' si quieres añadirlos manualmente.", font=(None, 8))
    batch_note.grid(row=1, column=0, columnspan=6, pady=(0, 2), sticky="w")

    status_frame = ttk.Frame(batch_frame)
    status_frame.grid(row=2, column=0, columnspan=6, sticky="ew", padx=6)
    status_frame.columnconfigure(0, weight=1)
    status_label = ttk.Label(status_frame, text="Sin cambios", font=(None, 9))
    status_label.grid(row=0, column=0, sticky="w")
    file_count_label = ttk.Label(status_frame, text="0 archivos", font=(None, 9))
    file_count_label.grid(row=0, column=1, sticky="e")

    # --- Editor ---
    editor = tk.Text(batch_frame, wrap="word", background="#202225", foreground="#ffffff", font=("Consolas", 10))
    editor.grid(row=3, column=0, columnspan=6, sticky="nsew", padx=6, pady=6)

    scroll_editor = ttk.Scrollbar(batch_frame, orient=tk.VERTICAL, command=editor.yview)
    editor.config(yscrollcommand=scroll_editor.set)
    # scroll_editor.grid(row=3, column=6, sticky="ns")  # Si quieres invisible

    output_label = ttk.Label(batch_frame, text="Salida del batch", font=(None, 9))
    output_label.grid(row=4, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 2))
    output = tk.Text(batch_frame, wrap="word", height=6, background="#1d1f21", foreground="#cfd2d6", font=("Consolas", 9), state="disabled")
    output.grid(row=5, column=0, columnspan=6, sticky="nsew", padx=6, pady=(0, 6))

    scroll_output = ttk.Scrollbar(batch_frame, orient=tk.VERTICAL, command=output.yview)
    output.config(yscrollcommand=scroll_output.set)
    # scroll_output.grid(row=5, column=6, sticky="ns")

    dirty = {"value": False}
    current_file = {"value": ""}

    # --- Funciones internas ---
    def set_dirty(value):
        dirty["value"] = value
        status_label.config(text="● Cambios sin guardar" if value else "Sin cambios")

    def update_file_count(count):
        label = "archivo" if count == 1 else "archivos"
        file_count_label.config(text=f"{count} {label}")

    def refresh_batch_files():
        try:
            files = sorted([f for f in os.listdir(BATCH_DIR) if f.lower().endswith('.bat')])
        except Exception:
            files = []
        batch_combobox['values'] = files
        update_file_count(len(files))
        if files:
            batch_combobox.current(0)
            load_batch()
        else:
            editor.delete("1.0","end")
            editor.insert("1.0", "No hay batches. Usa 'Crear' para añadir uno nuevo.\n")
            set_dirty(False)
            current_file["value"] = ""
            toggle_action_buttons(False)
            clear_output()

    def load_batch():
        if dirty["value"] and not confirm_discard_changes():
            batch_var.set(current_file["value"])
            return
        file = batch_var.get()
        if not file: return
        path = os.path.join(BATCH_DIR, file)
        if not os.path.exists(path): return
        with open(path,"r",encoding="utf-8", errors="ignore") as f:
            editor.delete("1.0","end")
            editor.insert("1.0", f.read())
        editor.edit_modified(False)
        set_dirty(False)
        current_file["value"] = file
        toggle_action_buttons(True)
        clear_output()

    def save_batch():
        file = batch_var.get()
        if not file:
            gui_log("Selecciona un archivo o crea uno nuevo", level="error")
            return
        path = os.path.join(BATCH_DIR,file)
        with open(path,"w",encoding="utf-8") as f:
            f.write(editor.get("1.0","end"))
        editor.edit_modified(False)
        set_dirty(False)
        gui_log(f"Guardado: {file}", level="info")

    def validate_batch_name(name):
        invalid = set('<>:"/\\|?*')
        if any(ch in invalid for ch in name):
            gui_log("Nombre inválido. Evita <>:\"/\\|?*", level="error")
            return False
        return True

    def create_batch():
        name = simpledialog.askstring("Nuevo .bat","Nombre del archivo (sin .bat):")
        if not name: return
        if not validate_batch_name(name):
            return
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

    def duplicate_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        new_name = simpledialog.askstring("Duplicar batch", "Nombre del nuevo archivo (sin .bat):")
        if not new_name: return
        if not validate_batch_name(new_name):
            return
        if not new_name.lower().endswith(".bat"):
            new_name += ".bat"
        src = os.path.join(BATCH_DIR, file)
        dest = os.path.join(BATCH_DIR, new_name)
        if os.path.exists(dest) and not messagebox.askyesno("Sobrescribir", f"{new_name} ya existe. ¿Sobrescribir?"):
            return
        with open(src, "r", encoding="utf-8", errors="ignore") as f_src:
            content = f_src.read()
        with open(dest, "w", encoding="utf-8") as f_dest:
            f_dest.write(content)
        refresh_batch_files()
        batch_var.set(new_name)
        load_batch()
        gui_log(f"Duplicado: {new_name}", level="info")

    def rename_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        if dirty["value"] and not confirm_save_changes():
            return
        new_name = simpledialog.askstring("Renombrar batch", "Nuevo nombre (sin .bat):")
        if not new_name: return
        if not validate_batch_name(new_name):
            return
        if not new_name.lower().endswith(".bat"):
            new_name += ".bat"
        src = os.path.join(BATCH_DIR, file)
        dest = os.path.join(BATCH_DIR, new_name)
        if os.path.exists(dest):
            gui_log("Ya existe un archivo con ese nombre", level="error")
            return
        try:
            os.rename(src, dest)
        except Exception as exc:
            gui_log(f"Error renombrando {file}: {exc}", level="error")
            return
        refresh_batch_files()
        batch_var.set(new_name)
        load_batch()
        gui_log(f"Renombrado: {new_name}", level="info")

    def delete_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        if dirty["value"] and not confirm_discard_changes():
            return
        if not messagebox.askyesno("Borrar", f"¿Borrar {file}?"):
            return
        path = os.path.join(BATCH_DIR,file)
        try: os.remove(path)
        except Exception as e:
            gui_log(f"Error borrando {file}: {e}", level="error")
        refresh_batch_files()
        gui_log(f"Borrado: {file}", level="info")

    def confirm_save_changes():
        if not dirty["value"]:
            return True
        answer = messagebox.askyesnocancel("Guardar cambios", "Tienes cambios sin guardar. ¿Quieres guardarlos?")
        if answer is None:
            return False
        if answer:
            save_batch()
        return True

    def confirm_discard_changes():
        if not dirty["value"]:
            return True
        return messagebox.askyesno("Descartar cambios", "Tienes cambios sin guardar. ¿Descartar cambios?")

    def toggle_action_buttons(enabled):
        state = "normal" if enabled else "disabled"
        for button in action_buttons:
            button.config(state=state)

    def clear_output():
        output.config(state="normal")
        output.delete("1.0", "end")
        output.config(state="disabled")

    def append_output(text, level="info"):
        output.config(state="normal")
        output.insert("end", f"[{level.upper()}] {text}\n")
        output.see("end")
        output.config(state="disabled")

    def run_batch():
        file = batch_var.get()
        if not file:
            gui_log("No hay batch seleccionado", level="error")
            return
        if dirty["value"] and not confirm_save_changes():
            return
        path = os.path.join(BATCH_DIR,file)
        if not os.path.exists(path):
            gui_log("El batch seleccionado no existe", level="error")
            return
        gui_log(f"▶️ Ejecutando batch: {file}", level="cmd")
        clear_output()

        def worker():
            try:
                proc = subprocess.Popen(path, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = proc.communicate()
                if out: gui_log(out.strip(), level="info")
                if err: gui_log(err.strip(), level="error")
                if out: append_output(out.strip(), level="info")
                if err: append_output(err.strip(), level="error")
                append_output(f"Código de salida: {proc.returncode}", level="info")
            except Exception as e:
                gui_log(f"Error ejecutando batch: {e}", level="error")
                append_output(f"Error ejecutando batch: {e}", level="error")

        run_in_thread(worker)

    def open_batch_folder():
        path = str(BATCH_DIR)
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", path], check=False)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as exc:
            gui_log(f"No se pudo abrir la carpeta: {exc}", level="error")

    def on_editor_modified(event=None):
        if editor.edit_modified():
            set_dirty(True)
            editor.edit_modified(False)

    editor.bind("<<Modified>>", on_editor_modified)

    # --- Botones ---
    btn_texts = [
        ("Ejecutar", run_batch),
        ("Refrescar", refresh_batch_files),
        ("Guardar", save_batch),
        ("Crear", create_batch),
        ("Duplicar", duplicate_batch),
        ("Renombrar", rename_batch),
        ("Borrar", delete_batch),
        ("Abrir carpeta", open_batch_folder),
    ]

    action_buttons = []
    for i, (txt, cmd) in enumerate(btn_texts):
        button = ttk.Button(batch_frame, text=txt, command=cmd)
        button.grid(row=6, column=i % 6, padx=4, pady=4, sticky="ew")
        if txt in {"Ejecutar", "Guardar", "Duplicar", "Renombrar", "Borrar"}:
            action_buttons.append(button)
        batch_frame.columnconfigure(i, weight=1)

    # Inicializar
    refresh_batch_files()
    return tab_batch
