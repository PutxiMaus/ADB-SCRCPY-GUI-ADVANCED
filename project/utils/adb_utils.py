import subprocess
import threading
from ..config.config import ADB_PATH, TOOLS_DIR
from .gui_utils import gui_log

DEFAULT_TIMEOUT = 15

def _run_adb_command(args, timeout=DEFAULT_TIMEOUT, log_command=True):
    if isinstance(args, str):
        args = args.split()
    cmd = [str(ADB_PATH)] + args
    if log_command:
        log_cmd = ["adb"] + args
        gui_log(f">> {' '.join(log_cmd)}", level="cmd")
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(TOOLS_DIR),
        )
    except FileNotFoundError:
        gui_log(f"No se encontró adb en: {ADB_PATH}", level="error")
        return None
    except subprocess.TimeoutExpired:
        gui_log(f"Tiempo de espera agotado ejecutando: {' '.join(cmd)}", level="error")
        return None
    except Exception as e:
        gui_log(f"Error ejecutando adb: {e}", level="error")
        return None

def run_adb(cmd):
    result = _run_adb_command(cmd, log_command=False)
    if result is None:
        return "Error ejecutando adb."
    if result.stderr:
        return result.stderr.strip()
    return result.stdout.strip()

def exec_adb(args):
    proc = _run_adb_command(args)
    if proc is None:
        return ""
    if proc.stdout:
        gui_log(proc.stdout.strip(), level="info")
    if proc.stderr:
        gui_log(proc.stderr.strip(), level="error")
    return proc.stdout

def run_in_thread(fn, *args, **kwargs):
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
