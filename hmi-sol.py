#!/usr/bin/env python3

"""
Combined HMI + Part B server.

Single Tornado app serving:
    /               — UI (camera feed, manual controls, Part B panel, detection log)
    /stream         — MJPEG camera stream
    /events         — Server-Sent Events (QR detections + Part B status)
    /<motor_cmd>    — POST motor commands (forward, backward, left, right, …)
    /partb/start    — POST start the autonomous Part B sequence
    /partb/stop     — POST abort Part B
"""

from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application
from tornado.log import enable_pretty_logging
from picamera2 import Picamera2
from adafruit_crickit import crickit as ck
from qr_code import decode_qrcode
from datetime import datetime
import tornado.web
import asyncio
import threading
import json
import motor
import cv2
import time
import os

# ── Configuration ────────────────────────────────────────────────────
PORT = 8888
WIDTH, HEIGHT = 640, 480
MY_UNI = os.environ.get('MY_UNI', 'di2256')
DEBUG = bool(os.environ.get('ROBOT_DEBUG'))

TRAVEL_DURATION = 15
MOVE_SPEED = 2
SCAN_INTERVAL = 0.05
BLINK_DURATION = 3.0
BLINK_INTERVAL = 0.25
COOLDOWN = 2.0

# ── Shared state ─────────────────────────────────────────────────────
_lock = threading.Lock()
_latest_jpeg = None
_sse_queues = []

_partb_thread = None
_partb_running = False
_partb_status = "idle"

led = ck.drive_1


def push_event(event_type, data):
    """Push an SSE event to all connected clients."""
    event = {"type": event_type, **data}
    with _lock:
        for q in _sse_queues:
            q.append(event)


# ── Camera thread ────────────────────────────────────────────────────
_picam2 = None

def camera_loop():
    global _latest_jpeg, _picam2

    _picam2 = Picamera2()
    config = _picam2.create_preview_configuration(
        main={"size": (WIDTH, HEIGHT), "format": "RGB888"}
    )
    _picam2.configure(config)
    _picam2.start()
    print(f'Camera started ({WIDTH}x{HEIGHT})', flush=True)

    last_detection = 0.0

    while True:
        frame = _picam2.capture_array()
        frame = cv2.flip(frame, -1)

        data = decode_qrcode(frame)
        now = time.time()

        if data and (now - last_detection) > COOLDOWN:
            last_detection = now
            is_mine = (data == MY_UNI)
            push_event("qr", {
                "data": data,
                "mine": is_mine,
                "time": time.strftime("%H:%M:%S"),
            })

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        with _lock:
            _latest_jpeg = buf.tobytes()

        time.sleep(0.03)


# ── Part B logic ─────────────────────────────────────────────────────
def partb_drive_forward():
    motor.set_throttle('R', MOVE_SPEED, 1)
    motor.set_throttle('L', MOVE_SPEED, -1)

def partb_drive_backward():
    motor.set_throttle('R', MOVE_SPEED, -1)
    motor.set_throttle('L', MOVE_SPEED, 1)

def partb_stop_motors():
    motor.set_throttle('R', 0)
    motor.set_throttle('L', 0)

def blink_led():
    end = time.time() + BLINK_DURATION
    state = True
    while time.time() < end:
        led.fraction = 1.0 if state else 0.0
        state = not state
        time.sleep(BLINK_INTERVAL)
    led.fraction = 0.0

def partb_worker():
    global _partb_running, _partb_status

    detections = 0
    forward_time = 0.0
    last_det = 0.0

    # Phase 1: forward + scan
    _partb_status = "phase1"
    push_event("partb", {"status": "phase1", "msg": "Spinning — scanning for QR codes…"})
    run_start = time.time()
    partb_drive_forward()

    while _partb_running:
        elapsed = time.time() - run_start
        if elapsed >= TRAVEL_DURATION:
            break

        if _picam2:
            frame = _picam2.capture_array()
            frame = cv2.flip(frame, -1)
            data = decode_qrcode(frame)

            if data == MY_UNI and (time.time() - last_det) > COOLDOWN:
                detections += 1
                partb_stop_motors()
                _partb_status = "detected"
                push_event("partb", {
                    "status": "detected",
                    "msg": f'Detected "{MY_UNI}" (#{detections}) — blinking LED…',
                    "detections": detections,
                })
                push_event("qr", {
                    "data": data, "mine": True,
                    "time": time.strftime("%H:%M:%S"),
                })
                blink_led()
                last_det = time.time()
                if _partb_running:
                    _partb_status = "phase1"
                    push_event("partb", {"status": "phase1", "msg": "Resuming spin…"})
                    partb_drive_forward()

            elif data and data != MY_UNI:
                push_event("qr", {
                    "data": data, "mine": False,
                    "time": time.strftime("%H:%M:%S"),
                })

        time.sleep(SCAN_INTERVAL)
        forward_time += SCAN_INTERVAL

    partb_stop_motors()

    if not _partb_running:
        _partb_status = "idle"
        push_event("partb", {"status": "aborted", "msg": "Part B aborted.", "detections": detections})
        led.fraction = 0.0
        return

    # Phase 2: return
    _partb_status = "phase2"
    push_event("partb", {"status": "phase2", "msg": f"Spinning back ({forward_time:.1f}s reverse)…"})
    partb_drive_backward()
    t0 = time.time()
    while _partb_running and (time.time() - t0) < forward_time:
        time.sleep(0.05)
    partb_stop_motors()

    # Done
    _partb_status = "idle"
    _partb_running = False
    led.fraction = 0.0
    push_event("partb", {"status": "done", "msg": f"Part B complete — {detections} detection(s).", "detections": detections})


# ── Handlers ─────────────────────────────────────────────────────────
class IndexHandler(RequestHandler):
    def get(self, name=''):
        stamp = datetime.now().isoformat()
        self.render('hmi.html', stamp=stamp, my_uni=MY_UNI,
                    TRAVEL_DURATION=TRAVEL_DURATION)


class MotorHandler(RequestHandler):
    def post(self, name):
        if _partb_running:
            self.set_status(409)
            self.write('Part B is running')
            return
        func = getattr(motor, name, None)
        if func:
            func()
        self.redirect('/')


class StreamHandler(RequestHandler):
    async def get(self):
        self.set_header('Content-Type', 'multipart/x-mixed-replace;boundary=frameboundary')
        self.set_header('Cache-Control', 'no-cache')
        boundary = b'--frameboundary\r\n'
        jpeg_hdr = b'Content-Type: image/jpeg\r\n\r\n'
        while True:
            with _lock:
                jpeg = _latest_jpeg
            if jpeg:
                self.write(boundary + jpeg_hdr + jpeg + b'\r\n')
                try:
                    await self.flush()
                except Exception:
                    break
            await asyncio.sleep(0.05)


class EventHandler(RequestHandler):
    async def get(self):
        self.set_header('Content-Type', 'text/event-stream')
        self.set_header('Cache-Control', 'no-cache')
        self.set_header('Connection', 'keep-alive')
        q = []
        with _lock:
            _sse_queues.append(q)
        try:
            while True:
                while q:
                    ev = q.pop(0)
                    self.write(f'data: {json.dumps(ev)}\n\n')
                    await self.flush()
                await asyncio.sleep(0.2)
        except Exception:
            pass
        finally:
            with _lock:
                if q in _sse_queues:
                    _sse_queues.remove(q)


class PartBStartHandler(RequestHandler):
    def post(self):
        global _partb_thread, _partb_running
        if _partb_running:
            self.set_status(409)
            self.write('Already running')
            return
        _partb_running = True
        _partb_thread = threading.Thread(target=partb_worker, daemon=True)
        _partb_thread.start()
        self.write('started')


class PartBStopHandler(RequestHandler):
    def post(self):
        global _partb_running
        _partb_running = False
        partb_stop_motors()
        led.fraction = 0.0
        self.write('stopped')


# ── Main ─────────────────────────────────────────────────────────────
enable_pretty_logging()

cam_thread = threading.Thread(target=camera_loop, daemon=True)
cam_thread.start()

settings = dict(debug=DEBUG)
app = Application([
    (r'/stream', StreamHandler),
    (r'/events', EventHandler),
    (r'/partb/start', PartBStartHandler),
    (r'/partb/stop', PartBStopHandler),
    (r'/motor/([a-z_]+)', MotorHandler),
    (r'/([a-z_]*)', IndexHandler),
], **settings)

app.listen(PORT)
print(f'HMI server running at http://0.0.0.0:{PORT}', flush=True)
IOLoop.current().start()
