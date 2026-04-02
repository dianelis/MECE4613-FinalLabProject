# MECE4613 — Final Lab Project

**Industrial Automation · Columbia University — Department of Mechanical Engineering**

---

## Overview

This is the final lab project for **MECE4613 Industrial Automation**. It covers building a Human-Machine Interface (HMI) to remotely control a mobile robot, implementing dynamic QR-code-based object detection, and answering design questions that bridge Industrial Automation and AI concepts.

The project is built on a **Raspberry Pi 4B** running Debian Bullseye (64-bit) and uses Python with OpenCV, Tornado, and the Adafruit Crickit motor driver.

---

## Project Structure

| File | Description |
|---|---|
| `hmi-sol.py` | Tornado web server that handles HMI requests and drives the motors |
| `hmi.html` | Browser-based HMI with directional control buttons |
| `motor.py` | Motor control library (forward, backward, left, right, spin) using Adafruit Crickit |
| `camera.py` | Camera initialization, real-time frame saving, and snapshot capture |
| `camera_stream.py` | Watches the latest camera frame and displays it locally via OpenCV |
| `hmi_stream.py` | Tornado-based MJPEG streaming server for the robot's camera feed |
| `file_watcher.py` | Utility class that detects file-modification events via `mtime` polling |
| `qr_code.py` | QR code detection and decoding using OpenCV's `QRCodeDetector` |
| `part_b.py` | **Part B solution** — integrated travel + QR detection + LED blink + return |
| `qr_stream.py` | Real-time QR code scanning on the camera stream |
| `am3469.png` | Sample personal QR code (UNI-based) |
| `Guide-Rev0.pdf` | Setup guide for the robot OS, camera, QR codes, and HMI streaming |
| `finalLabProject.pdf` | Full project specification |

---

## Parts

### Part A — Building an Industrial Automation HMI (5 pts)

Build and complete an HMI that controls the robot from a local computer, tablet, or smartphone.

- **`hmi-sol.py`** runs a [Tornado](https://www.tornadoweb.org/) web server on the robot's Raspberry Pi, listening on a configurable port (default `8888`).
- **`hmi.html`** renders directional control buttons (▲ ▼ ◀ ▶, spin left/right, and stop).
- When a button is pressed, the HTML form POSTs the movement command name to the server, which calls the corresponding function from `motor.py` via `getattr()`.

**To run:**
```bash
# On the Raspberry Pi (robot)
python3 hmi-sol.py
```
Then open `http://<robot-ip>:8888` in any browser on the same network.

---

### Part B — Dynamic Object Detection (40 pts)

Each robot detects a **unique QR code** (the student's university ID), stops for **3 seconds** with a blinking LED, and then returns to its starting station.

**Key concepts:**
- Sensor-based detection and programmed responses
- Timing control and autonomous decision-making
- Simulates real-world automation tasks (inventory management, quality control, sorting)

**QR code setup:**
```bash
pip install qrcode
qr <your-UNI> > <your-UNI>.png   # e.g., qr am3469 > am3469.png
```

**Relevant scripts:**
- `qr_code.py` — detects and decodes QR codes in a single image
- `qr_stream.py` — continuously scans the live camera stream for QR codes
- `camera.py` — captures and saves real-time frames to a shared path
- `file_watcher.py` — monitors the shared frame file for changes

---

### Part C — Questions (25 pts)

A set of open-ended design questions covering:

1. HMI round-trip information exchange (controllable parameters, required readings, emergency stops, security)
2. Belt conveyor + robot QR scanning and product-pushing system design
3. Hardware/control algorithms for rapid (<10 ms) pushing actions
4. Dual parallel conveyor autonomy and multi-request scheduling
5. Communication architecture for a nuclear-hazard field with XOR-redundant HMIs
6. QR-code-driven box handling system (hardware, software, control)
7. Urgent/critical product handling and escalation
8. SCADA monitoring, HMI design, and holistic AI integration across software layers

---

## Hardware & Software Requirements

### Hardware
- Raspberry Pi 4 Model B
- Raspberry Pi Camera Module
- Adafruit Crickit HAT (DC motor driver)
- Two DC motors (differential drive)
- LED (for blinking indicator)

### Software
- **OS:** Raspberry Pi OS Legacy 64-bit (Debian Bullseye)
- **Python 3** with the following packages:
  - `opencv-python` (cv2) — camera capture, image processing, QR detection
  - `tornado` — asynchronous web framework for HMI and streaming
  - `adafruit-circuitpython-crickit` — motor control via the Crickit HAT
  - `qrcode` — QR code generation

### Installation
```bash
pip install opencv-python tornado adafruit-circuitpython-crickit qrcode
```

---

## How It Works

### Motor Control (`motor.py`)
The robot uses a differential-drive system with two DC motors controlled through the Adafruit Crickit. Movement functions (`forward`, `backward`, `left`, `right`, `spin_left`, `spin_right`) are created as `functools.partial` wrappers around a base `move()` function that sets throttle values for a specified duration.

### Camera System (`camera.py`)
The camera captures frames at 640×480 @ 30 FPS. Frames are saved atomically using a write-then-rename pattern (`robot_stream_tmp.jpg` → `robot_stream.jpg`) to avoid tearing when read by other processes.

### Real-Time Streaming (`hmi_stream.py`)
An MJPEG streaming server built with Tornado serves the camera feed over HTTP using `multipart/x-mixed-replace` boundaries. Remote clients can view the live feed by navigating to `http://<robot-ip>:9000`.

### QR Code Detection (`qr_code.py`, `qr_stream.py`)
Uses OpenCV's built-in `QRCodeDetector` to decode QR codes in each frame. When a matching UNI code is found, the robot performs a stop-and-blink action.

### File Watcher (`file_watcher.py`)
A lightweight polling utility that checks file modification times (`mtime`) to detect when the camera has written a new frame, enabling decoupled producer-consumer communication between the camera process and display/detection processes.

---

## Usage

```bash
# 1. Start the camera (on the robot)
python3 camera.py

# 2. Start the HMI server (on the robot)
python3 hmi-sol.py

# 3. (Optional) Start the MJPEG stream server (on the robot)
python3 hmi_stream.py

# 4. (Optional) Start QR detection on the live stream (on the robot)
python3 qr_stream.py

# 5. (Optional) View the camera stream locally
python3 camera_stream.py
```

Access the HMI from any browser at `http://<robot-ip>:8888` and the camera stream at `http://<robot-ip>:9000`.

---

## References

- [Tornado Web Framework](https://www.tornadoweb.org/)
- [OpenCV Python Documentation](https://docs.opencv.org/)
- [Adafruit Crickit HAT Guide](https://learn.adafruit.com/adafruit-crickit-hat-for-raspberry-pi-linux-computers)
- Course lectures on event systems, SCADA, and HMI design
