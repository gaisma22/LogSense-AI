from __future__ import annotations
import re
import subprocess
import time
from typing import Generator, Dict, Any, Optional
from app.log_android import adb_daemon
from app.log_android.adb_device import adb_path
from app.log_android.live_enricher import enrich_live_entry


def _map_level(entry: Dict[str, Any]) -> Dict[str, Any]:
    level = (entry.get("level") or "").upper()
    if level in ("F", "FATAL", "E", "ERROR"):
        entry["severity"] = "high"
    elif level in ("W", "WARN", "WARNING"):
        entry["severity"] = "moderate"
    else:
        entry["severity"] = "low"
    return entry


def _parse_logcat_line(line: str) -> Dict[str, Any]:
    raw = line.rstrip("\n")
    entry: Dict[str, Any] = {
        "raw": raw,
        "timestamp": None,
        "level": "I",
        "tag": None,
        "message": raw,
        "repeat_count": 1,
    }
    if m := re.search(r'(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})', raw):
        entry["timestamp"] = m.group(1)
    if m := re.search(r'\b([VDIWEF])\/([^\s:(]+)', raw):
        entry["level"] = m.group(1)
        entry["tag"] = m.group(2)
        try:
            entry["message"] = raw.split(":", 1)[1].strip()
        except Exception:
            pass
    return entry


def stream_logcat(serial: Optional[str] = None, fresh: bool = False) -> Generator[Dict[str, Any], None, None]:
    if fresh:
        # Bypass daemon buffer. Start a direct adb logcat subprocess from now.
        adb = adb_path()
        if not adb:
            return
        cmd = [adb]
        if serial:
            cmd += ["-s", serial]
        # -T 1: start from the last 1 entry, no backlog dump
        cmd += ["logcat", "-v", "time", "-T", "1"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            try:
                for line in proc.stdout:
                    if not line:
                        continue
                    entry = _parse_logcat_line(line)
                    entry = _map_level(entry)
                    entry = enrich_live_entry(entry)
                    yield entry
            except GeneratorExit:
                return
            finally:
                try:
                    proc.terminate()
                except Exception:
                    pass
        except Exception:
            return
    else:
        # Non-fresh: read from daemon buffer (used for background daemon mode)
        adb_daemon.start(serial)
        cursor = 0
        try:
            while True:
                advanced = False
                for cursor, item in adb_daemon.snapshot(cursor):
                    item = _map_level(item)
                    yield item
                    advanced = True
                if not advanced:
                    time.sleep(0.25)
        except GeneratorExit:
            return
