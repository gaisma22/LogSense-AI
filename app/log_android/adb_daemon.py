# app/log_android/adb_daemon.py
# Persistent ADB logcat daemon with monotonic ring buffer
# Owns adb process. Never tied to HTTP lifecycle.

from __future__ import annotations

import threading
import subprocess
import time
import re
from collections import deque
from typing import Optional, Dict, Any, Deque, Tuple

from app.log_android.adb_device import adb_path

BUFFER_SIZE = 5000
_RESTART_DELAY = 2.0

_lock = threading.Lock()
_buffer: Deque[Tuple[int, Dict[str, Any]]] = deque(maxlen=BUFFER_SIZE)

_thread: Optional[threading.Thread] = None
_running = False
_serial: Optional[str] = None
_seq = 0  # monotonic cursor

# ---------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------
TS_RE = re.compile(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})')
LV_RE = re.compile(r'\b([VDIWEF])\/')

LV_MAP = {
    "V": "VERBOSE",
    "D": "DEBUG",
    "I": "INFO",
    "W": "WARN",
    "E": "ERROR",
    "F": "FATAL",
}


# ---------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------
def _parse(line: str) -> Dict[str, Any]:
    raw = line.rstrip("\n")
    out: Dict[str, Any] = {
        "raw": raw,
        "timestamp": None,
        "level": "INFO",
        "tag": None,
        "pid": None,
        "tid": None,
        "message": raw,
        "repeat_count": 1,
        # enrichment
        "explanation": None,
        "impact": None,
        "action_hint": None,
        "confidence": None,
        "_ts_monotonic": time.monotonic(),
    }

    if m := TS_RE.search(raw):
        out["timestamp"] = m.group(1)

    if m := LV_RE.search(raw):
        out["level"] = LV_MAP.get(m.group(1), "INFO")

    if m := re.search(r'[VDIWEF]\/([^\s:()]+)', raw):
        out["tag"] = m.group(1)
        try:
            out["message"] = raw.split(":", 1)[1].strip()
        except Exception:
            pass

    if m := re.search(r'\b(\d{2,6})\s+(\d{2,6})\b', raw):
        try:
            out["pid"] = int(m.group(1))
            out["tid"] = int(m.group(2))
        except Exception:
            pass

    return out

# ---------------------------------------------------------------------
# Repeat / identity helpers
# ---------------------------------------------------------------------
def _signature(entry: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        entry.get("level") or "",
        entry.get("tag") or "",
        entry.get("message") or "",
    )

# ---------------------------------------------------------------------
# Daemon loop
# ---------------------------------------------------------------------
def _daemon_loop():
    global _running, _seq

    last_sig: Optional[Tuple[str, str, str]] = None
    last_entry: Optional[Dict[str, Any]] = None

    while _running:
        adb = adb_path()
        if not adb:
            time.sleep(_RESTART_DELAY)
            continue

        cmd = [adb]
        if _serial:
            cmd += ["-s", _serial]
        cmd += ["logcat", "-v", "time"]

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            while _running:
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue

                entry = _parse(line)
                sig = _signature(entry)

                with _lock:
                    # Repeat compaction (Tier 3.2)
                    if sig == last_sig and last_entry is not None:
                        last_entry["repeat_count"] += 1
                        continue

                    # Commit log
                    _seq += 1
                    _buffer.append((_seq, entry))
                    last_sig = sig
                    last_entry = entry

        except Exception:
            time.sleep(_RESTART_DELAY)

        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            time.sleep(_RESTART_DELAY)

# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------
def start(serial: Optional[str] = None):
    global _thread, _running, _serial

    with _lock:
        if _running and serial == _serial:
            return
        _serial = serial
        _running = True

    if not _thread or not _thread.is_alive():
        _thread = threading.Thread(target=_daemon_loop, daemon=True)
        _thread.start()

def snapshot(since: int = 0):
    with _lock:
        data = list(_buffer)

    for seq, item in data:
        if seq > since:
            yield seq, item

