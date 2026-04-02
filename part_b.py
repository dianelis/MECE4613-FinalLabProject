#!/usr/bin/env python3

"""
Part B – Dynamic Object Detection (40 pts)
MECE4613 Final Lab Project — Industrial Automation

The robot travels along a straight line while continuously scanning for
QR codes with its camera. When it detects YOUR unique QR code (your UNI):
    1. Stops immediately
    2. Blinks an LED for 3 seconds
    3. Resumes forward travel

If multiple copies of your QR code exist along the path, the robot stops
at every one of them. QR codes belonging to other students are ignored.

After reaching the end of the run, the robot returns to its starting
station by reversing for the same distance it traveled forward.

Usage (on the Raspberry Pi):
    $ python3 part_b.py

    You can override your UNI at runtime:
    $ MY_UNI=xx1234 python3 part_b.py
"""


# ─── Imports ──────────────────────────────────────────────────────────
from adafruit_crickit import crickit as ck
from qr_code import decode_qrcode
import motor
import cv2
import time
import os


# ─── Configuration ────────────────────────────────────────────────────
# Your University ID — the QR code data the robot should react to.
# Override via environment variable: MY_UNI=xx1234 python3 part_b.py
MY_UNI = os.environ.get('MY_UNI', 'di2256')

# Travel
TRAVEL_DURATION  = 15       # max forward travel time (seconds)
MOVE_SPEED       = 2        # motor speed level (1–4, see motor.THROTTLE_SPEED)
SCAN_INTERVAL    = 0.05     # time between camera frames during travel (seconds)

# Detection response
BLINK_DURATION   = 3.0      # how long to blink the LED on detection (seconds)
BLINK_INTERVAL   = 0.25     # LED on/off toggle rate (seconds)
COOLDOWN         = 2.0      # ignore the same code for this long after a detection (seconds)

# Camera
WIDTH, HEIGHT, FPS = 640, 480, 30

# LED — connected to Crickit Drive pin 1 (PWM-capable)
led = ck.drive_1


# ─── Camera ───────────────────────────────────────────────────────────
def init_camera():
    """Open and configure the Pi camera."""
    cap = cv2.VideoCapture(0)
    assert cap.isOpened(), 'Error: could not open camera.'
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          FPS)
    return cap


def grab_frame(cap):
    """Capture one frame, flip it (camera is mounted upside-down), return it."""
    ret, frame = cap.read()
    if not ret:
        return None
    return cv2.flip(frame, -1)


# ─── LED ──────────────────────────────────────────────────────────────
def led_on():
    led.fraction = 1.0

def led_off():
    led.fraction = 0.0


def blink_led(duration=BLINK_DURATION, interval=BLINK_INTERVAL):
    """Blink the LED on/off for *duration* seconds."""
    end = time.time() + duration
    state = True
    while time.time() < end:
        led.fraction = 1.0 if state else 0.0
        state = not state
        time.sleep(interval)
    led_off()


# ─── Motor helpers ────────────────────────────────────────────────────
def drive_forward():
    """Start both motors forward (non-blocking — motors keep running)."""
    motor.set_throttle('R', MOVE_SPEED,  1)
    motor.set_throttle('L', MOVE_SPEED,  1)


def drive_backward():
    """Start both motors backward (non-blocking)."""
    motor.set_throttle('R', MOVE_SPEED, -1)
    motor.set_throttle('L', MOVE_SPEED, -1)


def stop():
    """Cut power to both motors."""
    motor.set_throttle('R', 0)
    motor.set_throttle('L', 0)


# ─── Main routine ────────────────────────────────────────────────────
def main():
    print('=' * 50)
    print(f'  Part B — Dynamic Object Detection')
    print(f'  Looking for QR code: "{MY_UNI}"')
    print(f'  Travel duration:     {TRAVEL_DURATION}s')
    print('=' * 50)

    cap = init_camera()
    detections     = 0      # how many times we found our code
    forward_time   = 0.0    # total time spent actually moving forward
    last_detection = 0.0    # timestamp of the last detection (for cooldown)

    # ── Phase 1: Travel forward while scanning ──────────────────────
    print('\n[Phase 1] Moving forward — scanning for QR codes...')
    run_start = time.time()

    drive_forward()

    while True:
        elapsed = time.time() - run_start
        if elapsed >= TRAVEL_DURATION:
            break

        # Grab a frame and try to decode any QR code in it
        frame = grab_frame(cap)
        if frame is not None:
            data = decode_qrcode(frame)

            if data == MY_UNI and (time.time() - last_detection) > COOLDOWN:
                # ── Match found ──
                detections += 1
                stop()
                print(f'\n  *** DETECTED "{MY_UNI}" *** (#{detections})')
                print(f'      Blinking LED for {BLINK_DURATION}s ...')
                blink_led()
                last_detection = time.time()

                # Resume forward travel
                print('      Resuming...')
                drive_forward()

            elif data and data != MY_UNI:
                # Someone else's code — log and skip
                print(f'  [skip] saw "{data}" — not mine', end='\r', flush=True)

        time.sleep(SCAN_INTERVAL)
        forward_time += SCAN_INTERVAL

    stop()
    print(f'\n[Phase 1 done] Detected {detections} code(s) in {elapsed:.1f}s')

    # ── Phase 2: Return to starting station ─────────────────────────
    print(f'\n[Phase 2] Returning to start ({forward_time:.1f}s backward)...')
    drive_backward()
    time.sleep(forward_time)
    stop()

    # ── Cleanup ─────────────────────────────────────────────────────
    cap.release()
    led_off()

    print('\n' + '=' * 50)
    print(f'  Part B complete — {detections} detection(s)')
    print('=' * 50)


if __name__ == '__main__':
    main()
