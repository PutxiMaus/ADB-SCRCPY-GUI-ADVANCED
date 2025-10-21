# theme.py
from tkinter import ttk, Text, Listbox, Canvas

# Paleta estilo Discord / ChatGPT
COLORS = {
    "bg": "#313338",       # Fondo principal
    "bg_alt": "#2b2d31",   # Paneles
    "bg_entry": "#1e1f22", # Inputs, listas
    "fg": "#e0e0e0",       # Texto normal
    "fg_muted": "#a3a6aa", # Texto secundario
    "accent": "#313338",   # Azul Discord
    "border": "#202225"    # Bordes
}


def apply_theme(root):
    """Aplica un tema oscuro uniforme a toda la app usando ttk.Style"""
    
    style = ttk.Style(root)
    style.theme_use("clam")

    # ----- Base -----
    style.configure(".", background=COLORS["bg"], foreground=COLORS["fg"], fieldbackground=COLORS["bg_entry"])

    # ----- Frames & Labels -----
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"])
    style.configure("Header.TLabel", font=("Segoe UI", 11, "bold"), foreground=COLORS["accent"])

    # ----- Buttons -----
    style.configure("TButton",
                    background=COLORS["bg_alt"],
                    foreground=COLORS["fg"],
                    borderwidth=1)
    style.map("TButton",
              background=[("active", COLORS["accent"]),],
              foreground=[("active", "#ffffff"), ("pressed", "#ffffff")])

    # ----- Entry -----
    style.layout("TEntry", [
        ("Entry.border", {"sticky": "nswe", "children": [
            ("Entry.padding", {"sticky": "nswe", "children": [
                ("Entry.textarea", {"sticky": "nswe"})
            ]})
        ]})
    ])
    style.configure("TEntry",
                    fieldbackground=COLORS["bg_entry"],
                    background=COLORS["bg_entry"],
                    foreground=COLORS["fg"],
                    bordercolor=COLORS["border"],
                    insertcolor=COLORS["fg"])

    # ----- Combobox -----
    style.configure("TCombobox",
                    fieldbackground=COLORS["bg_entry"],
                    background=COLORS["bg_entry"],
                    foreground=COLORS["fg"],
                    arrowcolor=COLORS["fg"])
    style.map("TCombobox",
              fieldbackground=[("readonly", COLORS["bg_entry"])],
              selectbackground=[("readonly", COLORS["accent"])],
              selectforeground=[("readonly", "#ffffff")])

    # ----- Treeview -----
    style.layout("Treeview", [
        ("Treeview.treearea", {"sticky": "nswe"})
    ])
    style.configure("Treeview",
                    background=COLORS["bg_entry"],
                    fieldbackground=COLORS["bg_entry"],
                    foreground=COLORS["fg"],
                    bordercolor=COLORS["border"],
                    rowheight=22)
    style.map("Treeview",
              background=[("selected", COLORS["accent"])],
              foreground=[("selected", "#ffffff")])

    style.configure("Treeview.Heading",
                    background=COLORS["bg_alt"],
                    foreground=COLORS["fg"],
                    bordercolor=COLORS["border"])
    style.map("Treeview.Heading",
              background=[("active", COLORS["accent"])])

    # ----- Notebook (Tabs) -----
    style.configure("TNotebook", background=COLORS["bg"], bordercolor=COLORS["border"])
    style.configure("TNotebook.Tab",
                    background=COLORS["bg_alt"],
                    foreground=COLORS["fg_muted"],
                    padding=(10, 5))
    style.map("TNotebook.Tab",
              background=[("selected", COLORS["bg_entry"])],
              foreground=[("selected", COLORS["fg"])])

    # ----- Scrollbars -----
    style.layout("Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"sticky": "nswe"})
        ]})
    ])
    style.configure("Vertical.TScrollbar",
                    troughcolor=COLORS["bg"],
                    background=COLORS["bg_alt"],
                    bordercolor=COLORS["border"],
                    arrowcolor=COLORS["fg"])
    style.map("Vertical.TScrollbar",
              background=[("active", COLORS["accent"])])

    style.layout("Horizontal.TScrollbar", [
        ("Horizontal.Scrollbar.trough", {"sticky": "we", "children": [
            ("Horizontal.Scrollbar.thumb", {"sticky": "nswe"})
        ]})
    ])
    style.configure("Horizontal.TScrollbar",
                    troughcolor=COLORS["bg"],
                    background=COLORS["bg_alt"],
                    bordercolor=COLORS["border"],
                    arrowcolor=COLORS["fg"])
    style.map("Horizontal.TScrollbar",
              background=[("active", COLORS["accent"])])


def force_dark(widget):
    """Aplica colores oscuros manualmente a widgets tk que no usan ttk.Style"""
    if isinstance(widget, Text):
        widget.configure(bg=COLORS["bg_entry"], fg=COLORS["fg"], insertbackground=COLORS["fg"])
    elif isinstance(widget, Listbox):
        widget.configure(bg=COLORS["bg_entry"], fg=COLORS["fg"], selectbackground=COLORS["accent"], selectforeground="#ffffff")
    elif isinstance(widget, Canvas):
        widget.configure(bg=COLORS["bg"])
    else:
        try:
            widget.configure(bg=COLORS["bg"], fg=COLORS["fg"])
        except Exception:
            pass
