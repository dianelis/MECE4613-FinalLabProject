#!/usr/bin/env python3

"""
Live camera stream with QR code detection served over HTTP.

Endpoints:
    /           — UI with live feed + QR detection log
    /stream     — raw MJPEG stream
    /events     — Server-Sent Events for QR detections
"""

from picamera2 import Picamera2
from qr_code import decode_qrcode
import tornado.web
import tornado.ioloop
import asyncio
import threading
import cv2
import time
import os
import json

# ── Configuration ────────────────────────────────────────────────────
PORT = 9000
WIDTH, HEIGHT = 640, 480
MY_UNI = os.environ.get('MY_UNI', 'di2256')
BOUNDARY = b'--frameboundary\r\n'
JPEG_HEADER = b'Content-Type: image/jpeg\r\n\r\n'

# ── Shared state ─────────────────────────────────────────────────────
_lock = threading.Lock()
_latest_jpeg = None
_events = []          # list of SSE listener queues


def camera_loop():
    """Runs in a background thread: capture → detect → encode JPEG."""
    global _latest_jpeg

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    print(f'Camera started ({WIDTH}x{HEIGHT})', flush=True)

    last_detection = 0.0
    cooldown = 2.0

    while True:
        frame = picam2.capture_array()
        frame = cv2.flip(frame, -1)

        data = decode_qrcode(frame)
        now = time.time()

        if data and (now - last_detection) > cooldown:
            last_detection = now
            is_mine = (data == MY_UNI)
            event = {
                "data": data,
                "mine": is_mine,
                "time": time.strftime("%H:%M:%S"),
            }
            print(f'QR detected: "{data}" {"(MATCH)" if is_mine else "(skip)"}', flush=True)
            with _lock:
                for q in _events:
                    q.append(event)

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with _lock:
            _latest_jpeg = buf.tobytes()

        time.sleep(0.03)


# ── Handlers ─────────────────────────────────────────────────────────
class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.set_header('Content-Type', 'text/html')
        self.write(HTML)


class StreamHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary=frameboundary')
        self.set_header('Cache-Control', 'no-cache')
        while True:
            with _lock:
                jpeg = _latest_jpeg
            if jpeg:
                self.write(BOUNDARY + JPEG_HEADER + jpeg + b'\r\n')
                try:
                    await self.flush()
                except Exception:
                    break
            await asyncio.sleep(0.05)


class EventHandler(tornado.web.RequestHandler):
    async def get(self):
        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')
        q = []
        with _lock:
            _events.append(q)
        try:
            while True:
                while q:
                    event = q.pop(0)
                    self.write(f'data: {json.dumps(event)}\n\n')
                    await self.flush()
                await asyncio.sleep(0.2)
        except Exception:
            pass
        finally:
            with _lock:
                if q in _events:
                    _events.remove(q)


# ── HTML ─────────────────────────────────────────────────────────────
HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Robot Camera &amp; QR Scanner</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0f1117;
    color: #e4e4e7;
    min-height: 100vh;
  }}
  header {{
    background: #16181f;
    border-bottom: 1px solid #2a2d37;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  header h1 {{
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.02em;
  }}
  header .status {{
    font-size: 0.8rem;
    color: #71717a;
  }}
  header .status .dot {{
    display: inline-block;
    width: 8px; height: 8px;
    background: #22c55e;
    border-radius: 50%;
    margin-right: 5px;
    animation: pulse 2s infinite;
  }}
  @keyframes pulse {{
    0%, 100% {{ opacity: 1; }}
    50% {{ opacity: 0.4; }}
  }}
  .container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 20px;
  }}
  .feed-wrapper {{
    position: relative;
    background: #000;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(0,0,0,0.5);
  }}
  .feed-wrapper img {{
    display: block;
    width: 100%;
    height: auto;
  }}
  .feed-label {{
    position: absolute;
    top: 10px; left: 12px;
    background: rgba(0,0,0,0.6);
    backdrop-filter: blur(4px);
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.75rem;
    color: #a1a1aa;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }}
  #toast {{
    position: absolute;
    bottom: 16px;
    left: 50%;
    transform: translateX(-50%) translateY(80px);
    padding: 12px 28px;
    border-radius: 10px;
    font-size: 1rem;
    font-weight: 600;
    opacity: 0;
    transition: transform 0.4s ease, opacity 0.4s ease;
    pointer-events: none;
    white-space: nowrap;
    z-index: 10;
  }}
  #toast.show {{
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }}
  #toast.match {{
    background: rgba(34, 197, 94, 0.9);
    color: #fff;
    box-shadow: 0 0 30px rgba(34,197,94,0.4);
  }}
  #toast.skip {{
    background: rgba(234, 179, 8, 0.85);
    color: #1a1a1a;
  }}
  h2 {{
    font-size: 0.9rem;
    font-weight: 600;
    color: #a1a1aa;
    margin: 24px 0 10px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }}
  #log {{
    background: #16181f;
    border: 1px solid #2a2d37;
    border-radius: 10px;
    padding: 6px;
    max-height: 240px;
    overflow-y: auto;
  }}
  #log:empty::after {{
    content: "No QR codes detected yet — hold one in front of the camera";
    display: block;
    padding: 20px;
    text-align: center;
    color: #52525b;
    font-size: 0.85rem;
  }}
  .log-entry {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 0.85rem;
    animation: slideIn 0.3s ease;
  }}
  .log-entry + .log-entry {{
    margin-top: 2px;
  }}
  .log-entry.match {{
    background: rgba(34,197,94,0.1);
    border-left: 3px solid #22c55e;
  }}
  .log-entry.skip {{
    background: rgba(234,179,8,0.07);
    border-left: 3px solid #eab308;
  }}
  .log-entry .badge {{
    font-size: 0.7rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    flex-shrink: 0;
  }}
  .match .badge {{ background: #22c55e; color: #fff; }}
  .skip .badge {{ background: #eab308; color: #1a1a1a; }}
  .log-entry .code {{ font-family: monospace; font-weight: 600; }}
  .log-entry .ts {{ color: #52525b; margin-left: auto; font-size: 0.75rem; }}
  @keyframes slideIn {{
    from {{ opacity: 0; transform: translateY(-8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
  }}
  .info {{
    margin-top: 16px;
    font-size: 0.78rem;
    color: #52525b;
    text-align: center;
  }}
</style>
</head>
<body>
<header>
  <h1>Robot Camera &amp; QR Scanner</h1>
  <div class="status"><span class="dot"></span>Looking for <strong>{MY_UNI}</strong></div>
</header>
<div class="container">
  <div class="feed-wrapper">
    <span class="feed-label">Live Feed</span>
    <img id="feed" src="/stream" alt="Camera feed">
    <div id="toast"></div>
  </div>
  <h2>Detection Log</h2>
  <div id="log"></div>
  <p class="info">Camera running at {WIDTH}&times;{HEIGHT} &mdash; scanning every frame for QR codes</p>
</div>
<script>
const log = document.getElementById('log');
const toast = document.getElementById('toast');
let toastTimer;
const evtSource = new EventSource('/events');
evtSource.onmessage = function(e) {{
  const d = JSON.parse(e.data);
  const cls = d.mine ? 'match' : 'skip';
  const label = d.mine ? 'Match' : 'Skip';
  // toast
  toast.className = 'show ' + cls;
  toast.textContent = d.mine
    ? '\\u2705  Detected ' + d.data + '!'
    : '\\u26A0  Saw ' + d.data + ' (not mine)';
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.className = '', 3500);
  // log entry
  const entry = document.createElement('div');
  entry.className = 'log-entry ' + cls;
  entry.innerHTML =
    '<span class="badge">' + label + '</span>' +
    '<span class="code">' + d.data + '</span>' +
    '<span class="ts">' + d.time + '</span>';
  log.prepend(entry);
  while (log.children.length > 50) log.removeChild(log.lastChild);
}};
</script>
</body>
</html>
"""


# ── Main ─────────────────────────────────────────────────────────────
if __name__ == '__main__':
    t = threading.Thread(target=camera_loop, daemon=True)
    t.start()

    app = tornado.web.Application([
        (r'/', IndexHandler),
        (r'/stream', StreamHandler),
        (r'/events', EventHandler),
    ])
    app.listen(PORT)
    print(f'Server running at http://0.0.0.0:{PORT}', flush=True)
    tornado.ioloop.IOLoop.current().start()
