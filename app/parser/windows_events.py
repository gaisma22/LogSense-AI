# app/parser/windows_events.py
# Windows Event ID lookup table and structured log parser.

import re
from typing import Dict, Any, Optional, List

# Event ID lookup table.
# Format: event_id -> (severity, section, explanation, threat)
EVENT_ID_MAP: Dict[int, tuple] = {
    # Security: high severity
    4625: ("high",     "Security",  "Login failed. Wrong credentials or account does not exist.", "Auth"),
    4648: ("high",     "Security",  "Login attempted with explicit credentials while already logged in. Possible pass-the-hash attack.", "Auth"),
    4672: ("high",     "Security",  "Admin privileges assigned at login.", "Privilege"),
    4720: ("high",     "Security",  "A user account was created.", "AccountChange"),
    4726: ("high",     "Security",  "A user account was deleted.", "AccountChange"),
    4732: ("high",     "Security",  "A user was added to a privileged local group.", "Privilege"),
    4756: ("high",     "Security",  "A user was added to a security group.", "Privilege"),
    1102: ("high",     "Security",  "Audit log was cleared. Someone may be covering tracks.", "Tampering"),
    104:  ("high",     "Security",  "Event log was cleared.", "Tampering"),
    5038: ("high",     "Security",  "Code integrity check failed. A system file may have been modified.", "Tampering"),
    5152: ("high",     "Security",  "Windows Firewall blocked a packet.", "Network"),
    4698: ("high",     "Security",  "A scheduled task was created. Check if this is expected.", "Persistence"),
    4688: ("high",     "Security",  "A new process was created.", "Execution"),
    # System: high severity
    41:   ("high",     "System",    "Kernel power failure. System was not shut down cleanly.", "Crash"),
    1000: ("high",     "Crashes",   "Application crashed.", "Crash"),
    6008: ("high",     "System",    "Unexpected shutdown. Power loss or system crash.", "Crash"),
    51:   ("high",     "Hardware",  "Disk error during a paging operation. Drive may be failing.", "Hardware"),
    # Network: moderate severity
    4201: ("moderate", "Network",   "Network connection lost.", "Network"),
    36887:("moderate", "Network",   "TLS fatal alert received from remote endpoint.", "Network"),
    36888:("moderate", "Network",   "TLS error generated.", "Network"),
    # Auth: moderate severity
    4740: ("moderate", "Auth",      "Account locked out after too many failed login attempts.", "Auth"),
    4624: ("low",      "Auth",      "Successful login.", "Auth"),
    4634: ("low",      "Auth",      "User logged off.", "Auth"),
    # System: low severity
    7036: ("low",      "System",    "A service started or stopped.", "System"),
    7040: ("low",      "System",    "Service start type was changed.", "System"),
    1001: ("low",      "System",    "Windows Error Reporting submitted a fault report.", "System"),
    6013: ("low",      "System",    "System uptime reported.", "System"),
}

# Windows level text to severity mapping
LEVEL_MAP: Dict[str, str] = {
    "critical":    "high",
    "error":       "high",
    "warning":     "moderate",
    "information": "low",
    "verbose":     "low",
    "audit failure": "high",
    "audit success": "low",
}

def _level_to_severity(level_str: str) -> str:
    return LEVEL_MAP.get((level_str or "").strip().lower(), "low")

def parse_windows_event_block(block: str) -> Optional[Dict[str, Any]]:
    """
    Parse one Windows Event Viewer text block into a structured dict.
    Expected format:
        Log Name: System
        Source: Service Control Manager
        Date: 2025-02-14 09:00:01
        Event ID: 7036
        Level: Information
        Description:
        The Windows Update service entered the running state.
    Returns None if block does not look like a Windows event.
    """
    lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
    if not lines:
        return None

    fields: Dict[str, str] = {}
    desc_lines: List[str] = []
    in_desc = False

    for line in lines:
        if in_desc:
            desc_lines.append(line)
            continue
        if line.lower().startswith("description:"):
            in_desc = True
            remainder = line[len("description:"):].strip()
            if remainder:
                desc_lines.append(remainder)
            continue
        for key in ("log name", "source", "date", "event id", "level"):
            if line.lower().startswith(key + ":"):
                fields[key] = line[len(key)+1:].strip()
                break

    if "event id" not in fields and "level" not in fields:
        return None

    event_id_raw = fields.get("event id", "")
    try:
        event_id = int(event_id_raw)
    except ValueError:
        event_id = None

    level_str = fields.get("level", "")
    description = " ".join(desc_lines).strip()
    source = fields.get("source", "")
    date = fields.get("date", "")
    log_name = fields.get("log name", "")

    # Build entry text for display
    entry_parts = []
    if date:
        entry_parts.append(date)
    if source:
        entry_parts.append(source)
    if event_id:
        entry_parts.append(f"EventID {event_id}")
    if description:
        entry_parts.append(description)
    entry = "  ".join(entry_parts)

    # Determine severity and explanation
    if event_id and event_id in EVENT_ID_MAP:
        severity, section, explanation, threat = EVENT_ID_MAP[event_id]
        if description:
            explanation = explanation + " " + description
    else:
        severity = _level_to_severity(level_str)
        section = log_name or "General"
        threat = "None"
        explanation = description or f"{source} logged a {level_str.lower() or 'system'} event."

    return {
        "entry": entry,
        "simplified": description[:180] if description else entry[:180],
        "severity": severity,
        "section": section,
        "explanation": explanation,
        "evidence": [],
        "os": "Windows",
        "threat": threat,
        "confidence": 0.9 if event_id in (EVENT_ID_MAP or {}) else 0.4,
        "matched_patterns": [{"event_id": event_id}] if event_id else [],
        "timestamp": date,
        "source": source,
        "event_id": event_id,
        "log_name": log_name,
    }


def parse_windows_event_blocks(text: str) -> List[Dict[str, Any]]:
    """
    Split text into Windows event blocks and parse each one.
    Blocks are separated by a blank line or a new 'Log Name:' line.
    """
    results = []
    current: List[str] = []

    for line in text.splitlines():
        if line.strip().lower().startswith("log name:") and current:
            block = "\n".join(current)
            parsed = parse_windows_event_block(block)
            if parsed:
                results.append(parsed)
            current = [line]
        else:
            current.append(line)

    if current:
        block = "\n".join(current)
        parsed = parse_windows_event_block(block)
        if parsed:
            results.append(parsed)

    return results


def looks_like_windows_event_log(text: str) -> bool:
    """
    Quick heuristic: does this text look like a Windows Event Viewer export?
    """
    lower = text.lower()
    return (
        "log name:" in lower and
        "event id:" in lower and
        "level:" in lower
    )
