# Hip Wear Tester System

A portable hip wear testing system for orthopedic implant durability research, built as a Senior Design project (SY26). The system drives stepper motors in synchronized cycles to simulate repetitive hip joint motion while monitoring temperature at the test stations.

## Hardware Overview

| Component | Role |
|-----------|------|
| **Raspberry Pi 4 Model B** | Hosts the GUI dashboard and reads temperature sensors |
| **Arduino #1 (Lateral)** | Controls the lateral/side stepper motor |
| **Arduino #2 (Top)** | Controls two top stepper motors (Station 1 and Station 2) |

### Motor Configuration

- **Lateral motor**: 13 back-and-forth steps per cycle (23 degrees each direction)
- **Top Left motor (S1)**: 5 back-and-forth steps per cycle (23 degrees each direction)
- **Top Right motor (S2)**: 5 back-and-forth steps per cycle (23 degrees each direction)

All motors are synchronized so that one overall cycle (all motors completing their respective steps) takes exactly **1 second**. The Arduino firmware pads each cycle with a delay to maintain this timing.

### Station Modes

| Mode | Active Motors |
|------|---------------|
| **S1** | Lateral + Top Left |
| **S2** | Lateral + Top Right |
| **BOTH** | Lateral + Top Left + Top Right |

## Software Architecture

The system is split into Arduino firmware (motor control) and a Python application (GUI + data logging) running on the Raspberry Pi.

### Python Application

```
main.py                          # Entry point
src/
  controller/
    tester_controller.py         # State machine (IDLE/RUNNING/PAUSED/ERROR),
                                 #   MotorIO interfaces (Sim + Arduino)
  uno_comms/
    uno_manager.py               # Orchestrates both Arduinos
    uno_single.py                # Serial interface for lateral Arduino
    uno_dual.py                  # Serial interface for top Arduino
  sensors/
    sim_sensor_manager.py        # Simulated temperature sensor
    sensor.py                    # Real sensor (stub)
    sensor_manager.py            # Real sensor manager (stub)
  data/
    logger.py                    # CSV data logging + matplotlib graph generation
  ui/
    app.py                       # Tkinter root window setup
    dashboard.py                 # Main dashboard with 200ms refresh loop
    theme.py                     # Dark theme colors and fonts
    panels/
      station_select.py          # Station mode radio buttons (S1/S2/BOTH)
      status.py                  # Status panel (state, elapsed time, cycles, motors)
      buttons.py                 # Start/Pause/Stop/Reset/E-Stop buttons
      temp_display.py            # Live temperature readout with sparklines
      temp_graph.py              # Real-time temperature graph
```

### Arduino Firmware

```
ino_files/
  lat_arduino.ino                # Lateral motor control
  top_arduino.ino                # Top motors control (S1, S2, or both)
```

### Serial Protocol

**Lateral Arduino** (default baud: 9600)

| Command | Description |
|---------|-------------|
| `START:<cycles>` | Begin running the specified number of cycles |
| `STOP` | Immediately stop and reset |

| Response | Description |
|----------|-------------|
| `STARTED:LAT:<cycles>` | Acknowledged start |
| `CYCLE:<n>` | Completed cycle number `n` |
| `DONE:LAT` | All cycles finished |
| `STOPPED:LAT` | Acknowledged stop |

**Top Arduino** (default baud: 9600)

| Command | Description |
|---------|-------------|
| `START:S1:<cycles>` | Run Station 1 for the specified cycles |
| `START:S2:<cycles>` | Run Station 2 for the specified cycles |
| `START:BOTH:<cycles>` | Run both stations for the specified cycles |
| `STOP` | Immediately stop and reset |

| Response | Description |
|----------|-------------|
| `STARTED:TOP:<mode>:<cycles>` | Acknowledged start |
| `CYCLE:<n>` | Completed cycle number `n` |
| `DONE:TOP` | All cycles finished |
| `STOPPED:TOP` | Acknowledged stop |

## Data Logging

Each test run creates a timestamped folder under `data/runs/`:

```
data/runs/run_20260408_143000_S1/
  data.csv       # Logged at 1 Hz
  graph.png      # Temperature vs time plot (generated on test end)
```

**CSV columns:** `timestamp`, `elapsed_seconds`, `elapsed_time`, `station_mode`, `test_state`, `temp_station1_celsius`, `temp_station2_celsius`, `lateral_motor_state`, `top_motor_station1_state`, `top_motor_station2_state`, `log_message`

## Getting Started

### Prerequisites

- Python 3.10+
- Raspberry Pi 4 Model B (for deployment) or macOS/Linux (for development)
- Two Arduino boards with stepper motor drivers
- `pyserial` for serial communication
- `matplotlib` for graph generation
- `tkinter` (usually included with Python)

### Running the Application

```bash
python main.py
```

### Serial Ports

The serial port names differ between development and deployment:

| Arduino | Mac (dev) | Raspberry Pi |
|---------|-----------|--------------|
| Lateral | `Check Arduino IDE` | `/dev/ttyACM0` |
| Top | `Check Arduino IDE` | `/dev/ttyACM1` |

Port configuration is in `src/controller/tester_controller.py` in the `TesterController.__init__` method.

### Uploading Arduino Firmware

Upload `ino_files/lat_arduino.ino` to the lateral Arduino and `ino_files/top_arduino.ino` to the top Arduino using the Arduino IDE.
