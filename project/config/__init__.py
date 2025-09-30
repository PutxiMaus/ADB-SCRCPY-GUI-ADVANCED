import os
from pathlib import Path

# Ruta raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Archivo de perfiles
PERFILES_FILE = PROJECT_ROOT / "config" / "devices.json"

# Base para herramientas (por ejemplo aapt.exe, scrcpy, platform-tools)
TOOLS_DIR = PROJECT_ROOT / "tools"
