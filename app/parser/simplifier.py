# app/parser/simplifier.py
# Rule-based log parser. Classifies log lines by severity, section, and threat type.
# Returns structured output: severity, explanation, confidence, matched patterns, OS guess.

import re
from typing import Dict, Optional, List, Tuple

# Severity constants (string labels used across UI)
SEV_HIGH = "high"
SEV_MOD = "moderate"
SEV_LOW = "low"

# Helper mapping for severity weight (used to compute confidence)
_SEV_WEIGHT = {SEV_HIGH: 3.0, SEV_MOD: 2.0, SEV_LOW: 1.0}

# Pattern table: (regex, severity, section, short_summary, threat_tag, explanation_template)
# explanation_template is a short human-friendly phrase; final explanation will append Matched token(s).
PATTERNS: List[Tuple[re.Pattern, str, str, str, str, str]] = [
    # HIGH - Crashes & signals
    (re.compile(r'\bANR in\b', re.I), SEV_HIGH, 'Crashes', 'App not responding', 'Crash',
     "ANR detected"),  # ANR
    (re.compile(r'\bFATAL EXCEPTION\b', re.I), SEV_HIGH, 'Crashes', 'Fatal exception', 'Crash',
     "Fatal exception (application crash)"),
    (re.compile(r'NullPointerException', re.I), SEV_HIGH, 'Crashes', 'Null pointer crash', 'Crash',
     "NullPointerException (null reference)"),
    (re.compile(r'OutOfMemoryError', re.I), SEV_HIGH, 'Crashes', 'Out of memory', 'Crash',
     "OutOfMemoryError (heap exhausted)"),
    (re.compile(r'\bSIG(?:SEGV|ABRT|BUS|ILL)\b', re.I), SEV_HIGH, 'Crashes', 'Native crash / signal', 'Crash',
     "Native crash signal (segfault/abort)"),

    # HIGH - Clear privilege escalation / rooting / suspicious execution
    (re.compile(r'\b(?:\b|/)(?:su\b|magisk\b|superuser\b|/system/xbin/|/system/bin/su|/sbin/su)\b', re.I),
     SEV_HIGH, 'Security', 'Root / su activity', 'Rooting',
     "Root/superuser indicator"),
    (re.compile(r'Runtime\.getRuntime\(\)\.exec|exec\(|/system/bin/sh\b|sh -c\b|ProcessBuilder|powershell\b|cmd\.exe\b',
                re.I),
     SEV_HIGH, 'Security', 'Command execution', 'Execution',
     "Shell/command execution detected"),
    (re.compile(r'DexClassLoader|PathClassLoader|UnsatisfiedLinkError', re.I),
     SEV_HIGH, 'Security', 'Dynamic/native load', 'Tampering',
     "Dynamic code / native load indicator"),
    (re.compile(r'\brm -rf\b|dd if=|dd of=|mount -o remount\b|remount rw\b|chmod 777\b|chown root\b', re.I),
     SEV_HIGH, 'Security', 'Privileged filesystem operation', 'Destructive',
     "Destructive or privileged filesystem operation"),

    # HIGH - Permission & IPC problems
    (re.compile(r'Permission Denial|permission denied', re.I), SEV_HIGH, 'Security', 'Permission denied', 'Security',
     "Permission denial (access blocked)"),
    (re.compile(r'\bdead object\b|\bFailed binder transaction\b|\bBinder transaction failed\b', re.I),
     SEV_HIGH, 'IPC', 'IPC/Binder failure', 'IPC',
     "Severe IPC or binder failure"),
    (re.compile(r'\bgetDeviceId|getSubscriberId|readContacts|readSMS|getAccounts\b', re.I),
     SEV_HIGH, 'Privacy', 'Sensitive data access', 'Privacy',
     "Access to sensitive identifiers/data"),

    # MODERATE - IO, network, auth, warnings
    (re.compile(r'\bIOException\b|\bI/O error\b', re.I), SEV_MOD, 'I/O', 'I/O error', 'I/O',
     "I/O failure (read/write/network)"),
    (re.compile(r'\b(timeout|timed out)\b', re.I), SEV_MOD, 'Network/Timeouts', 'Timeout', 'Network',
     "Operation timed out"),
    (re.compile(r'Connection refused|No route to host|Network is unreachable', re.I), SEV_MOD, 'Network',
     'Network connectivity issue', 'Network',
     "Network connectivity issue"),
    (re.compile(r'SSLHandshakeException|\bcertificate (expired|invalid|revoked|untrusted)\b', re.I),
     SEV_MOD, 'Network', 'TLS/SSL issue', 'Network',
     "TLS/SSL handshake or certificate problem"),
    (re.compile(r'\bSecurityException\b', re.I), SEV_MOD, 'Security', 'Security exception', 'Security',
     "SecurityException occurred"),
    (re.compile(r'Authentication failed|Auth failed|login failed|invalid credentials', re.I), SEV_MOD, 'Auth',
     'Authentication failure', 'Auth',
     "Authentication or login failure"),
    (re.compile(r'camera (failed|disabled|error)', re.I), SEV_MOD, 'Hardware', 'Camera problem', 'Hardware',
     "Camera subsystem error"),
    (re.compile(r'\bWARNING\b', re.I), SEV_MOD, 'General', 'Warning', 'Warning',
     "Warning-level log"),
    (re.compile(r'\bLowMemory\b|\bmemory pressure\b|\btrim memory\b', re.I), SEV_MOD, 'Performance', 'Memory pressure',
     'Performance',
     "Memory pressure or low-memory warning"),

    # LOW - informational, normal operations
    (re.compile(r'(?:(?:^|\s)I/|\bINFO\b|\bDEBUG\b|\bVERBOSE\b)', re.I), SEV_LOW, 'General', 'Informational', 'Info',
     "Informational or debug"),
    (re.compile(r'\bGET\b|\bPOST\b|\b200 OK\b|\b304\b', re.I), SEV_LOW, 'Network', 'HTTP/info', 'Network',
     "Normal HTTP/network activity"),
    # Windows service logs etc. (keep low unless other signals)
    (re.compile(r'Service started|Service stopped|Started service', re.I), SEV_LOW, 'System', 'Service event', 'System',
     "Service start/stop informational"),
]

# Short package or identifier extractor for better summaries
PACKAGE_RE = re.compile(r'\b([a-z][a-z0-9_]*\.)+([a-z][a-z0-9_]*)\b', re.I)

# OS detection heuristics: regex -> OS label
_OS_PATTERNS = [
    (re.compile(r'\bAndroid\b|\blogcat\b|\badb\b', re.I), 'Android'),
    (re.compile(r'\bWindows\b|\\Windows NT\b|EventLog|Event Viewer|Win32', re.I), 'Windows'),
    (re.compile(r'\bmacOS\b|\bDarwin\b|CoreFoundation|launchd\b', re.I), 'macOS'),
    (re.compile(r'\bLinux\b|\bsystemd\b|\bukernel\b|\bjournalctl\b', re.I), 'Linux'),
]


def _detect_os(line: str) -> str:
    """Simple heuristics to guess the OS the log line originates from."""
    for rx, label in _OS_PATTERNS:
        if rx.search(line):
            return label
    # fallback to keyword cues
    if re.search(r'\b/var/|/proc/|/sys/|systemd|journalctl', line, re.I):
        return 'Linux'
    if re.search(r'\\Windows|C:\\', line):
        return 'Windows'
    return 'Unknown'


def _short_package_name(s: str) -> str:
    """Return last segment of dotted package name (com.example.app -> app)."""
    m = PACKAGE_RE.search(s)
    if not m:
        return ''
    segment = m.group(2).lower()
    # reject single generic words that leak from file paths
    _IGNORE = {'log', 'txt', 'xml', 'cfg', 'conf', 'ini', 'dat', 'tmp', 'bak', 'out', 'err', 'service', 'dispatcher'}
    if segment in _IGNORE:
        return ''
    return m.group(2)


def _accumulate_matches(line: str) -> List[Dict]:
    """
    Run through PATTERNS and return list of matches with context.
    Each match record: {severity, section, summary, threat, explanation, token, pattern_index}
    """
    matches = []
    for idx, (rx, sev, section, summary, threat, expl) in enumerate(PATTERNS):
        m = rx.search(line)
        if m:
            token = m.group(0).strip()
            matches.append({
                "severity": sev,
                "section": section,
                "summary": summary,
                "threat": threat,
                "explanation": expl,
                "token": token,
                "pattern_index": idx
            })
    return matches


def _choose_final_severity(matches: List[Dict]) -> str:
    """
    Decide final severity given list of matches.
    Strategy:
      - If any HIGH match -> high (but still compute confidence)
      - Else if any MODERATE -> moderate
      - Else low
      - If no pattern matches, heuristics (exception -> high, 'error' -> moderate).
    """
    if not matches:
        return SEV_LOW
    severities = {m["severity"] for m in matches}
    if SEV_HIGH in severities:
        return SEV_HIGH
    if SEV_MOD in severities:
        return SEV_MOD
    return SEV_LOW


def _compute_confidence(matches: List[Dict], final_sev: str, line: str) -> float:
    """
    Compute a simple confidence score (0.0..1.0).
    Heuristics:
      - Use weighted sum of matched severities vs. maximum possible.
      - Boost if multiple high/mod matches present.
      - Slight boost if keyword 'exception' or 'error' present and matches align.
    """
    if not matches:
        # fallback: check keywords
        base = 0.10
        if 'exception' in line.lower():
            return 0.6
        if re.search(r'\berror\b', line, re.I):
            return 0.35
        return base

    total_weight = 0.0
    score = 0.0
    for m in matches:
        w = _SEV_WEIGHT.get(m["severity"], 1.0)
        total_weight += w
        # add more if match severity equals final severity
        score += w if m["severity"] == final_sev else (w * 0.6)

    if total_weight <= 0:
        return 0.25

    raw = score / total_weight  # 0..1 scale
    # emphasize multiple matches of same high severity
    if final_sev == SEV_HIGH:
        high_count = sum(1 for m in matches if m["severity"] == SEV_HIGH)
        if high_count >= 2:
            raw = min(1.0, raw + 0.15)
    # small boosts for 'exception' token alignment
    if 'exception' in line.lower() and final_sev == SEV_HIGH:
        raw = min(1.0, raw + 0.05)
    # clamp
    return round(max(0.0, min(1.0, raw)), 2)


def _build_explanation(matches: List[Dict], final_sev: str, line: str) -> str:
    """
    Build a user-facing explanation:
    - Primary sentence describing why severity assigned.
    - Include matched tokens and short advice where appropriate.
    Keep language simple and actionable.
    """
    if matches:
        # Prefer highest-priority match (lowest pattern_index)
        matches_sorted = sorted(matches, key=lambda m: (m["pattern_index"], -_SEV_WEIGHT.get(m["severity"], 1.0)))
        top = matches_sorted[0]
        # core explanation based on top match
        expl = f"{top['explanation']}. Matched token: '{top['token']}'."
        # Add short context if multiple matches
        if len(matches) > 1:
            extra = []
            for m in matches_sorted[1:3]:  # up to 2 extras
                extra.append(f"'{m['token']}' ({m['summary']})")
            if extra:
                expl = expl + " Other indicators: " + ", ".join(extra) + "."
        # If severity is high and threat is security/privacy, add action hint
        if final_sev == SEV_HIGH and top.get("threat") in ("Rooting", "Tampering", "Destructive", "Privacy", "Security"):
            expl = expl + " Check surrounding lines for the process name and timestamp. Look for related entries within the same second."
        # For crashes, suggest looking for stacktrace lines nearby
        if final_sev == SEV_HIGH and top.get("section") == "Crashes":
            expl = expl + " Hint: check adjacent lines for 'at <class>' stacktrace entries."
        return expl
    # no matches - fallback heuristics
    if 'exception' in line.lower():
        return "Line contains 'exception'. Check nearby lines for the full stacktrace."
    if re.search(r'\berror\b', line, re.I):
        return "Line contains 'error'. Check surrounding entries for more context."
    # default
    return "No known issues matched. This line appears informational."

# -------------------------
# Public API
# normalize_line(line: str) -> Dict
# Keys: entry, simplified, severity, section, explanation, evidence, os, threat, confidence, matched_patterns
# -------------------------
def normalize_line(line: str) -> Dict:
    original = line if isinstance(line, str) else str(line or "")

    # Quick trim
    s = original.strip()

    # Very short/empty
    if not s:
        return {
            "entry": original,
            "simplified": "",
            "severity": SEV_LOW,
            "section": "General",
            "explanation": "",
            "evidence": [],
            "os": "Unknown",
            "threat": "None",
            "confidence": 0.0,
            "matched_patterns": []
        }

    # 0) Detect OS early (helps some pattern decisions)
    os_guess = _detect_os(s)

    # 1) Normalize/clean common prefixes (timestamps/PID columns) without losing text content
    clean = re.sub(r'^\s*\d{4}-\d{1,2}-\d{1,2}[ T]\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s*', '', s)
    clean = re.sub(r'^\s*\d{1,2}-\d{1,2}\s+\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\s*', '', clean)
    clean = re.sub(r'\(\s*\d+\s*\)\s*:', '', clean)  # (1234):
    clean = re.sub(r'^\s*\d+\s+\d+\s+', '', clean)    # "1234 5678 " style
    clean = clean.strip()

    # 2) Collect all pattern matches (multi-hit)
    matches = _accumulate_matches(clean)

    # 3) If no pattern matches, use fallback heuristics for severity
    final_sev = _choose_final_severity(matches)
    # heuristics if nothing matched
    if not matches:
        if 'exception' in clean.lower():
            final_sev = SEV_HIGH
        elif re.search(r'\berror\b', clean, re.I):
            final_sev = SEV_MOD
        else:
            final_sev = SEV_LOW

    # 4) compute confidence
    confidence = _compute_confidence(matches, final_sev, clean)

    # 5) build explanation
    explanation = _build_explanation(matches, final_sev, clean)

    # 6) determine top section and threat tag from highest priority match or heuristics
    threat_tag = "None"
    section = "General"
    simplified = clean if len(clean) <= 180 else (clean[:180] + "…")
    matched_patterns = []
    evidence = []
    if matches:
        # choose top match: lowest pattern_index (first in table), then highest severity
        top = sorted(matches, key=lambda m: (m["pattern_index"], -_SEV_WEIGHT.get(m["severity"], 1.0)))[0]
        section = top.get("section", section)
        threat_tag = top.get("threat", threat_tag)
        # create short simplified summary using top summary + package if present
        pkg_short = _short_package_name(clean)
        summary = top.get("summary", "")
        if pkg_short and pkg_short.lower() not in summary.lower():
            simplified = f"{summary} ({pkg_short})"
        else:
            simplified = summary
        # collect matched_patterns and evidence
        for m in matches:
            matched_patterns.append({
                "pattern_index": m["pattern_index"],
                "token": m["token"],
                "summary": m["summary"],
                "severity": m["severity"],
                "section": m["section"],
                "threat": m["threat"]
            })
            evidence.append({
                "token": m["token"],
                "why": m["explanation"]
            })
    else:
        # no matches -> small heuristics for section/threat
        if 'exception' in clean.lower():
            section = "Crashes"
            threat_tag = "Crash"
            simplified = "Exception"
        elif re.search(r'\berror\b', clean, re.I):
            section = "General"
            threat_tag = "Error"
            simplified = "Error"
        else:
            section = "General"
            threat_tag = "Info"

    # Final output dict must include the original keys used by templates/routes plus extras
    out = {
        "entry": original,
        "simplified": simplified,
        "severity": final_sev,
        "section": section,
        "explanation": explanation,
        # extras
        "evidence": evidence,               # list of {token, why}
        "os": os_guess,                     # detected OS label
        "threat": threat_tag,               # coarse threat tag
        "confidence": confidence,           # 0.0..1.0
        "matched_patterns": matched_patterns
    }

    return out
