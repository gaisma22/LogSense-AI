# app/model/analyze_lines.py
# Runs the parser over a list of log lines and returns structured dicts for the results page.

from typing import List, Dict
from app.parser.simplifier import normalize_line

def analyze_lines(lines: List[str]) -> List[Dict]:
    results: List[Dict] = []
    for ln in lines:
        # Normalize each line into a structured dict
        item = normalize_line(ln or "")
        # Ensure minimal compatibility keys exist (older UI relies on these)
        out = {
            "entry": item.get("entry", ""),
            "simplified": item.get("simplified", "") or "",
            "severity": item.get("severity", "low"),
            "section": item.get("section", "General"),
            "explanation": item.get("explanation", "")
        }
        # Include extras returned by the simplifier so UI or future components can use them
        # (don't override the required keys above)
        extras = {
            "evidence": item.get("evidence", []),
            "os": item.get("os", "Unknown"),
            "threat": item.get("threat", "None"),
            "confidence": item.get("confidence", 0.0),
            "matched_patterns": item.get("matched_patterns", [])
        }
        out.update(extras)
        results.append(out)
    return results
