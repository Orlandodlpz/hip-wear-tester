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

### Python Dependencies

The application uses three external Python packages:

| Package | Used by | Why |
|---------|---------|-----|
| `pyserial` | `src/uno_comms/` | Serial communication with both Arduinos |
| `matplotlib` | `src/data/logger.py` | Generates `graph.png` (temperature vs. time) at the end of each run |
| `tkinter` | `src/ui/` | GUI framework |

`tkinter` is part of the Python standard library on most platforms but on the Raspberry Pi it ships as a separate apt package (`python3-tk`). `pyserial` and `matplotlib` install via pip.

### Raspberry Pi 4 Model B — Full Installation

The following has been tested on Raspberry Pi OS Bookworm (64-bit). Run each block in a terminal on the Pi.

**1. System packages** (Python, Tk for the GUI, pip):

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-tk python3-venv git
```

**2. Project location**

Clone or copy the project into the user's home directory, e.g. `/home/pi/hip-wear-tester`.

**3. Python virtual environment + Python packages**

Recommended: install the project's Python dependencies inside a virtual environment so they don't conflict with system packages.

```bash
cd ~/hip-wear-tester
python3 -m venv .venv
source .venv/bin/activate
pip install pyserial matplotlib
```

(If you prefer to install system-wide instead of using a venv, you may need `sudo pip install pyserial matplotlib --break-system-packages` on Bookworm.)

**4. Serial port permissions**

The Pi user must be in the `dialout` group to access `/dev/ttyACM*` without `sudo`:

```bash
sudo usermod -aG dialout $USER
```

Log out and back in (or reboot) for the group change to take effect.

**5. DS18B20 temperature sensor (1-Wire)**

The DS18B20 sensors plug into the Pi's GPIO and are read via the kernel's 1-Wire interface. Enable it once:

```bash
sudo raspi-config
# Interface Options -> 1-Wire -> Enable -> reboot
```

Wire the DS18B20 data line to GPIO 4 (physical pin 7) with a 4.7 kΩ pull-up resistor between the data line and 3.3V. After reboot, sensors should appear under `/sys/bus/w1/devices/28-*`. Confirm:

```bash
ls /sys/bus/w1/devices/
```

**6. Auto-launch the GUI on boot (optional)**

If the kiosk should start automatically on the touchscreen, add a systemd user service or an autostart entry. A minimal autostart approach using LXDE:

```bash
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/hip-wear-tester.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Hip Wear Tester
Exec=/home/pi/hip-wear-tester/.venv/bin/python /home/pi/hip-wear-tester/main.py
EOF
```

### Running the Application

From the project root, with the venv activated:

```bash
python main.py
```

### Serial Ports

The serial port names differ between development and deployment. Update `TesterController.__init__` in `src/controller/tester_controller.py` to match your environment:

| Arduino | Mac (dev) | Raspberry Pi |
|---------|-----------|--------------|
| Lateral | `/dev/tty.usbmodem31301` | `/dev/ttyACM0` |
| Top | `/dev/tty.usbmodem31401` | `/dev/ttyACM1` |

Port configuration is in `src/controller/tester_controller.py` in the `TesterController.__init__` method.

### Uploading Arduino Firmware

Upload `ino_files/lat_arduino.ino` to the lateral Arduino and `ino_files/top_arduino.ino` to the top Arduino using the Arduino IDE.

Both firmwares use **9600 baud** by default. If you change `Serial.begin(...)` in either `.ino`, change `baudrate=` in `TesterController.__init__` to match.
