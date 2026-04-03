import threading
import time
import secrets

# In-RAM store only. No disk writes. Auto-expires.
_STORE = {}          # session_id -> {"data": [...], "expires": timestamp}
_TTL_DEFAULT = 86400  # 24 hours
_CLEANUP_INTERVAL = 1800  # 30 minutes


def generate_session_id():
    return secrets.token_hex(16)


def save(session_id, data, ttl=_TTL_DEFAULT):
    expires = time.time() + ttl
    _STORE[session_id] = {"data": data, "expires": expires}


def load(session_id):
    entry = _STORE.get(session_id)
    if not entry:
        return None

    if entry["expires"] < time.time():
        try:
            del _STORE[session_id]
        except KeyError:
            pass
        return None

    return entry["data"]


def remove(session_id):
    try:
        del _STORE[session_id]
    except KeyError:
        pass


def clean_expired():
    now = time.time()
    dead_keys = [sid for sid, v in _STORE.items() if v["expires"] < now]
    for sid in dead_keys:
        try:
            del _STORE[sid]
        except KeyError:
            pass


def _cleanup_loop():
    while True:
        try:
            clean_expired()
        except Exception:
            pass
        time.sleep(_CLEANUP_INTERVAL)


_cleanup_thread_started = False


def start_cleanup():
    global _cleanup_thread_started
    if _cleanup_thread_started:
        return

    t = threading.Thread(target=_cleanup_loop, daemon=True)
    t.start()
    _cleanup_thread_started = True
