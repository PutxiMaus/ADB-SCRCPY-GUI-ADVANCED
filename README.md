# SCRCPY Python GUI

Interfaz gráfica en Python/Tkinter para gestionar conexiones ADB, lanzar `scrcpy` y ejecutar comandos auxiliares.
Punto de entrada: `main.py`.

**Autor:** PutxiMaus

## Estructura principal
- `main.py` — aplicación principal (Tkinter).
- `adb_commands.py` — helpers ADB usados por la app.
- `bat_sources/` — scripts .bat auxiliares antiguos.
- `tools/` — carpeta con `platform-tools`, `scrcpy`, `ipscan` (portable).

## Requisitos

- Python 3.10+ (probado con 3.13 en Windows).
- Windows: comandos `ping -n` y `arp -a`.
