import os
import shutil
from pathlib import Path

# Ruta raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Archivo de perfiles
PERFILES_FILE = PROJECT_ROOT / "config" / "devices.json"

# Base para herramientas (por ejemplo aapt.exe, scrcpy, platform-tools)
CONFIG_DIR = PROJECT_ROOT / "config"
TOOLS_DIR = CONFIG_DIR / "tools" / "platform-tools"
ADB_ENV_PATH = os.environ.get("ADB_PATH") or os.environ.get("ADB_EXECUTABLE")
ADB_PATH = Path(ADB_ENV_PATH) if ADB_ENV_PATH else None
ADB_FALLBACK_NAME = "adb.exe" if os.name == "nt" else "adb"
ADB_FOUND = shutil.which("adb") if ADB_PATH is None else None
ADB_PATH = Path(ADB_FOUND) if ADB_PATH is None and ADB_FOUND else ADB_PATH
if ADB_PATH is None:
    ADB_PATH = TOOLS_DIR / ADB_FALLBACK_NAME
