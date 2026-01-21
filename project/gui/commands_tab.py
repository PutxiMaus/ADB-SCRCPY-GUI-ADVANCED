import os, subprocess, random, tkinter as tk
from tkinter import ttk, filedialog, simpledialog
from ..config.config import PROJECT_ROOT
from ..config.config import TOOLS_DIR, ADB_PATH
from ..utils.adb_utils import exec_adb, run_in_thread
from ..utils.gui_utils import gui_log

# procesos globales
_scrcpy_proc = None
_screenrec_proc = None

# =========================
# Funciones de comandos
# =========================
def start_scrcpy():
    global _scrcpy_proc
    if _scrcpy_proc and getattr(_scrcpy_proc, 'poll', lambda: None)() is None:
        gui_log("scrcpy ya está en ejecución", level="error")
        return
    try:
        _scrcpy_proc = subprocess.Popen(
            ["scrcpy"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(TOOLS_DIR),
        )
        gui_log("scrcpy iniciado", level="info")
    except Exception as e:
        gui_log(f"No se pudo iniciar scrcpy: {e}", level="error")

def stop_scrcpy():
    global _scrcpy_proc
    if not _scrcpy_proc:
        gui_log("scrcpy no está en ejecución", level="error")
        return
    try:
        _scrcpy_proc.terminate()
        _scrcpy_proc.wait(timeout=5)
    except Exception:
        try:
            _scrcpy_proc.kill()
        except Exception:
            pass
    _scrcpy_proc = None
    gui_log("scrcpy detenido", level="info")

def install_apk():
    apk = filedialog.askopenfilename(title="Selecciona APK", filetypes=[("APK files", "*.apk")])
    if not apk:
        return
    run_in_thread(lambda: exec_adb(["install", "-r", apk]))

def uninstall_app():
    pkg = simpledialog.askstring("Uninstall", "Nombre del paquete (p.ej. com.example.app):")
    if not pkg:
        return
    run_in_thread(lambda: exec_adb(["uninstall", pkg]))

def reboot_device():
    run_in_thread(lambda: exec_adb(["reboot"]))

def adb_disconnect_all():
    run_in_thread(lambda: exec_adb(["disconnect"]))

def dump_logcat():
    run_in_thread(lambda: exec_adb(["logcat", "-d"]))

def get_device_info():
    run_in_thread(lambda: exec_adb(["shell", "getprop"]))

def start_screenrecord():
    global _screenrec_proc
    if _screenrec_proc and getattr(_screenrec_proc, 'poll', lambda: None)() is None:
        gui_log("screenrecord ya en ejecución", level="error")
        return
    try:
        _screenrec_proc = subprocess.Popen(
            [str(ADB_PATH), "shell", "screenrecord", "/sdcard/record.mp4"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(TOOLS_DIR),
        )
        gui_log("screenrecord iniciado en /sdcard/record.mp4", level="info")
    except Exception as e:
        gui_log(f"No se pudo iniciar screenrecord: {e}", level="error")

def stop_screenrecord_and_pull():
    global _screenrec_proc
    if not _screenrec_proc:
        gui_log("No hay screenrecord en ejecución", level="error")
        return
    try:
        _screenrec_proc.terminate()
        _screenrec_proc.wait(timeout=5)
    except Exception:
        try:
            _screenrec_proc.kill()
        except Exception:
            pass
    _screenrec_proc = None
    local = filedialog.asksaveasfilename(defaultextension=".mp4",
                                         filetypes=[("MP4 files", "*.mp4")],
                                         title="Guardar grabación como")
    if not local:
        gui_log("Cancelado pull de grabación", level="error")
        return
    run_in_thread(lambda: exec_adb(["pull", "/sdcard/record.mp4", local]))

def set_wallpaper_via_agent():
    img = filedialog.askopenfilename(title="Selecciona imagen", filetypes=[("Imágenes", "*.jpg;*.png")])
    if not img:
        return

    remote = "/data/local/tmp/fondo.jpg"
    installed = exec_adb(["shell", "pm", "list", "packages", "com.example.wallpaperchanger"])
    if "com.example.wallpaperchanger" not in installed:
        exec_adb(["install", os.path.join(TOOLS_DIR, "WallpaperAgent.apk")])
    exec_adb(["push", img, remote])
    exec_adb(["shell", "am", "broadcast", "-n", "com.example.wallpaperchanger/.WallpaperReceiver", "--es", "path", remote])
    exec_adb(["shell", "rm", remote])
    gui_log("Fondo aplicado mediante WallpaperAgent.", level="success")


# =========================
# Construcción de pestaña
# =========================
def create_commands_tab(notebook):
    tab_comandos = ttk.Frame(notebook)
    notebook.add(tab_comandos, text="Comandos")

    cmds_outer = ttk.Frame(tab_comandos, padding=12)
    cmds_outer.grid(row=0, column=0, sticky="nsew")

    tab_comandos.rowconfigure(0, weight=1)
    tab_comandos.columnconfigure(0, weight=1)
    cmds_outer.rowconfigure(0, weight=1)
    cmds_outer.columnconfigure(0, weight=1)

    sections = ttk.Notebook(cmds_outer)
    sections.grid(row=0, column=0, sticky="nsew")

    def build_section(parent, commands, cols=3):
        grid = ttk.Frame(parent, padding=12)
        grid.pack(fill="both", expand=True)
        for i, (label, cb) in enumerate(commands):
            r = i // cols
            c = i % cols
            btn = ttk.Button(grid, text=label, command=cb)
            btn.grid(row=r, column=c, padx=16, pady=8, ipadx=10, ipady=8, sticky="nsew")

        for c in range(cols):
            grid.columnconfigure(c, weight=1)

        total_rows = (len(commands) + cols - 1) // cols
        for r in range(total_rows):
            grid.rowconfigure(r, weight=1, minsize=50)

    apps_tab = ttk.Frame(sections)
    control_tab = ttk.Frame(sections)
    other_tab = ttk.Frame(sections)
    sections.add(apps_tab, text="Apps")
    sections.add(control_tab, text="Control")
    sections.add(other_tab, text="Otros")

    apps_commands = [
        ("Play Store", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.android.vending", "-c", "android.intent.category.LAUNCHER", "1"]))),
        ("YouTube", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.google.android.youtube", "-c", "android.intent.category.LAUNCHER", "1"]))),
        ("Chrome", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.android.chrome", "-c", "android.intent.category.LAUNCHER", "1"]))),
        ("Gmail", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.google.android.gm", "-c", "android.intent.category.LAUNCHER", "1"]))),
        ("Maps", lambda: run_in_thread(lambda: exec_adb(["shell", "monkey", "-p", "com.google.android.apps.maps", "-c", "android.intent.category.LAUNCHER", "1"]))),
        ("Ajustes", lambda: run_in_thread(lambda: exec_adb(["shell", "am", "start", "-a", "android.settings.SETTINGS"]))),
    ]

    control_commands = [
        ("Home", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "3"]))),
        ("Back", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "4"]))),
        ("Recientes", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "187"]))),
        ("Power", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "26"]))),
        ("Vol +", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "24"]))),
        ("Vol -", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "25"]))),
        ("Mute", lambda: run_in_thread(lambda: exec_adb(["shell", "input", "keyevent", "164"]))),
        ("Screenshot", lambda: run_in_thread(lambda: exec_adb(["shell", "screencap", "-p", "/sdcard/screen.png"]) or exec_adb(["pull", "/sdcard/screen.png", os.path.join(PROJECT_ROOT, "screenshot.png")]))),
        ("Crazy taps", lambda: run_in_thread(lambda: [exec_adb(["shell", "input", "tap", str(random.randint(0, 1080)), str(random.randint(0, 1920))]) for _ in range(10)])),
    ]

    other_commands = [
        ("Disconnect all", adb_disconnect_all),
        ("Reboot", reboot_device),
        ("Install APK", install_apk),
        ("Uninstall app", uninstall_app),
        ("Start scrcpy", start_scrcpy),
        ("Stop scrcpy", stop_scrcpy),
        ("Start screenrecord", start_screenrecord),
        ("Stop screenrecord & pull", stop_screenrecord_and_pull),
        ("Elegir fondo", set_wallpaper_via_agent),
        ("Get device info", get_device_info),
        ("Dump logcat", dump_logcat),
    ]

    build_section(apps_tab, apps_commands)
    build_section(control_tab, control_commands)
    build_section(other_tab, other_commands)

    return tab_comandos
