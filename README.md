# SCRCPY Python GUI

Interfaz gráfica en Python/Tkinter para gestionar conexiones ADB, lanzar `scrcpy` y ejecutar comandos auxiliares.
Punto de entrada: `start.py`.

**Autor:** PutxiMaus

## Estructura principal
- `start.py` — launcher.
- `project/` — todo el proyecto.


## Requisitos

- Python 3.10+ (probado con 3.13 en Windows).
- Windows
- Android SDK Platform-Tools (`adb`) y `scrcpy` (en el PATH o dentro de `config/tools/platform-tools`).
- Drivers USB instalados para el dispositivo Android.

## Configuración rápida

1. Descarga el zip del proyecto.
2. Instala Python 3.10 o superior.
3. Instala `adb` y `scrcpy`:
   - O bien agrega `adb` al PATH del sistema.
   - O bien coloca los binarios en `config/tools/platform-tools`.
4. Activa **Depuración USB** en el dispositivo Android (Opciones de desarrollador).
5. Ejecuta:

```
python start.py
```

## Variables de entorno

Puedes forzar una ruta personalizada a `adb`:

- `ADB_PATH` o `ADB_EXECUTABLE` → ruta absoluta al binario `adb`.

## Instalation

Guia de instalacion [INSTALL.md](./INSTALL.md).
