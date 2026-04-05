# app/log_android/adb_device.py
from __future__ import annotations

import os
import shutil
import subprocess
from typing import List, Dict, Optional, Any

# ---------------------------------------------------------------------------
# adb helpers
# ---------------------------------------------------------------------------
def adb_path() -> Optional[str]:
    explicit = os.environ.get("ADB")
    if explicit and shutil.which(explicit):
        return explicit
    return shutil.which("adb")

def adb_exists() -> bool:
    return bool(adb_path())

def _run_cmd(cmd: List[str], timeout: float = 2.0) -> str:
    out = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=True
    )
    return out.stdout or ""

def _adb_shell(serial: Optional[str], args: List[str], timeout: float = 1.5) -> str:
    path = adb_path()
    if not path:
        return ""
    cmd = [path]
    if serial:
        cmd += ["-s", serial]
    cmd += ["shell"] + args
    try:
        return _run_cmd(cmd, timeout=timeout).strip()
    except Exception:
        return ""

def _getprop(serial: Optional[str], prop: str) -> Optional[str]:
    v = _adb_shell(serial, ["getprop", prop])
    return v if v else None

# ---------------------------------------------------------------------------
# device listing
# ---------------------------------------------------------------------------
def list_devices(include_emulator: bool = False) -> List[Dict[str, Any]]:
    path = adb_path()
    if not path:
        return []

    try:
        out = _run_cmd([path, "devices", "-l"], timeout=3.0)
    except Exception:
        return []

    devices = []
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        serial, state = parts[0], parts[1]
        if not include_emulator and serial.startswith("emulator-"):
            continue

        info = {"serial": serial, "state": state}
        for t in parts[2:]:
            if ":" in t:
                k, v = t.split(":", 1)
                info[k] = v
        devices.append(info)

    return devices

# ---------------------------------------------------------------------------
# stats helpers
# ---------------------------------------------------------------------------
def _read_mem(serial: str) -> Dict[str, Optional[int]]:
    """
    Returns MB used / total
    """
    txt = _adb_shell(serial, ["cat", "/proc/meminfo"])
    if not txt:
        return {}

    mem_total = None
    mem_free = None
    for line in txt.splitlines():
        if line.startswith("MemTotal"):
            mem_total = int(line.split()[1]) // 1024
        elif line.startswith("MemAvailable"):
            mem_free = int(line.split()[1]) // 1024

    if mem_total is None or mem_free is None:
        return {}

    return {
        "ram_total": mem_total,
        "ram_used": mem_total - mem_free
    }

def _read_storage(serial: str) -> Dict[str, Optional[int]]:
    """
    Returns GB used / total for /data
    """
    txt = _adb_shell(serial, ["df", "/data"])
    if not txt:
        return {}

    lines = txt.splitlines()
    if len(lines) < 2:
        return {}

    parts = lines[1].split()
    try:
        total = int(parts[1]) // (1024 * 1024)
        used = int(parts[2]) // (1024 * 1024)
        return {
            "storage_total": total,
            "storage_used": used
        }
    except Exception:
        return {}

def _read_cpu(serial: str) -> Optional[int]:
    """
    Returns approximate CPU usage %
    """
    txt = _adb_shell(serial, ["top", "-bn", "1"])
    if not txt:
        return None

    for line in txt.splitlines():
        if "CPU usage" in line or "cpu" in line.lower():
            import re
            m = re.search(r'(\d+)%', line)
            if m:
                return int(m.group(1))
    return None

# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------
def get_device_info(serial: Optional[str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "serial": serial,
        "connected": False,
        "model": None,
        "device": None,
        "manufacturer": None,
        "android_version": None,
        "sdk": None,
        "battery": None,
        "network": None,
        "signal": None,
        "ram_used": None,
        "ram_total": None,
        "storage_used": None,
        "storage_total": None,
        "cpu": None,
    }

    if not serial or not adb_exists():
        return result

    try:
        for d in list_devices(include_emulator=True):
            if d.get("serial") == serial:
                result["connected"] = d.get("state") == "device"
                break
    except Exception:
        pass

    result["model"] = _getprop(serial, "ro.product.model")
    result["device"] = _getprop(serial, "ro.product.device")
    result["manufacturer"] = _getprop(serial, "ro.product.manufacturer")
    result["android_version"] = _getprop(serial, "ro.build.version.release")
    result["sdk"] = _getprop(serial, "ro.build.version.sdk")

    # battery
    try:
        txt = _adb_shell(serial, ["dumpsys", "battery"])
        for l in txt.splitlines():
            if l.strip().lower().startswith("level:"):
                result["battery"] = int(l.split(":")[1].strip())
    except Exception:
        pass

    # network
    result["network"] = _getprop(serial, "gsm.network.type")

    # signal
    try:
        wifi = _adb_shell(serial, ["dumpsys", "wifi"])
        import re
        for l in wifi.splitlines():
            if "rssi" in l.lower():
                m = re.search(r'(-?\d+)', l)
                if m:
                    result["signal"] = max(0, min(100, 100 + int(m.group(1))))
                    break
    except Exception:
        pass

    # RAM / Storage / CPU
    result.update(_read_mem(serial))
    result.update(_read_storage(serial))
    result["cpu"] = _read_cpu(serial)

    return result

__all__ = [
    "adb_path",
    "adb_exists",
    "list_devices",
    "get_device_info",
]
