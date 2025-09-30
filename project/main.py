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
    root.title("ADB+SCRCPY GUI ADVANCED")
    root.state("zoomed")

    # Notebook principal
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Pestañas
    create_profiles_tab(notebook)
    create_devices_tabs(notebook)
    create_commands_tab(notebook)
    create_explorer_tab(notebook)
    create_apps_tab(notebook)
    create_batch_tab(notebook)

    # Consola inferior
    log_frame = tk.Frame(root)
    log_frame.pack(side=tk.BOTTOM, fill=tk.X)
    logs.text_log = tk.Text(log_frame, height=10, bg="#0b0b0b", fg="#b8ffb8")
    logs.text_log.pack(fill=tk.BOTH, expand=True)

    apply_theme(root)
    force_dark(root)
    root.mainloop()

if __name__ == "__main__":
    main()
