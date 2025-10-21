import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TOOLS_DIR = CONFIG_DIR / "tools" / "platform-tools"
ADB_EXE = "adb.exe" if os.name == "nt" else "adb"

# Archivos de perfiles
DEVICES = PROJECT_ROOT / "config" / "devices.json"
