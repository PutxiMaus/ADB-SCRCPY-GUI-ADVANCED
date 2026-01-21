import tkinter as tk
from tkinter import ttk
from .gui.theme import apply_theme, force_dark
from .gui.profiles_tab import create_profiles_tab
from .gui.devices_tab import create_devices_tabs
from .gui.commands_tab import create_commands_tab
from .gui.explorer_tab import create_explorer_tab
from .gui.apps_tab import create_apps_tab
from .gui.batch_tab import create_batch_tab
from .utils import gui_utils as logs

def main():
    root = tk.Tk()
    root.title("ADB+SCRCPY GUI v2.0")
    root.state("zoomed")

    # Crear PanedWindow vertical
    paned = tk.PanedWindow(root, orient=tk.VERTICAL)
    paned.pack(fill=tk.BOTH, expand=True)

    # Parte superior: Notebook principal
    notebook = ttk.Notebook(paned)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Pestañas
    create_profiles_tab(notebook)
    create_devices_tabs(notebook)
    create_commands_tab(notebook)
    create_explorer_tab(notebook)
    create_apps_tab(notebook)
    create_batch_tab(notebook)

    paned.add(notebook, stretch="always")  # Notebook se expande

    # Parte inferior: Consola
    log_frame = tk.Frame(paned)
    logs.text_log = tk.Text(
        log_frame,
        height=10,        # Más grande por defecto
        bg="#1e1f22",
        fg="#b8ffb8",
        wrap=tk.WORD
    )
    logs.text_log.pack(fill=tk.BOTH, expand=True)
    paned.add(log_frame, minsize=20)  # Tamaño mínimo de la consola

    # Aplicar tema
    apply_theme(root)
    force_dark(root)

    root.mainloop()

if __name__ == "__main__":
    main()
