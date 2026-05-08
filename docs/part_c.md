# Part C — Questions (25 pts)

**MECE4613 Final Lab Project — Industrial Automation**
**Columbia University · Department of Mechanical Engineering**

---

## Question 1

*HMI is a round-trip information exchange.*

### a) Complete machine parameters controllable via our HMI

| Category | Parameters |
|---|---|
| **Motion control** | Forward / backward speed (throttle level 1–4), turn direction (left / right), spin direction, movement duration |
| **Motor tuning** | Sync coefficients (`SyncForwardR`, `SyncBackwardR`), individual left/right motor throttle override |
| **Navigation mode** | Manual (button-by-button), semi-autonomous (waypoint following), fully autonomous (QR-seek mode) |
| **Camera** | Resolution (width × height), frame rate (FPS), brightness, contrast, saturation, flip orientation |
| **Detection** | Target QR code (UNI string), detection sensitivity threshold, cooldown interval between successive detections |
| **LED / actuator** | LED on/off, blink rate, blink duration |
| **System** | Emergency stop (E-Stop), mode selection (idle / run / calibration), debug logging on/off |

### b) Required readings the user should observe during operation

| Reading | Source | Why |
|---|---|---|
| **Live camera feed** | MJPEG stream via `hmi_stream.py` | Visual confirmation of the robot's surroundings |
| **Motor status** | Throttle values for L and R motors | Verify intended motion is being executed |
| **Current speed & direction** | Computed from throttle + factor | Situational awareness |
| **QR detection events** | Decoded data string + timestamp | Confirms correct target identification |
| **Battery / power level** | Crickit HAT voltage reading | Prevents unexpected shutdowns in the field |
| **System health** | CPU temperature, uptime, error log | Ensures the Raspberry Pi is operating within safe limits |
| **Connection latency** | Round-trip time between HMI and robot | Alerts the operator if commands may be delayed |
| **Operation log** | Timestamped event history | Traceability and audit trail |

### c) Emergency stop scenarios and how the user should respond

| Scenario | Response |
|---|---|
| **Obstacle collision** | Immediate E-Stop via HMI button → cut all motor throttle to 0 → assess damage before resuming |
| **Loss of communication** | Robot firmware should implement a *watchdog timer*; if no heartbeat from HMI within a timeout (e.g., 2s), the robot autonomously halts all actuators |
| **Unintended motion** | Operator presses E-Stop → motors stop → operator verifies sync coefficients and recalibrates before restarting |
| **Overheating** | System monitors CPU/motor temperature → triggers automatic shutdown → HMI displays thermal warning → operator waits for cooldown |
| **Camera failure** | Robot cannot detect QR codes → enters safe-stop mode → HMI alerts operator → manual retrieval |

In all cases the HMI should provide a **single, always-visible E-Stop button** that sends a priority interrupt to the robot, overriding any running automation sequence.

### d) Security considerations

| Consideration | Self-addressed or HMI-visible? |
|---|---|
| **Authentication** | Self-addressed — the Tornado server should require login credentials (username/password or token) before granting motor control |
| **Encryption (TLS/SSL)** | Self-addressed — all HMI ↔ robot traffic should use HTTPS/WSS to prevent man-in-the-middle attacks on the network |
| **Access control** | HMI-visible — display current user role (operator vs. admin); restrict dangerous commands (speed > 3, calibration) to admin |
| **Audit logging** | Both — every command is logged server-side (self-addressed), and a read-only log viewer is available in the HMI |
| **Network segmentation** | Self-addressed — the robot should be on an isolated VLAN or VPN, not exposed to the public internet |
| **Firmware integrity** | Self-addressed — verify software checksums on boot to detect tampering |

---

## Question 2

*Belt conveyor carrying products with barcodes/QR codes. Conveyor can stop/move in either direction. Robot receives a signal via webapp/HMI to spot and push products off the conveyor. What changes are needed?*

### Required changes

**Hardware modifications:**
1. **Linear rail or track** — mount the robot on a rail parallel to the conveyor so it can travel alongside products at matching speed
2. **Pushing actuator** — add a servo-driven arm or pneumatic piston to physically push products off the conveyor
3. **Position encoder** — add wheel encoders or a linear encoder on the rail to know the robot's exact position relative to the conveyor
4. **Side-mounted camera** — reposition the camera to face the conveyor laterally for optimal QR code scanning

**Software modifications:**
1. **Conveyor-synchronized motion** — the robot must match the conveyor's speed and direction. This requires reading a conveyor encoder or receiving speed data from a PLC (Programmable Logic Controller) via Modbus or OPC-UA
2. **Product tracking queue** — maintain a FIFO (First In, First Out) queue of products-to-push, received from the HMI or webapp. Each entry contains: product ID (QR data), target action (push), and priority
3. **Positional control** — replace time-based `move()` with closed-loop position control using encoder feedback, enabling the robot to align precisely with a target product
4. **Bidirectional conveyor handling** — the robot's scanning logic must account for products moving left or right, adjusting its own travel direction accordingly
5. **WebSocket or MQTT communication** — upgrade from HTTP POST to a real-time event-driven protocol so the HMI can push commands instantly and the robot can report status without polling
6. **State machine** — implement a finite state machine (FSM) with states: `IDLE → SCANNING → TRACKING → ALIGNED → PUSHING → RETURNING`

---

## Question 3

*What components for quick pushing? What control algorithms for rapid action (10 ms decision window)? What bottlenecks exist vs. when speed is not a concern?*

### Hardware for rapid pushing

| Component | Purpose |
|---|---|
| **Pneumatic solenoid actuator** | Sub-10 ms actuation time; far faster than servo motors |
| **High-speed camera (≥120 FPS)** | Reduces the time between frames, giving the controller more detection opportunities |
| **FPGA or dedicated vision co-processor** | Offloads QR decoding from the Raspberry Pi's CPU for near-instantaneous image processing |
| **Proximity / photoelectric sensor** | Provides a hardware interrupt the instant a product enters the push zone — faster than polling the camera |
| **Linear actuator with limit switches** | Ensures the pusher retracts fully before the next product arrives |

### Control algorithms

1. **Predictive tracking** — once a target product is first detected upstream, compute its expected arrival time at the push zone using conveyor speed × distance. Pre-position the actuator so no movement is wasted at decision time.
2. **Interrupt-driven triggering** — use a hardware interrupt from a photoelectric sensor at the push zone. When triggered, the ISR (Interrupt Service Routine) fires the solenoid immediately — no polling delay.
3. **PID position control** — if the robot must align with the product, a PID controller on the encoder feedback minimizes settling time.
4. **Look-ahead pipeline** — process frames in a pipeline: while frame N is being decoded, frame N+1 is being captured. This hides latency behind parallelism.

### Bottlenecks at 10 ms vs. unconstrained

| Factor | At 10 ms | When speed is not a concern |
|---|---|---|
| **Image capture** | Standard 30 FPS camera gives 33 ms/frame — too slow; need ≥120 FPS or hardware trigger | Any camera works |
| **QR decoding** | OpenCV's `QRCodeDetector` on a Pi takes ~15–30 ms — exceeds budget; need FPGA or pre-filtering | Software decoding is fine |
| **Actuation** | Servo motors are too slow (~100–500 ms); must use pneumatic/solenoid | Servo or linear actuator is acceptable |
| **Communication** | HTTP round-trip adds latency; need local edge computing, no network hop | Cloud or remote processing is fine |
| **Decision logic** | Must be hard real-time (deterministic); Linux is not an RTOS — may need a real-time microcontroller (e.g., STM32) | Soft real-time on Linux is sufficient |

---

## Question 4

*Robot serves two parallel belt conveyors. What design considerations for optimum autonomy? What if it receives multiple simultaneous push requests?*

### Design considerations

1. **Crossover mechanism** — the robot needs a perpendicular rail or rotary platform to switch between the two conveyors. Minimize crossover time to reduce idle gaps.

2. **Dual-camera setup** — mount one camera per conveyor side so the robot can monitor both lines simultaneously, even while working on one.

3. **Priority-based scheduling** — implement a **priority queue** for incoming push requests:
   - Assign priority based on product urgency, distance to push zone, and conveyor speed
   - Use a scheduling algorithm (e.g., Earliest Deadline First, EDF) to decide which product to handle next

4. **Predictive product tracking** — since conveyor speeds are known, the system can predict when each product will reach the push zone and schedule the robot's crossover in advance.

5. **Conflict resolution for simultaneous requests:**

   | Situation | Strategy |
   |---|---|
   | One product per conveyor, different arrival times | Handle the earlier one first, then cross over |
   | One product per conveyor, same arrival time | Handle the higher-priority product; the other may need a second pass (conveyor reversal) or a downstream backup pusher |
   | Multiple products on one conveyor | Batch-process if consecutive; otherwise queue by arrival time |
   | Overload (more requests than capacity) | Alert the operator via HMI; flag missed products for manual intervention or conveyor pause |

6. **Redundancy planning** — if throughput demand exceeds what one robot can handle, the system architecture should allow adding a second robot. The server assigns products to robots using a load-balancing algorithm.

---

## Question 5

*Nuclear radiation field, operators 25 miles away. Two HMIs with XOR operational logic (only one active at a time). Each HMI registered with a server connected to the robot's computer. Clarify the communication architecture.*

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    FIELD (Hazardous Zone)                     │
│                                                              │
│   ┌─────────┐    Serial/I²C    ┌──────────────────────┐     │
│   │  Robot   │◄───────────────►│  Robot Computer (Pi) │     │
│   │ (Motors, │                 │  - motor.py          │     │
│   │  Camera, │                 │  - camera.py         │     │
│   │  LED)    │                 │  - part_b.py         │     │
│   └─────────┘                 └──────────┬───────────┘     │
│                                          │ Encrypted        │
│                                          │ VPN tunnel        │
└──────────────────────────────────────────┼───────────────────┘
                                           │
                              ─── 25+ miles, secure WAN ───
                                           │
┌──────────────────────────────────────────┼───────────────────┐
│                  CONTROL CENTER (Safe Zone)                   │
│                                          │                   │
│                              ┌───────────▼──────────┐       │
│                              │   Central Server     │       │
│                              │  - Registration DB   │       │
│                              │  - XOR Gate Logic    │       │
│                              │  - Command Router    │       │
│                              │  - Audit Logger      │       │
│                              └─────┬─────┬──────────┘       │
│                                    │     │                   │
│                 ┌──────────────────┘     └───────────────┐   │
│                 │                                        │   │
│         ┌───────▼───────┐                      ┌─────────▼─┐│
│         │   HMI Alpha   │                      │  HMI Beta ││
│         │  (Primary)    │                      │ (Standby) ││
│         │  Operator A   │                      │ Operator B││
│         └───────────────┘                      └───────────┘│
└──────────────────────────────────────────────────────────────┘
```

### XOR operational logic

The XOR constraint means **exactly one** HMI may be active (registered) at any time. If both are active or both are inactive, the robot will **not** accept commands.

| HMI Alpha | HMI Beta | Robot accepts commands? |
|:-:|:-:|:-:|
| Inactive | Inactive | **No** — no operator in control |
| **Active** | Inactive | **Yes** — Alpha controls |
| Inactive | **Active** | **Yes** — Beta controls |
| Active | Active | **No** — XOR violation, safety lockout |

### Implementation

1. **Registration protocol** — each HMI sends a `REGISTER` request to the central server with its credentials. The server checks the XOR condition before granting control.
2. **Heartbeat** — the active HMI sends periodic heartbeats. If missed for N seconds, the server de-registers it, allowing the other HMI to take over (failover).
3. **Handoff procedure** — to transfer control, the active HMI must explicitly `DEREGISTER` before the standby HMI can `REGISTER`. This prevents both being active simultaneously.
4. **VPN tunnel** — all traffic between the control center and the field uses an encrypted VPN (e.g., WireGuard or IPSec) over a secure WAN link, providing confidentiality and integrity across the 25-mile distance.
5. **Audit trail** — every registration, command, and state change is logged on the central server for accountability and incident investigation.

---

## Question 6

*QR code on a box posts to a web page with handling instructions (size, mass, grip force). Design a system to remove the material with ultimate care.*

### System design

**Hardware:**

| Component | Purpose |
|---|---|
| **6-DOF robotic arm** (e.g., UR3e) | Precise, force-controlled manipulation of the material |
| **Force/torque sensor** (wrist-mounted) | Measures gripping force in real-time to ensure it matches instructions |
| **Soft gripper or adaptive fingers** | Conforms to irregular shapes without damaging delicate material |
| **Load cell** | Verifies the mass of the object matches the expected value (quality check) |
| **High-resolution camera** | Reads the QR code and confirms correct box identification |
| **Weighing platform** | Independent mass verification after extraction |

**Software:**

1. **QR → Instruction pipeline:**
   - Camera detects and decodes QR code
   - QR data is a URL; the system issues an HTTP GET to retrieve a JSON payload:
     ```json
     {
       "product_id": "X-4821",
       "size_mm": [120, 80, 60],
       "mass_kg": 0.45,
       "max_grip_force_N": 8.5,
       "handling_notes": "fragile, keep upright",
       "destination": "station_3"
     }
     ```

2. **Grip-force control loop:**
   - A PID controller regulates the gripper's motor current based on the force/torque sensor reading
   - Setpoint = `max_grip_force_N` from the instruction payload
   - Safety margin: grip at 80% of max to prevent crushing, with a hard upper-limit cutoff

3. **Motion planning:**
   - Given `size_mm`, compute approach vector and clearance path to avoid collisions
   - Given `handling_notes` (e.g., "keep upright"), constrain the arm's orientation during transport
   - Use a trajectory planner (e.g., MoveIt with ROS) to generate smooth, jerk-limited paths

4. **Verification loop:**
   - After extraction, place the object on the weighing platform
   - Compare measured mass to `mass_kg` ± tolerance
   - If mismatch → flag anomaly, alert operator via HMI

**Control system:**
- **Supervisory layer** — coordinates the overall sequence (detect → fetch instructions → grip → extract → verify → deposit)
- **Servo layer** — real-time joint-level control of the robotic arm (typically runs at 1 kHz)
- **Safety layer** — monitors force limits, workspace boundaries, and emergency stop conditions independently from the main controller

---

## Question 7

*Some products are "urgent" / critical to kick off the conveyor. If not pushed, an action should be taken. How to address this and what impact on hardware/software?*

### Addressing urgent product handling

**Detection and classification:**
- Encode urgency level in the QR code data or in the server's product database (e.g., `"priority": "critical"`)
- When a critical QR code is detected, the system immediately escalates it to the top of the scheduling queue, preempting any normal-priority tasks

**Escalation on failure:**

| Stage | Action |
|---|---|
| **1st attempt failed** | Reverse the conveyor to bring the product back into the push zone; retry |
| **2nd attempt failed** | Trigger a **conveyor stop** to prevent the critical product from leaving the system |
| **Any failure** | Send an **alarm** to the HMI (audible + visual) and log the event in the SCADA system |
| **Continued failure** | Notify a downstream backup mechanism (e.g., a second robot or a manual intervention station) |

**Hardware impact:**
- **Redundant pusher** — install a secondary actuator downstream as a fail-safe for critical products
- **Conveyor emergency brake** — the conveyor motor controller must support immediate stop commands from the robot's computer
- **Visual alarm (beacon/siren)** — mounted near the conveyor to attract operator attention

**Software impact:**
- **Priority queue with preemption** — the scheduler must support real-time preemption; when a critical product is detected, the current non-critical task is paused
- **Watchdog timer per critical product** — if the product is not confirmed pushed within a deadline, the escalation sequence activates automatically
- **Event logging** — every critical product event (detected, attempted, succeeded, failed) is recorded with timestamps for compliance and audit
- **HMI notification system** — real-time push notifications (via WebSocket) to all active HMI clients when a critical event occurs

---

## Question 8

*For Question 7, record data for (1) incoming requests, (2) actions taken, (3) results. Explain SCADA, HMI, top software layer, and holistic AI integration.*

### SCADA system and monitored parameters

**SCADA (Supervisory Control and Data Acquisition)** is the top-level software layer that aggregates data from all field devices and presents a unified operational view.

**Parameters to monitor:**

| Category | Parameters |
|---|---|
| **Conveyor** | Speed (m/s), direction, running/stopped state, motor current, belt temperature |
| **Robot** | Position on rail, current action state, actuator status, battery/power level |
| **Product flow** | Products detected per minute, products successfully pushed, products missed, queue depth |
| **Critical events** | Critical product detections, push success/failure rate, escalation triggers, conveyor stops |
| **System health** | Network latency, CPU load, camera FPS, sensor calibration status |

**Data recording schema:**

```
incoming_requests:
  - timestamp, product_id, qr_data, priority, conveyor_id, position

actions_taken:
  - timestamp, product_id, action_type (push/skip/retry/stop_conveyor),
    robot_position, actuator_force

results:
  - timestamp, product_id, outcome (success/fail/escalated),
    time_to_complete, error_code
```

### Required HMI for this task

The operator-facing HMI should include:

1. **Live dashboard** — real-time conveyor visualization showing product positions, robot location, and push zone
2. **Event feed** — scrolling list of recent events (detections, pushes, alarms) color-coded by priority
3. **KPI panel** — throughput rate, success rate, average response time, missed-product count
4. **Alarm management** — active alarms with acknowledge/silence controls; alarm history
5. **Manual override** — buttons to pause conveyor, trigger a push, or recall the robot
6. **Historical data view** — filterable tables and charts of past requests, actions, and results

### Top software layer

The highest software layer sits above SCADA and provides **business intelligence and decision support:**

- **Reporting engine** — generates shift reports, daily summaries, and compliance documents from the recorded data
- **Trend analysis** — identifies patterns such as increasing failure rates on a specific conveyor section, suggesting preventive maintenance
- **Integration API** — exposes the system's data to enterprise systems (ERP, MES) via REST or OPC-UA for supply chain visibility

### Holistic AI system correlated with each software layer

| Software Layer | AI Model | Training Data | Purpose |
|---|---|---|---|
| **Field (edge)** | **Computer vision CNN** (e.g., YOLOv8) | Labeled images of products, QR codes, and defects | Real-time product detection and classification — faster and more robust than OpenCV's built-in QR detector |
| **Field (edge)** | **Reinforcement Learning (RL) agent** | Simulated and real robot–conveyor interactions | Optimizes push timing and robot positioning through trial-and-error learning; maximizes success rate while minimizing energy usage |
| **SCADA** | **Anomaly detection model** (autoencoder or Isolation Forest) | Historical sensor readings with labeled normal/abnormal periods | Detects deviations from normal operating patterns (e.g., motor current spike = belt jam) and triggers preventive alerts |
| **SCADA** | **Predictive maintenance model** (LSTM or survival analysis) | Maintenance logs + sensor time-series | Predicts when components (belt, motor bearings, actuator) will need service, enabling scheduled downtime instead of unexpected failures |
| **Business layer** | **Demand forecasting model** (time-series: Prophet, ARIMA) | Historical product flow data + external demand signals | Predicts incoming product volumes to optimize staffing, conveyor speed, and robot deployment |
| **Business layer** | **Process optimization model** (Bayesian optimization or genetic algorithm) | SCADA KPIs across different operating configurations | Finds optimal conveyor speed, robot speed, and scheduling parameters that maximize throughput and minimize missed products |

**Data scheme alignment:**
- **Edge models** consume raw sensor data (images, encoder ticks) at millisecond granularity
- **SCADA models** consume aggregated time-series data at second-to-minute granularity
- **Business models** consume daily/weekly KPI summaries and trend data
- All models feed predictions back into the layer below: business forecasts adjust SCADA setpoints, SCADA anomaly alerts adjust edge behavior, creating a **closed-loop intelligent automation system**
