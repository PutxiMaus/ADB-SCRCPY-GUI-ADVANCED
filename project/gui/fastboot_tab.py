# universal_flashing_tab.py
"""
Pestaña universal para flasheo (Fastboot / Heimdall / ROM zips) — diseñada para integrarse
en tu proyecto con gui_log() y run_in_thread() disponibles.

Características:
 - Detecta dispositivo/mode/manufacturer.
 - Detecta disponibilidad de fastboot/adb/heimdall.
 - Ofrece ayuda para drivers (abre enlaces o intenta lanzar Zadig si está disponible).
 - Flasheo por fastboot (partición a partición o flasheo de múltiples imágenes).
 - Flasheo por heimdall (Download Mode), maneja nombres en mayúsculas y evita espacios en rutas.
 - Análisis de archivos zip/tar/tar.md5/img/payload.bin; soporta extracción con herramientas externas si están en PATH.
 - Todo en hilos; GUI no bloqueante; logs con gui_log(...).
NOTA: No instala drivers automáticamente por razones de seguridad. Provee acciones recomendadas.
"""
import os
import re
import sys
import shutil
import subprocess
import tempfile
import zipfile
import tarfile
import platform
from pathlib import Path
from tkinter import (
    ttk, filedialog, messagebox, StringVar, Canvas, Frame, Scrollbar,
    BOTH, X, Y, RIGHT, LEFT, VERTICAL, BooleanVar, Checkbutton, Button, Label
)

# Ajusta estos imports según la estructura de tu proyecto
from ..config.config import TOOLS_DIR
from ..utils.adb_utils import run_in_thread
from ..utils.gui_utils import gui_log
from ..gui.theme import apply_theme, force_dark, COLORS

# Ejecutables (pueden ser rutas absolutas o solo nombres si están en PATH)
FASTBOOT_EXE = str(TOOLS_DIR / "fastboot.exe")
ADB_EXE = str(TOOLS_DIR / "adb.exe")
HEIMDALL_EXE = str(TOOLS_DIR / "heimdall.exe") 

# herramientas auxiliares opcionales
PAYLOAD_DUMPER = "payload_dumper.py"  # si está en PATH (o ruta absoluta), puede extraer payload.bin
ZADIG_EXE_NAMES = str(TOOLS_DIR / "Drivers" / "zadig.exe")  

# Particiones comunes (UI-friendly lower-case)
COMMON_PARTITIONS = [
    "boot", "recovery", "system", "vendor", "userdata", "cache",
    "modem", "radio", "dtbo", "vbmeta", "tz", "persist", "oem", "product", "system_ext"
]

# ----------------------
# Helpers de ejecución
# ----------------------
def is_windows():
    return platform.system().lower().startswith("win")

def is_executable_available(exe):
    """Devuelve True si exe es accesible (ruta absoluta) o está en PATH (shutil.which)."""
    if not exe:
        return False
    if os.path.isabs(exe) and os.path.isfile(exe):
        return True
    return shutil.which(exe) is not None

def run_capture(cmd, timeout=None):
    """
    Ejecuta comando (lista) y devuelve (code, stdout, stderr).
    Uso centralizado para logging y debug.
    """
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired as e:
        return 124, "", f"Timeout: {e}"
    except Exception as e:
        return 1, "", str(e)

def run_fastboot(args):
    return run_capture([FASTBOOT_EXE] + args)

def run_adb(args):
    return run_capture([ADB_EXE] + args)

def run_heimdall(args):
    return run_capture([HEIMDALL_EXE] + args)

# ----------------------
# Detección de dispositivo y marca
# ----------------------
def get_device_state_and_manufacturer():
    """
    Intenta detectar el estado del dispositivo:
     - 'fastboot' si fastboot devices devuelve algo
     - 'download' si adb detecta un samsung y getprop muestra samsung
     - 'android' si adb devices muestra un device
     - None si no se detecta nada
    Retorna (state, manufacturer) (manufacturer puede ser empty string)
    """
    # Fastboot
    if is_executable_available(FASTBOOT_EXE):
        code, out, err = run_fastboot(["devices"])
        if code == 0 and out.strip():
            lines = [l for l in out.splitlines() if l.strip()]
            if lines:
                return "fastboot", ""
    # ADB
    if is_executable_available(ADB_EXE):
        code, out, err = run_adb(["devices"])
        if code == 0 and out.strip():
            lines = [l for l in out.splitlines() if l.strip() and "device" in l and "offline" not in l]
            if lines:
                # manufacturer
                code2, out2, err2 = run_adb(["shell", "getprop", "ro.product.manufacturer"])
                manufacturer = out2.strip().lower() if code2 == 0 else ""
                if "samsung" in manufacturer:
                    return "download", "samsung"
                return "android", manufacturer
    return None, ""

# ----------------------
# Helpers para Heimdall (rutas sin espacios)
# ----------------------
def copy_to_temp_no_spaces(path):
    """
    Copia el archivo a un temporal con nombre sin espacios y devuelve la ruta.
    """
    try:
        base = os.path.basename(path)
        safe = base.replace(" ", "_")
        fd, tmp = tempfile.mkstemp(prefix="heimdall_", suffix="_" + safe)
        os.close(fd)
        shutil.copyfile(path, tmp)
        return tmp
    except Exception as e:
        gui_log(f"Error preparando temporal: {e}", level="error")
        return None

# ----------------------
# Análisis de paquetes ROM
# ----------------------
def analyze_package(path, extract_dir=None):
    """
    Analiza un archivo .zip, .tar, .tar.md5 o .img.
    Si extract_dir es proporcionado, extrae dentro de él.
    Devuelve un dict con keys: 'type' ('zip','tar','img','payload'), 'files' (list of found images),
    y 'payload' boolean if payload.bin found.
    """
    path = os.path.abspath(path)
    name = os.path.basename(path).lower()
    result = {"type": None, "files": [], "payload": False, "extracted_dir": None}
    try:
        if zipfile.is_zipfile(path):
            result["type"] = "zip"
            z = zipfile.ZipFile(path, "r")
            names = z.namelist()
            # common image names
            images = []
            for candidate in ("boot.img", "recovery.img", "system.img", "vendor.img", "vbmeta.img", "payload.bin", "boot_recovery.img"):
                for n in names:
                    if n.lower().endswith(candidate):
                        images.append(n)
                        if candidate == "payload.bin":
                            result["payload"] = True
            result["files"] = images
            if extract_dir and images:
                z.extractall(extract_dir)
                result["extracted_dir"] = extract_dir
            z.close()
        elif tarfile.is_tarfile(path):
            result["type"] = "tar"
            t = tarfile.open(path, "r:*")
            names = t.getnames()
            images = []
            for candidate in ("boot.img", "recovery.img", "system.img", "vendor.img", "vbmeta.img", "payload.bin"):
                for n in names:
                    if n.lower().endswith(candidate):
                        images.append(n)
                        if candidate == "payload.bin":
                            result["payload"] = True
            result["files"] = images
            if extract_dir and images:
                t.extractall(extract_dir)
                result["extracted_dir"] = extract_dir
            t.close()
        else:
            # single img file?
            lower = name
            if lower.endswith(".img") or lower.endswith(".bin"):
                result["type"] = "img"
                result["files"] = [path]
            elif lower.endswith("payload.bin"):
                result["type"] = "payload"
                result["files"] = [path]
                result["payload"] = True
            else:
                result["type"] = "unknown"
                result["files"] = []
    except Exception as e:
        gui_log(f"Error analizando paquete {path}: {e}", level="error")
        result["type"] = "error"
    return result

# ----------------------
# Payload handling (A/B OTAs)
# ----------------------
def extract_payload_bin(payload_path, outdir):
    """
    Intenta extraer payload.bin usando payload_dumper.py si está disponible en PATH.
    Devuelve (success, message, list_of_images_dir)
    """
    if not os.path.isfile(payload_path):
        return False, "payload.bin no existe", []
    dumper_cmd = shutil.which("payload-dumper-go") or shutil.which("payload_dumper") or shutil.which("payload_dumper.py") or shutil.which(PAYLOAD_DUMPER)
    if not dumper_cmd:
        return False, "No se encontró una herramienta para extraer payload.bin (payload_dumper). Instálala y vuelve a intentarlo.", []
    # Ejecutar la herramienta: muchos dumpers aceptan payload.bin -o outdir
    cmd = [dumper_cmd, payload_path, "-o", outdir] if "payload-dumper-go" in dumper_cmd else [dumper_cmd, payload_path, outdir]
    code, out, err = run_capture(cmd, timeout=600)
    if code == 0:
        # Buscar imágenes extraídas
        imgs = []
        for root, _, files in os.walk(outdir):
            for f in files:
                if f.lower().endswith(".img"):
                    imgs.append(os.path.join(root, f))
        return True, out or "Extraído correctamente", imgs
    else:
        return False, f"Error extrayendo payload: {err or out}", []

# ----------------------
# Flasheo universal (fastboot / heimdall)
# ----------------------
def flash_via_fastboot(partition, img_path):
    """
    Flash simple: fastboot flash <partition> <img_path>
    """
    if not is_executable_available(FASTBOOT_EXE):
        return 1, "", "fastboot no disponible"
    cmd = [FASTBOOT_EXE, "flash", partition, img_path]
    return run_capture(cmd)

def erase_via_fastboot(partition):
    if not is_executable_available(FASTBOOT_EXE):
        return 1, "", "fastboot no disponible"
    return run_capture([FASTBOOT_EXE, "erase", partition])

def flash_via_heimdall(partition, img_path):
    """
    Usa --<PARTITION> <file>, y en Windows evita espacios copiando a temporal.
    Convierte el partition a mayúsculas (Heimdall lo suele esperar).
    """
    if not is_executable_available(HEIMDALL_EXE):
        return 1, "", "heimdall no disponible"
    # preparar archivo temporal si ruta contiene espacios (Windows issue)
    safe_path = img_path
    if is_windows() and " " in img_path:
        tmp = copy_to_temp_no_spaces(img_path)
        if not tmp:
            return 1, "", "No se pudo preparar archivo temporal para Heimdall"
        safe_path = tmp
    part_arg = f"--{partition.upper()}"
    code, out, err = run_heimdall([ "flash", part_arg, safe_path ])
    # si usamos tmp, intentar borrarlo
    if is_windows() and safe_path != img_path:
        try:
            os.remove(safe_path)
        except Exception:
            pass
    return code, out, err

# ----------------------
# Drivers / ayuda
# ----------------------
MANUFACTURER_DRIVER_LINKS = {
    "samsung": "https://developer.samsung.com/mobile/android-usb-driver.html",
    "google": "https://developer.android.com/studio/run/win-usb",
    "oneplus": "https://www.oneplus.com/support",
    "xiaomi": "https://www.mi.com/global/service/faq/",
    "motorola": "https://support.motorola.com",
    "sony": "https://developer.sony.com",
    # añade otros según necesites
}

def open_driver_page(manufacturer):
    """
    Abre la página del fabricante para drivers; si no se reconoce, abre search genérico.
    """
    import webbrowser
    m = (manufacturer or "").lower()
    url = MANUFACTURER_DRIVER_LINKS.get(m)
    if not url:
        # búsqueda genérica
        url = f"https://www.google.com/search?q=android+usb+drivers+{m or ''}"
    webbrowser.open(url)

def try_launch_zadig(tools_dir=None):
    """
    Si Zadig está presente en tools dir, lo lanza para que el usuario pueda seleccionar WinUSB.
    """
    possible = []
    if tools_dir:
        for n in ZADIG_EXE_NAMES:
            p = Path(tools_dir) / n
            if p.exists():
                possible.append(str(p))
    # también buscar en PATH
    for n in ZADIG_EXE_NAMES:
        p = shutil.which(n)
        if p:
            possible.append(p)
    if not possible:
        gui_log("Zadig no encontrado en tools ni en PATH.", level="info")
        return False
    # lanzar primera coincidencia
    try:
        subprocess.Popen([possible[0]])
        gui_log(f"Lanzado Zadig: {possible[0]}", level="info")
        return True
    except Exception as e:
        gui_log(f"No se pudo lanzar Zadig: {e}", level="error")
        return False

# ----------------------
# GUI: pestaña universal
# ----------------------
def create_universal_flashing_tab(notebook):
    """
    Crea la pestaña y devuelve el widget.
    Integra:
     - Detector de dispositivo
     - Selector de paquete (.zip/.tar/.img)
     - Botones: Analizar, Flash All (auto), Flash by partition, Erase (fastboot), Backup (fastboot)
     - Ayuda para drivers (abrir links / lanzar Zadig)
    """
    tab = ttk.Frame(notebook)
    notebook.add(tab, text="Universal Flash")

    apply_theme(tab)
    force_dark(tab)
    tab.grid_rowconfigure(0, weight=1)
    tab.grid_columnconfigure(1, weight=1)

    left = ttk.Frame(tab, padding=8)
    left.grid(row=0, column=0, sticky="nsew")
    center = ttk.Frame(tab, padding=8)
    center.grid(row=0, column=1, sticky="nsew")
    right = ttk.Frame(tab, padding=8)
    right.grid(row=0, column=2, sticky="nsew")

    force_dark(left); force_dark(center); force_dark(right)

    # LEFT: herramientas y driver help
    ttk.Label(left, text="Herramientas / Estado").pack(anchor="w", pady=(0,6))
    device_state_var = StringVar(value="No detectado")
    ttk.Label(left, textvariable=device_state_var).pack(anchor="w", pady=(0,6))

    def action_detect():
        def _job():
            state, manuf = get_device_state_and_manufacturer()
            device_state_var.set(f"{state or 'Ninguno'}  ({manuf or 'unknown'})")
            gui_log(f"Estado detectado: {state} - fabricante: {manuf}", level="info")
            # habilitar botones según estado
            # (center sección manejará el contenido)
        run_in_thread(_job)
    ttk.Button(left, text="Detectar dispositivo", command=action_detect).pack(fill="x", pady=4)

    ttk.Button(left, text="Abrir página drivers", command=lambda: open_driver_page(device_state_var.get().split("(")[-1].rstrip(")"))).pack(fill="x", pady=4)
    ttk.Button(left, text="Lanzar Zadig (si existe)", command=lambda: try_launch_zadig(str(TOOLS_DIR))).pack(fill="x", pady=4)

    # center: package selector + analyze + actions
    ttk.Label(center, text="Paquete / Imágenes").pack(anchor="w")
    package_path_var = StringVar(value="")
    package_label = ttk.Label(center, textvariable=package_path_var, wraplength=400)
    package_label.pack(anchor="w", pady=(2,6))

    def choose_package():
        f = filedialog.askopenfilename(title="Selecciona ROM / imagen", filetypes=[("ZIP/TAR/IMG","*.zip *.tar *.img *.tar.md5 *.bin"),("All files","*.*")])
        if f:
            package_path_var.set(f)
            gui_log(f"Seleccionado paquete: {f}", level="info")
    ttk.Button(center, text="Seleccionar paquete (.zip/.tar/.img)", command=choose_package).pack(fill="x", pady=4)

    analyze_result_var = StringVar(value="")
    ttk.Label(center, textvariable=analyze_result_var, wraplength=400).pack(anchor="w", pady=(6,4))

    temp_extract_dir = None
    analyzed = {}  # guardará el resultado de analyze

    def analyze_package_action():
        nonlocal temp_extract_dir, analyzed
        pkg = package_path_var.get()
        if not pkg:
            messagebox.showinfo("Selecciona paquete", "Selecciona un paquete antes de analizar.")
            return
        # extraer a un temporal si es zip/tar
        temp_extract_dir = tempfile.mkdtemp(prefix="rom_extract_")
        res = analyze_package(pkg, extract_dir=temp_extract_dir)
        analyzed = res
        if res["type"] in ("zip","tar") and res["files"]:
            analyze_result_var.set(f"Encontrado: {', '.join(res['files'])}")
            gui_log(f"Análisis OK: {res['files']}", level="info")
        elif res["type"] == "img":
            analyze_result_var.set("Archivo de imagen único detectado.")
            analyzed["files"] = [pkg]
        elif res["payload"]:
            analyze_result_var.set("Encontrado payload.bin; requiere extractor (payload_dumper).")
        else:
            analyze_result_var.set("No se detectaron imágenes reconocibles en el paquete.")
            gui_log(f"Análisis: no se encontraron imágenes en {pkg}", level="info")
    ttk.Button(center, text="Analizar paquete", command=lambda: run_in_thread(analyze_package_action)).pack(fill="x", pady=4)

    # action buttons area
    actions_frame = ttk.Frame(center)
    actions_frame.pack(fill=X, pady=(8,0))

    reboot_after_var = BooleanVar(value=False)
    Checkbutton(actions_frame, text="Reboot after flash", variable=reboot_after_var, bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=LEFT, padx=(0,8))

    def flash_all_auto():
        """
        Intento de flasheo 'todo' con heurísticas:
         - Si payload.bin -> intentar extraer (si hay extractor)
         - Si zip/tar con boot.img/system.img -> flashear por fastboot o heimdall según modo
         - Si single .img -> preguntar partición objetivo (o usar 'boot' por defecto)
        """
        pkg = package_path_var.get()
        if not pkg:
            messagebox.showinfo("Selecciona paquete", "Selecciona un paquete antes de flashear.")
            return

        def _job():
            state, manuf = get_device_state_and_manufacturer()
            gui_log(f"Flasheando en modo {state} (manufacturer={manuf})", level="info")
            if analyzed.get("payload"):
                # intentar extraer payload
                outdir = tempfile.mkdtemp(prefix="payload_extract_")
                ok, msg, imgs = extract_payload_bin(os.path.join(temp_extract_dir, "payload.bin") if temp_extract_dir else pkg, outdir)
                if not ok:
                    gui_log(f"No se pudo extraer payload.bin: {msg}", level="error")
                    messagebox.showerror("Payload extraction", msg)
                    return
                # si hay imgs, flashear por fastboot por defecto
                for img in imgs:
                    # heurística: si filename contains boot -> flash boot
                    name = os.path.basename(img).lower()
                    part = "boot" if "boot" in name else ("system" if "system" in name else None)
                    if not part:
                        gui_log(f"No se infiere partición para {img}, se salta.", level="warning")
                        continue
                    if state == "fastboot":
                        code, out, err = flash_via_fastboot(part, img)
                    elif state == "download":
                        code, out, err = flash_via_heimdall(part, img)
                    else:
                        gui_log("Dispositivo no en modo de flasheo.", level="error")
                        return
                    if out: gui_log(out, level="info")
                    if err: gui_log(err, level="error")
            else:
                # normalmente tenemos extracted files in temp_extract_dir or single img
                files = analyzed.get("files", [])
                if not files:
                    # si es img único (package_path is img)
                    if analyzed.get("type") == "img":
                        files = [pkg]
                    else:
                        gui_log("No se encontraron archivos para flashear.", level="error")
                        return
                # flashear cada archivo con heurística
                for fpath in files:
                    name = os.path.basename(fpath).lower()
                    if "boot" in name:
                        part = "boot"
                    elif "recovery" in name:
                        part = "recovery"
                    elif "system" in name:
                        part = "system"
                    elif "vendor" in name:
                        part = "vendor"
                    elif "vbmeta" in name:
                        part = "vbmeta"
                    else:
                        # si es single img y no sabemos -> preguntar al usuario
                        if len(files) == 1:
                            # preguntar partición destino
                            part = ask_partition_from_user(fpath)
                            if not part:
                                gui_log("Usuario canceló selección de partición.", level="info")
                                return
                        else:
                            gui_log(f"No se infiere partición para {fpath}, se salta.", level="warning")
                            continue
                    # ejecutar según estado
                    if state == "fastboot":
                        code, out, err = flash_via_fastboot(part, fpath)
                    elif state == "download":
                        code, out, err = flash_via_heimdall(part, fpath)
                    else:
                        gui_log("Dispositivo no en modo de flasheo.", level="error")
                        return
                    if out: gui_log(out, level="info")
                    if err: gui_log(err, level="error")
                    if code == 0:
                        gui_log(f"Flasheo {part} OK", level="info")
                    else:
                        gui_log(f"Flasheo {part} falló (code {code})", level="error")
            # reboot si corresponde
            if reboot_after_var.get():
                if state == "fastboot":
                    run_fastboot(["reboot"])
                elif state == "download":
                    run_heimdall(["reboot"])
                gui_log("Comando reboot ejecutado", level="info")

        run_in_thread(_job)

    ttk.Button(actions_frame, text="Flash All (auto)", command=flash_all_auto).pack(side=LEFT, padx=4)

    def ask_partition_from_user(fpath):
        """
        Muestra un dialogo simple para preguntar la partición objetivo si no se puede inferir.
        Devuelve la partición (string) o None.
        """
        # dialog simple: pedir texto
        import tkinter.simpledialog as sd
        ans = sd.askstring("Partición objetivo", f"No se pudo inferir la partición para {os.path.basename(fpath)}.\nIntroduce la partición (ej: boot, recovery, system):")
        if ans:
            return ans.strip()
        return None

    # Flash por partición (UI manual)
    ttk.Label(center, text="Flasheo manual por partición (selecciona una imagen o paquete y luego la partición):").pack(anchor="w", pady=(8,4))
    manual_partition_var = StringVar(value="")
    manual_file_var = StringVar(value="")

    def choose_manual_file():
        f = filedialog.askopenfilename(title="Selecciona imagen", filetypes=[("IMG files","*.img *.img.gz *.bin *.img.xz *.img.*"),("All","*.*")])
        if f:
            manual_file_var.set(f)
            gui_log(f"Seleccionado (manual): {f}", level="info")
    ttk.Button(center, text="Seleccionar imagen (manual)", command=choose_manual_file).pack(fill=X, pady=4)
    ttk.Label(center, textvariable=manual_file_var, wraplength=400).pack(anchor="w", pady=(2,4))

    part_entry = ttk.Entry(center, textvariable=manual_partition_var)
    part_entry.pack(fill=X, pady=(2,4))
    part_entry.insert(0, "boot")

    def manual_flash_action():
        fpath = manual_file_var.get()
        part = manual_partition_var.get().strip()
        if not fpath or not part:
            messagebox.showinfo("Falta datos", "Selecciona una imagen y escribe la partición.")
            return
        def _job():
            state, manuf = get_device_state_and_manufacturer()
            gui_log(f"Flasheando (manual) {part} <= {fpath} en modo {state}", level="info")
            if state == "fastboot":
                code, out, err = flash_via_fastboot(part, fpath)
            elif state == "download":
                code, out, err = flash_via_heimdall(part, fpath)
            else:
                gui_log("Dispositivo no en modo fastboot/download", level="error")
                return
            if out: gui_log(out, level="info")
            if err: gui_log(err, level="error")
            if code == 0 and reboot_after_var.get():
                if state == "fastboot":
                    run_fastboot(["reboot"])
                else:
                    run_heimdall(["reboot"])
        run_in_thread(_job)

    ttk.Button(center, text="Flash manual partición", command=manual_flash_action).pack(fill=X, pady=4)

    # Erase (fastboot only)
    ttk.Label(center, text="Erase (fastboot sólo)").pack(anchor="w", pady=(8,4))
    erase_part_var = StringVar(value="userdata")
    ttk.Entry(center, textvariable=erase_part_var).pack(fill=X, pady=(2,4))
    def erase_action():
        if not messagebox.askyesno("Confirmar", f"Erase {erase_part_var.get()}? Esto puede dejar el dispositivo inservible."):
            return
        def _job():
            state, _ = get_device_state_and_manufacturer()
            if state != "fastboot":
                gui_log("Erase requiere dispositivo en Fastboot.", level="error")
                return
            code, out, err = erase_via_fastboot(erase_part_var.get())
            if out: gui_log(out, level="info")
            if err: gui_log(err, level="error")
        run_in_thread(_job)
    ttk.Button(center, text="Erase partición (fastboot)", command=erase_action).pack(fill=X, pady=4)

    # Backup (fastboot)
    ttk.Label(center, text="Backup (fastboot simple - si el fastboot soporta 'dump')").pack(anchor="w", pady=(8,4))
    backup_part_var = StringVar(value="boot")
    ttk.Entry(center, textvariable=backup_part_var).pack(fill=X, pady=(2,4))
    def backup_action():
        save = filedialog.asksaveasfilename(title="Guardar backup como", defaultextension=".img", filetypes=[("IMG",".img")])
        if not save:
            return
        def _job():
            state, _ = get_device_state_and_manufacturer()
            if state != "fastboot":
                gui_log("Backup requiere dispositivo en Fastboot.", level="error")
                return
            code, out, err = run_fastboot(["dump", backup_part_var.get(), save])
            if out: gui_log(out, level="info")
            if err: gui_log(err, level="error")
            if code == 0:
                gui_log(f"Backup guardado en {save}", level="info")
            else:
                gui_log("Backup falló o 'dump' no soportado por fastboot.", level="error")
        run_in_thread(_job)
    ttk.Button(center, text="Backup partición (fastboot)", command=backup_action).pack(fill=X, pady=4)

    # RIGHT: ayuda / info rápida
    ttk.Label(right, text="Ayuda rápida").pack(anchor="w")
    ttk.Label(right, text="Notas:", wraplength=240).pack(anchor="w", pady=(4,4))
    ttk.Label(right, text="- Ejecuta la app como Administrador en Windows para Heimdall (libusb errors).", wraplength=240).pack(anchor="w", pady=(2,2))
    ttk.Label(right, text="- Para Samsung usa Download Mode (Heimdall) o Odin en Windows.", wraplength=240).pack(anchor="w", pady=(2,2))
    ttk.Label(right, text="- Si el paquete contiene payload.bin, instala payload_dumper y usa 'Analizar' antes.", wraplength=240).pack(anchor="w", pady=(2,2))

    return tab
