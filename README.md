# MECE4613 Final Lab Project

Industrial Automation final lab project for a Raspberry Pi mobile robot with a web HMI, live camera streaming, QR-code detection, and an autonomous Part B routine.

## What This Project Does

The system combines three robot capabilities:

- A browser-based HMI for manual wheel control: forward, backward, left, right, spin left, spin right, and stop.
- A live camera stream served over HTTP so the operator can see the robot view remotely.
- QR-code detection with OpenCV. In Part B, the robot scans for a configured UNI QR code, stops when it sees a match, blinks an LED for 3 seconds, resumes travel, and then returns to its starting station.

## Architecture

```text
.
├── assets/
│   └── qr/                 # Sample and student QR codes
├── docs/                   # Lab handout, setup guide, and Part C response
├── robot/                  # Reusable robot application package
│   ├── camera.py           # Pi camera capture to robot_stream.jpg
│   ├── file_watcher.py     # mtime-based frame watcher
│   ├── motor.py            # Adafruit Crickit motor helpers
│   ├── part_b.py           # Autonomous QR detection routine
│   ├── qr.py               # OpenCV QR decoding and annotation
│   ├── templates/hmi.html  # Tornado HMI template
│   └── web_app.py          # Combined HMI, stream, events, and Part B server
└── scripts/                # Runnable command-line entrypoints
    ├── camera_capture.py   # Start camera frame capture
    ├── camera_stream.py    # Preview shared camera frames locally
    ├── camera_web.py       # Standalone camera + QR web viewer
    ├── hmi_server.py       # Start the combined robot HMI
    ├── hmi_stream.py       # Serve shared camera frames as MJPEG
    └── qr_stream.py        # Scan shared camera frames for QR codes
```

## Hardware

- Raspberry Pi 4 Model B
- Raspberry Pi Camera Module
- Adafruit Crickit HAT
- Two DC motors in a differential-drive chassis
- Onboard Crickit RGB LED or compatible indicator output

## Software

The robot code targets Raspberry Pi OS with Python 3 and these libraries:

```bash
pip install opencv-python tornado adafruit-circuitpython-crickit qrcode
```

The camera scripts use `picamera2`, which is usually installed through Raspberry Pi OS packages.

## Running The Robot

Run commands from the repository root on the Raspberry Pi.

Start the combined HMI, live stream, QR detection events, and Part B controls:

```bash
python3 scripts/hmi_server.py
```

Then open:

```text
http://<robot-ip>:8888
```

Run only the autonomous Part B routine:

```bash
python3 -m robot.part_b
```

Override the target QR code with an environment variable:

```bash
MY_UNI=xx1234 python3 scripts/hmi_server.py
MY_UNI=xx1234 python3 -m robot.part_b
```

Optional standalone tools:

```bash
python3 scripts/camera_capture.py
python3 scripts/camera_stream.py
python3 scripts/hmi_stream.py
python3 scripts/qr_stream.py
python3 scripts/camera_web.py
```

## HMI Endpoints

The combined Tornado app in `robot/web_app.py` exposes:

- `/` for the browser HMI
- `/stream` for the MJPEG camera feed
- `/events` for QR and Part B status events
- `/motor/<command>` for manual motor commands
- `/partb/start` to start the autonomous QR routine
- `/partb/stop` to abort the autonomous QR routine

## QR Codes

QR image assets live in `assets/qr/`. Generate a new UNI QR code with:

```bash
pip install qrcode
qr <your-UNI> > assets/qr/<your-UNI>.png
```

## Portfolio Summary

**QR-Guided Mobile Robot with Web-Based HMI Control**

Developed a Raspberry Pi mobile robot system that combines real-time QR code scanning with a browser-based human-machine interface. The robot uses OpenCV to detect QR codes from a live camera stream and a Tornado-powered UI to remotely control wheel movement, including forward, backward, left, right, spin, and stop commands. Motor control was implemented through an Adafruit Crickit driver, enabling responsive directional movement for industrial automation-style navigation and object identification tasks.
