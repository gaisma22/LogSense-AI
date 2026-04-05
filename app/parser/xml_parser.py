# app/parser/xml_parser.py
# XML log parser. Handles Windows Event Log XML and generic XML formats.

from typing import List, Dict, Any
import xmltodict

def _safe_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        return val.get("#text", "") or ""
    return str(val)

def _is_useful(s: str) -> bool:
    if not s or not s.strip():
        return False
    sl = s.strip()
    if sl.startswith("S-1-"):
        return False
    if sl.startswith("0x"):
        return False
    if sl.startswith("{"):
        return False
    if sl.startswith("%%"):
        return False
    if sl == "-":
        return False
    return True


def parse_windows_event_xml(text: str) -> List[Dict[str, Any]]:
    """
    Parse Windows Event Log XML export.
    Expected structure: <Events><Event>...</Event></Events>
    or a single <Event> element.
    """
    from app.parser.windows_events import EVENT_ID_MAP, _level_to_severity

    try:
        parsed = xmltodict.parse(text, force_list=("Event",))
    except Exception:
        return []

    root = parsed.get("Events") or parsed
    events_raw = root.get("Event", []) if isinstance(root, dict) else []

    if not events_raw:
        return []

    results = []
    for ev in events_raw:
        if not isinstance(ev, dict):
            continue

        system = ev.get("System") or {}
        event_data = ev.get("EventData") or {}

        event_id_raw = _safe_str(system.get("EventID", ""))
        try:
            event_id = int(event_id_raw)
        except ValueError:
            event_id = None

        level_raw = _safe_str(system.get("Level", ""))
        provider = _safe_str((system.get("Provider") or {}).get("@Name", ""))
        time_created = _safe_str((system.get("TimeCreated") or {}).get("@SystemTime", ""))
        channel = _safe_str(system.get("Channel", ""))

        # Extract message data
        data_parts = []
        if isinstance(event_data, dict):
            data_vals = event_data.get("Data", [])
            if isinstance(data_vals, list):
                for d in data_vals:
                    s = _safe_str(d)
                    if s:
                        data_parts.append(s)
            else:
                s = _safe_str(data_vals)
                if s:
                    data_parts.append(s)

        clean_parts = [p for p in data_parts if _is_useful(p)]
        description = " ".join(clean_parts).strip()

        entry_parts = []
        if time_created:
            entry_parts.append(time_created[:19].replace("T", " "))
        if provider:
            entry_parts.append(provider)
        if event_id:
            entry_parts.append(f"EventID {event_id}")
        entry = "  ".join(entry_parts)
        entry = entry[:220] if len(entry) > 220 else entry

        if event_id and event_id in EVENT_ID_MAP:
            severity, section, explanation, threat = EVENT_ID_MAP[event_id]
            confidence = 0.9
            matched = [{"event_id": event_id}]
        else:
            try:
                level_int = int(level_raw)
                level_map = {1: "high", 2: "high", 3: "moderate", 4: "low", 5: "low"}
                severity = level_map.get(level_int, "low")
            except ValueError:
                severity = _level_to_severity(level_raw)
            section = channel or "General"
            threat = "None"
            if provider and event_id:
                explanation = f"{provider} logged event {event_id}."
            elif provider:
                explanation = f"{provider} logged an event."
            else:
                explanation = "An unrecognized Windows event was logged."
            confidence = 0.4
            matched = []

        raw_data = "  ".join([p for p in data_parts if p.strip()])
        results.append({
            "entry": entry,
            "simplified": explanation[:180],
            "severity": severity,
            "section": section,
            "explanation": explanation,
            "evidence": [],
            "os": "Windows",
            "threat": threat,
            "confidence": confidence,
            "matched_patterns": matched,
            "timestamp": time_created[:19].replace("T", " ") if time_created else "",
            "source": provider,
            "event_id": event_id,
            "log_name": channel,
            "raw_data": raw_data,
        })

    return results


def parse_generic_xml(text: str) -> List[Dict[str, Any]]:
    """
    Fallback for non-Windows XML log files.
    Flattens XML structure into key-value text and feeds into the main parser.
    """
    from app.parser.simplifier import normalize_line

    try:
        parsed = xmltodict.parse(text)
    except Exception:
        return []

    def flatten(obj: Any, prefix: str = "") -> List[str]:
        lines = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                lines.extend(flatten(v, f"{k}: " if not prefix else f"{prefix}{k}: "))
        elif isinstance(obj, list):
            for item in obj:
                lines.extend(flatten(item, prefix))
        else:
            if obj is not None:
                lines.append(f"{prefix}{obj}")
        return lines

    lines = flatten(parsed)
    results = []
    for line in lines:
        if line.strip():
            results.append(normalize_line(line))
    return results


def looks_like_windows_event_xml(text: str) -> bool:
    stripped = text.strip()[:500].lower()
    return "<event" in stripped and ("<system>" in stripped or "xmlns" in stripped)
