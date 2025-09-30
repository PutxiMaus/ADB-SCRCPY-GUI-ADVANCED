# Este archivo marca el directorio gui/ como un paquete.
# Opcional: puedes importar aquí todas las funciones de creación de pestañas
# para simplificar los imports en main.py.

from .profiles_tab import create_profiles_tab
from .apps_tab import create_apps_tab
from .explorer_tab import create_explorer_tab
from .batch_tab import create_batch_tab
from .devices_tab import create_devices_tabs
from .commands_tab import create_commands_tab
from .theme import apply_theme

__all__ = [
    "create_profiles_tab",
    "create_apps_tab",
    "create_explorer_tab",
    "create_batch_tab",
    "create_devices_tabs",
    "create_commands_tab",
    "apply_theme"
]
