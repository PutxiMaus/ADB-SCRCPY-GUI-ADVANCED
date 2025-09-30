import tkinter as tk
from ..gui.theme import force_dark

text_log = None  # se inicializa desde main

def gui_log(msg, level="info"):
    global text_log
    if text_log and isinstance(text_log, tk.Text):
        text_log.after(0, lambda: _append_log(msg, level))
    else:
        print(f"[{level}] {msg}")

def _append_log(msg, level="info"):
    global text_log
    if not text_log:
        return

    # Aplica tema oscuro si no se ha hecho aún
    force_dark(text_log)

    tag = level
    if tag not in text_log.tag_names():
        colors = {"info": "lime", "error": "red", "cmd": "cyan"}
        text_log.tag_config(tag, foreground=colors.get(tag, "white"))

    text_log.insert(tk.END, msg + "\n", tag)
    text_log.see(tk.END)