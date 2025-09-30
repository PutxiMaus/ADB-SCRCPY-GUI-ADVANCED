# 📋 Changelog — v2.0

## ✨ Added
- Nueva estructura modular bajo la carpeta `project/`:
  - `project/__init__.py`
  - `project/main.py` (reemplaza al antiguo `main.py` de raíz).
  - **Módulo de configuración**: `project/config/`
    - `config.py`
    - `devices.json`
    - Subcarpeta `tools/` con todos los binarios y utilidades de plataforma (antes estaban en `tools/` en raíz).
  - **Módulo de GUI**: `project/gui/`
    - `apps_tab.py`, `batch_tab.py`, `commands_tab.py`, `devices_tab.py`, `explorer_tab.py`, `profiles_tab.py`, `theme.py`.
  - **Módulo de utilidades**: `project/utils/`
    - `adb_utils.py`, `gui_utils.py`, `net_utils.py`.
    - Subcarpeta `batch/` con scripts `.bat` (ej: `OpenLink.bat`, `Unlock114.bat`).
- Nuevo archivo de arranque: `start.py`.
- Nueva organización de documentación y metadatos bajo `github/`:
  - `.github_workflow_python-ci.yml`, `.gitignore`, `CHANGELOG.md`, `CONTRIBUTING.md`, `INSTALL.md`, `LICENSE`, `README.md`.

## 🔄 Changed
- La estructura del proyecto se reorganizó completamente:
  - Archivos raíz de configuración, herramientas y documentación movidos a subcarpetas (`project/config/`, `project/utils/`, `github/`).
  - `main.py` ahora está dentro de `project/` en lugar de la raíz.
  - Las herramientas de Android
