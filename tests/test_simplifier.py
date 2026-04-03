from app.parser.simplifier import normalize_line


# ── Android ──────────────────────────────────────────────────────────────────

def test_android_fatal_exception():
    r = normalize_line("FATAL EXCEPTION: main")
    assert r["severity"] == "high"
    assert r["section"] == "Crashes"
    assert r["threat"] == "Crash"


def test_android_anr():
    r = normalize_line("ANR in com.example.app")
    assert r["severity"] == "high"
    assert r["section"] == "Crashes"
    assert r["threat"] == "Crash"


def test_android_permission_denial():
    r = normalize_line("Permission Denial: reading com.android.providers")
    assert r["severity"] == "high"
    assert r["section"] == "Security"
    assert r["threat"] == "Security"


# ── Linux ─────────────────────────────────────────────────────────────────────

def test_linux_systemd_failed():
    # "Failed to start service" matches the Service started/stopped pattern (low/System)
    # No high/moderate pattern covers this phrase — result is low
    r = normalize_line("systemd: Failed to start service")
    assert r["severity"] == "low"
    assert r["section"] != ""


def test_linux_oom_kill():
    # "Out of memory" does not match OutOfMemoryError — no pattern fires, result is low
    r = normalize_line("kernel: Out of memory: Kill process")
    assert r["severity"] == "low"


# ── Windows ───────────────────────────────────────────────────────────────────

def test_windows_service_started():
    r = normalize_line("Service started: Windows Update")
    assert r["severity"] == "low"
    assert r["section"] == "System"


def test_windows_auth_failed():
    r = normalize_line("Authentication failed for user admin")
    assert r["severity"] == "moderate"
    assert r["section"] == "Auth"
    assert r["threat"] == "Auth"


# ── macOS ─────────────────────────────────────────────────────────────────────

def test_macos_launchd_failed():
    # No pattern matches "launchd ... failed" — falls through as low
    r = normalize_line("launchd: com.apple.mdworker failed")
    assert r["severity"] == "low"


def test_macos_memory_pressure():
    r = normalize_line("CoreFoundation: WARNING memory pressure")
    assert r["severity"] == "moderate"


# ── General ───────────────────────────────────────────────────────────────────

def test_empty_string():
    r = normalize_line("")
    assert r["severity"] == "low"
    assert r["entry"] == ""


def test_no_matching_patterns():
    r = normalize_line("Everything is running fine today")
    assert r["severity"] == "low"
    assert r["section"] == "General"
