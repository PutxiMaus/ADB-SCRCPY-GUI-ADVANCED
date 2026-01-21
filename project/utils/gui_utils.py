import tkinter as tk
from ..gui.theme import force_dark

text_log = None  # se inicializa desde main
_dark_applied = False

def gui_log(msg, level="info"):
    global text_log, _dark_applied
    if text_log and isinstance(text_log, tk.Text):
        if not _dark_applied:
            force_dark(text_log)
            _dark_applied = True
        text_log.after(0, lambda: _append_log(msg, level))
    else:
        print(f"[{level}] {msg}")

def _append_log(msg, level="info"):
    global text_log
    if not text_log:
        return

    tag = level
    if tag not in text_log.tag_names():
        colors = {"info": "lime", "error": "red", "cmd": "cyan"}
        text_log.tag_config(tag, foreground=colors.get(tag, "white"))

    text_log.insert(tk.END, msg + "\n", tag)
    text_log.see(tk.END)
