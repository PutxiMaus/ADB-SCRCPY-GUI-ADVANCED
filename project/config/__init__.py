import os
from pathlib import Path

# Ruta raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Archivo de perfiles
PERFILES_FILE = PROJECT_ROOT / "config" / "devices.json"

# Base para herramientas (por ejemplo aapt.exe, scrcpy, platform-tools)
CONFIG_DIR = PROJECT_ROOT / "config"
TOOLS_DIR = CONFIG_DIR / "tools" / "platform-tools"
ADB_EXE = "adb.exe" if os.name == "nt" else "adb"
