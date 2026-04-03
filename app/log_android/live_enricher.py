# app/log_android/live_enricher.py
from __future__ import annotations
from typing import Dict, Any

from app.parser.simplifier import normalize_line

_KNOWN_NOISE_TAGS = {
    'dumpsys', 'df', 'BBinder', 'Binder', 'servicemanager',
    'hwservicemanager', 'vndservicemanager', 'linker', 'ziparchive',
    'GraphicBuffer', 'Gralloc', 'AHardwareBuffer', 'qdgralloc',
    'PhBaseOp', 'BoundBrokerSvc', 'GCloudVoice', 'GVoiceAndroidLog',
}


def _is_noise(entry: Dict[str, Any]) -> bool:
    tag = (entry.get("tag") or "").strip()
    return tag in _KNOWN_NOISE_TAGS or any(tag.startswith(n) for n in _KNOWN_NOISE_TAGS)


def _triage(entry: Dict[str, Any], parsed: Dict[str, Any]) -> Dict[str, Any]:
    level = (entry.get("level") or "I").upper()
    has_pattern = bool(parsed.get("matched_patterns"))
    severity = parsed.get("severity", "low")

    if has_pattern and severity == "high":
        return {
            "triage": "investigate",
            "triage_label": "Needs attention",
            "triage_reason": parsed.get("explanation", "A known issue pattern was detected."),
            "action": "Click to see details and check surrounding log entries.",
        }

    if has_pattern and severity == "moderate":
        return {
            "triage": "monitor",
            "triage_label": "Worth a look",
            "triage_reason": parsed.get("explanation", "A potential issue was detected."),
            "action": "Not urgent. Monitor if this repeats frequently.",
        }

    if not has_pattern and level in ("E", "ERROR"):
        if _is_noise(entry):
            return {
                "triage": "ignore",
                "triage_label": "Safe to ignore",
                "triage_reason": "System background process. Normal activity.",
                "action": None,
            }
        return {
            "triage": "monitor",
            "triage_label": "Worth a look",
            "triage_reason": f"Error from {entry.get('tag', 'unknown')}. No known pattern matched.",
            "action": "Check if this repeats or if the app behaves unexpectedly.",
        }

    if not has_pattern and level in ("W", "WARN", "WARNING"):
        if _is_noise(entry):
            return {
                "triage": "ignore",
                "triage_label": "Safe to ignore",
                "triage_reason": "System background activity. Nothing unusual.",
                "action": None,
            }
        return {
            "triage": "monitor",
            "triage_label": "Worth a look",
            "triage_reason": f"Warning from {entry.get('tag', 'unknown')}.",
            "action": "Monitor if this appears frequently.",
        }

    if level in ("F", "FATAL"):
        return {
            "triage": "investigate",
            "triage_label": "Needs attention",
            "triage_reason": "A process crashed or was killed.",
            "action": "Check which app crashed and look at surrounding error lines.",
        }

    return {
        "triage": "ignore",
        "triage_label": "Safe to ignore",
        "triage_reason": "Informational system activity. Normal.",
        "action": None,
    }


def enrich_live_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(entry)
    message = entry.get("message") or entry.get("raw") or ""
    parsed = normalize_line(message)

    triage_data = _triage(entry, parsed)
    enriched.update(triage_data)

    if parsed.get("matched_patterns"):
        enriched["severity"] = parsed["severity"]
        enriched["section"] = parsed.get("section", "General")
        enriched["threat"] = parsed.get("threat", "None")
        enriched["what_happened"] = parsed.get("explanation", "")
        enriched["confidence"] = parsed.get("confidence", 0.0)
        enriched["matched_patterns"] = parsed.get("matched_patterns", [])
    else:
        enriched["what_happened"] = ""
        enriched["confidence"] = 0.0
        enriched["matched_patterns"] = []

    enriched.pop("explanation", None)
    enriched.pop("impact", None)
    enriched.pop("action_hint", None)

    return enriched
