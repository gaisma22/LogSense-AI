# app/parser/evtx_parser.py
# .evtx binary parser. Converts Windows Event Log binary format to structured dicts.

from typing import List, Dict, Any

def parse_evtx(file_path: str) -> List[Dict[str, Any]]:
    try:
        from evtx import PyEvtxParser
    except ImportError:
        return [{"entry": ".evtx parsing requires the evtx package. Run: pip install evtx", "severity": "low", "section": "General", "explanation": "", "evidence": [], "os": "Windows", "threat": "None", "confidence": 0.0, "matched_patterns": [], "simplified": ""}]

    from app.parser.xml_parser import parse_windows_event_xml

    results = []
    try:
        parser = PyEvtxParser(file_path)
        for record in parser.records():
            try:
                xml_str = record['data']
                parsed = parse_windows_event_xml(xml_str)
                results.extend(parsed)
            except Exception:
                continue
    except Exception as e:
        return [{"entry": f"Failed to read .evtx file: {str(e)}", "severity": "low", "section": "General", "explanation": "", "evidence": [], "os": "Windows", "threat": "None", "confidence": 0.0, "matched_patterns": [], "simplified": ""}]

    return results
