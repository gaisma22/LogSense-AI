#!/usr/bin/env python3
"""
Dummy SSE stream generator for testing the Android terminal UI
without ADB or any connected device.
Run:
    python3 test_sse.py
Then open:
    http://localhost:9001/stream
"""

import json
import time
from flask import Flask, Response

app = Flask(__name__)

def fake_log_events():
    levels = [
        ("INFO", "General system message"),
        ("DEBUG", "Debug details here"),
        ("WARN", "Possible issue detected"),
        ("ERROR", "Something failed"),
    ]
    counter = 0

    while True:
        level, msg = levels[counter % len(levels)]
        payload = {
            "timestamp": time.strftime("%H:%M:%S"),
            "tag": "TestModule",
            "level": level,
            "message": f"{msg} #{counter}",
        }
        yield f"data: {json.dumps(payload)}\n\n"
        counter += 1
        time.sleep(1)


@app.route("/stream")
def stream():
    return Response(fake_log_events(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(port=9001, debug=True)
