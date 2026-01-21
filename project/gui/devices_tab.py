from tkinter import ttk

from .connected_tab import create_connected_tab, refresh_connected_list
from .network_tab import create_network_tab, on_tab_change, refresh_available_list_incremental

# =========================
# Construcción de pestañas
# =========================

def create_devices_tabs(notebook):
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Dark.TFrame")
    style.configure("Treeview")
    style.configure("Treeview.Heading")
    style.configure("TButton")
    style.configure("Vertical.TScrollbar")

    create_network_tab(notebook)
    create_connected_tab(notebook, refresh_available_callback=refresh_available_list_incremental)

    # inicializar listas básicas (rápidas)
    refresh_connected_list()
    refresh_available_list_incremental()

    # ligar evento de cambio de pestaña
    notebook.bind("<<NotebookTabChanged>>", on_tab_change)
