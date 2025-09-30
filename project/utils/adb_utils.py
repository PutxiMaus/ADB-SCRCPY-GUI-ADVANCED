import subprocess
import threading
from ..config.config import TOOLS_DIR, ADB_EXE
from .gui_utils import gui_log

def run_adb(cmd):
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(
            [str(TOOLS_DIR/ADB_EXE)] + cmd,
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error ejecutando adb: {e}"

def exec_adb(args):
    if isinstance(args, str):
        args = args.split()
    cmd = ["adb"] + args
    gui_log(f">> {' '.join(cmd)}", level="cmd")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.stdout:
            gui_log(proc.stdout.strip(), level="info")
        if proc.stderr:
            gui_log(proc.stderr.strip(), level="error")
        return proc.stdout
    except Exception as e:
        gui_log(f"Error ejecutando adb: {e}", level="error")
        return ""

def run_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
