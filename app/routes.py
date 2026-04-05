# app/routes.py
from __future__ import annotations

import io
import csv
import json
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    Response,
    jsonify,
    make_response,
    current_app,
    stream_with_context,
)

from app.model.analyze_lines import analyze_lines
from app.utils.session_store import (
    generate_session_id, save, load,
    start_cleanup,
)

# Android helpers
try:
    from app.log_android.adb_device import adb_exists, list_devices, get_device_info
except Exception:
    def adb_exists() -> bool:
        return False
    def list_devices(include_emulator: bool = False):
        return []
    def get_device_info(serial: Optional[str]) -> Dict[str, Any]:
        return {}

try:
    from app.log_android.adb_stream import stream_logcat
except Exception:
    def stream_logcat(serial: Optional[str] = None):
        if False:
            yield
        return

# Live enrichment engine
from app.log_android.live_enricher import enrich_live_entry

routes = Blueprint("routes", __name__)

ALLOWED_EXT = {'.txt', '.log', '.xml', '.evtx'}

try:
    start_cleanup()
except Exception:
    pass


def allowed_file(filename: Optional[str]) -> bool:
    if not filename:
        return False
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT


def read_file_safely(fl) -> Optional[str]:
    try:
        raw = fl.stream.read() if hasattr(fl, 'stream') else fl.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8", errors="ignore")
        return str(raw)
    except Exception:
        return None


def enforce_line_limit(lines, limit):
    return lines[:limit] if len(lines) > limit else lines


# -------------------------------------------------------------------------
# Pages
# -------------------------------------------------------------------------
@routes.route("/")
def home_page():
    return render_template("index.html")


@routes.route("/upload", methods=["GET", "POST"])
def upload_page():
    if request.method == "GET":
        return render_template("upload.html")

    fl = request.files.get("file")
    if not fl or not fl.filename:
        flash("No file uploaded.")
        return redirect(url_for("routes.upload_page"))

    _, ext = os.path.splitext((fl.filename or '').lower())
    if not allowed_file(fl.filename):
        flash("Unsupported file type. Supported formats: .log, .txt, .xml, .evtx")
        return redirect(url_for("routes.upload_page"))

    content = read_file_safely(fl)
    if not content and ext != '.evtx':
        flash("File unreadable.")
        return redirect(url_for("routes.upload_page"))

    if ext == '.evtx':
        import tempfile, os as _os
        from app.parser.evtx_parser import parse_evtx
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.evtx') as tmp:
                fl.stream.seek(0)
                tmp.write(fl.stream.read())
                tmp_path = tmp.name
            results = parse_evtx(tmp_path)
        except Exception:
            current_app.logger.exception("evtx parse failed")
            flash("Failed to read .evtx file.")
            return redirect(url_for("routes.upload_page"))
        finally:
            try:
                _os.unlink(tmp_path)
            except Exception:
                pass
    elif ext == '.xml':
        from app.parser.xml_parser import looks_like_windows_event_xml, parse_windows_event_xml, parse_generic_xml
        if looks_like_windows_event_xml(content):
            results = parse_windows_event_xml(content)
        else:
            lines = enforce_line_limit(
                [l for l in content.splitlines() if l.strip()],
                current_app.config["MAX_LINES"]
            )
            results = parse_generic_xml(content) if content.strip().startswith('<') else analyze_lines(lines)
    else:
        from app.parser.windows_events import looks_like_windows_event_log, parse_windows_event_blocks
        lines = enforce_line_limit(
            [l for l in content.splitlines() if l.strip()],
            current_app.config["MAX_LINES"]
        )
        if looks_like_windows_event_log(content):
            results = parse_windows_event_blocks(content)
        else:
            results = analyze_lines(lines)

    if not results:
        results = []

    sid = generate_session_id()
    save(sid, results, ttl=86400)

    resp = make_response(
        render_template("results.html", entries=results, total=len(results))
    )
    resp.set_cookie("logsense_sid", sid, max_age=86400, httponly=True, samesite="Lax")
    return resp


@routes.route("/results")
def results_page():
    sid = request.cookies.get("logsense_sid")
    entries = load(sid) if sid else []
    return render_template("results.html", entries=entries or [], total=len(entries or []))


@routes.route("/about")
def about_page():
    return render_template("about.html")


@routes.route("/faq")
def faq_page():
    return render_template("faq.html")


@routes.route("/instructions")
def instructions_page():
    return render_template("instructions.html")


# -------------------------------------------------------------------------
# Android status
# -------------------------------------------------------------------------
@routes.route("/android/status")
def android_status():
    result = {"adb_available": False, "devices": []}
    try:
        from app.log_android import adb_daemon
        adb_daemon.start()
        if not adb_exists():
            return jsonify(result)

        result["adb_available"] = True
        for d in list_devices(include_emulator=False):
            serial = d.get("serial")
            info = get_device_info(serial) or {}
            result["devices"].append({
                "serial": serial,
                "connected": info.get("connected"),
                "model": info.get("model"),
                "android_version": info.get("android_version"),
                "battery": info.get("battery"),
                "net": info.get("network"),
                "signal": info.get("signal"),
                "ram_used": info.get("ram_used"),
                "ram_total": info.get("ram_total"),
                "storage_used": info.get("storage_used"),
                "storage_total": info.get("storage_total"),
                "cpu": info.get("cpu"),
            })
        return jsonify(result)
    except Exception:
        current_app.logger.exception("android/status failed")
        return jsonify(result)



# -------------------------------------------------------------------------
# SSE helpers
# -------------------------------------------------------------------------
def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


# -------------------------------------------------------------------------
# Android live stream (ENRICHED + DEVICE META)
# -------------------------------------------------------------------------
@routes.route("/android/stream/live")
def android_stream_live():
    serial = request.args.get("serial")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }

    def generator():
        # Basic stream meta
        yield _sse_event("meta", {"serial": serial or "unknown"})

        # Device info snapshot (sent once)
        try:
            info = get_device_info(serial) or {}
            yield _sse_event("device", {
                "serial": serial,
                "model": info.get("model"),
                "android_version": info.get("android_version"),
                "battery": info.get("battery"),
                "network": info.get("network"),
            })
        except Exception:
            current_app.logger.exception("device meta failed")

        fresh = request.args.get('fresh', '0') == '1'
        try:
            for item in stream_logcat(serial, fresh=fresh):
                if not isinstance(item, dict):
                    continue

                enriched = enrich_live_entry(item)
                yield _sse_event("log", enriched)

        except GeneratorExit:
            return
        except Exception:
            current_app.logger.exception("android_stream_live error")
            yield _sse_event("log", {"message": "stream error"})

    return Response(stream_with_context(generator()), headers=headers)


# -------------------------------------------------------------------------
# Android disconnect
# -------------------------------------------------------------------------
@routes.route("/android/disconnect", methods=["POST"])
def android_disconnect():
    import subprocess
    from app.log_android.adb_device import adb_path
    serial = request.args.get("serial")
    if serial:
        try:
            adb = adb_path()
            if adb:
                subprocess.run([adb, "disconnect", serial], timeout=3, capture_output=True)
        except Exception:
            pass
    return jsonify({"ok": True})


# -------------------------------------------------------------------------
# Health
# -------------------------------------------------------------------------
@routes.route("/health")
def health():
    return jsonify({"ok": True})


# -------------------------------------------------------------------------
# Export
# -------------------------------------------------------------------------
@routes.route("/export", methods=["POST"])
def export_data():
    sid = request.cookies.get("logsense_sid")
    entries = load(sid) if sid else None
    if not entries:
        return jsonify({"ok": False, "error": "No session data found"}), 404

    body = request.get_json(silent=True) or {}
    fmt = body.get("format", "json")
    severity_filter = (body.get("filter") or {}).get("severity")

    if severity_filter:
        entries = [e for e in entries if e.get("severity") == severity_filter]

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if fmt == "txt":
        lines = []
        for e in entries:
            lines.append(
                f"[{e.get('severity', '')}] [{e.get('section', '')}] "
                f"| {e.get('entry', '')} | {e.get('explanation', '')}"
            )
        buf = io.BytesIO("\n".join(lines).encode("utf-8"))
        return send_file(
            buf,
            mimetype="text/plain",
            as_attachment=True,
            download_name=f"logsense_{stamp}.txt",
        )

    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["severity", "section", "entry", "explanation", "threat", "confidence"])
        for e in entries:
            writer.writerow([
                e.get("severity", ""),
                e.get("section", ""),
                e.get("entry", ""),
                e.get("explanation", ""),
                e.get("threat", ""),
                e.get("confidence", ""),
            ])
        out = io.BytesIO(buf.getvalue().encode("utf-8"))
        return send_file(
            out,
            mimetype="text/csv",
            as_attachment=True,
            download_name=f"logsense_{stamp}.csv",
        )

    # default: json
    buf = io.BytesIO(json.dumps(entries, ensure_ascii=False, indent=2).encode("utf-8"))
    return send_file(
        buf,
        mimetype="application/json",
        as_attachment=True,
        download_name=f"logsense_{stamp}.json",
    )


# -------------------------------------------------------------------------
# Error handling
# -------------------------------------------------------------------------
@routes.errorhandler(Exception)
def route_global_error(err):
    current_app.logger.exception("Route error")
    return jsonify({"ok": False, "error": str(err)}), 500
