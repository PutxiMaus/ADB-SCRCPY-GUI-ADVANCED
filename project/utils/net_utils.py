import os, re, socket, subprocess, threading, time
from ..config.config import PROJECT_ROOT
from ..utils.gui_utils import gui_log

def _get_local_ipv4_and_prefix():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip, 24
    except Exception:
        return None, 24

def _run_angryip_scan(range_start, range_end, export_file):
    executables = ["ipscan", "ipscan.exe", "angryip", "angryip.exe"]
    for exe in executables:
        try:
            cmd = [exe, "-f:range", range_start, range_end, "-o", export_file]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
            if proc.returncode == 0 or os.path.exists(export_file):
                return True
        except Exception:
            continue
    return False

def _ping_sweep_cold(range_base):
    threads = []
    def p(ip):
        try:
            subprocess.run(["ping", "-n", "1", "-w", "200", ip],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           encoding="utf-8", errors="replace")
        except Exception:
            pass

    for i in range(1, 255):
        ip = f"{range_base}.{i}"
        t = threading.Thread(target=p, args=(ip,), daemon=True)
        t.start()
        threads.append(t)
        if len(threads) % 50 == 0:
            time.sleep(0.05)
    for t in threads:
        t.join(timeout=0.2)

def find_ip_from_mac(mac):
    if not mac:
        return None

    mac_norm = mac.lower().replace(":", "-").replace(".", "-").replace(" ", "-")
    local_ip, _ = _get_local_ipv4_and_prefix()
    if local_ip:
        parts = local_ip.split(".")
        if len(parts) >= 3:
            base = ".".join(parts[0:3])
            range_start = f"{base}.1"
            range_end = f"{base}.254"
            export_tmp = os.path.join(PROJECT_ROOT, "angry_scan_result.txt")
            try:
                ok = _run_angryip_scan(range_start, range_end, export_tmp)
                if ok and os.path.exists(export_tmp):
                    with open(export_tmp, "r", encoding="utf-8", errors="ignore") as f:
                        data = f.read().lower()
                        if mac_norm in data:
                            for line in data.splitlines():
                                if mac_norm in line:
                                    parts = line.split()
                                    if parts:
                                        return parts[0]
            except Exception:
                pass
            _ping_sweep_cold(base)

    try:
        out = subprocess.getoutput("arp -a")
    except Exception as e:
        gui_log(f"No se pudo ejecutar arp -a: {e}", level="error")
        return None

    for line in out.splitlines():
        low = line.lower()
        if mac_norm in low or mac.lower().replace("-", ":") in low:
            parts = line.split()
            if parts and re.match(r"^\d{1,3}(\.\d{1,3}){3}$", parts[0]):
                return parts[0]
    return None
