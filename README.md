# DPW Gantry - 2D Powder-Dispensing Gantry Controller

A desktop application built with Python and **PySide6 (Qt)** designed for controlling a custom 2D powder-dispensing gantry driven by a **BigTreeTech (BTT) SKR Mini E3** running Marlin firmware over USB Serial.

![DPW Gantry UI](https://raw.githubusercontent.com/placeholder/preview.png)

---

## Key Features

### 1. Serial Interface & Hardware Control (BTT SKR Mini E3)
- **Auto-Detection**: Scans COM/TTY ports and connects with configurable baud rates (default: `250000` baud).
- **Virtual Simulation Mode**: Test and simulate entire toolpaths and G-code execution without requiring a physical board plugged in.
- **Dedicated Worker Thread (`QThread`)**: Non-blocking line-by-line G-code streaming engine that waits for Marlin `ok` responses and reports live progress.
- **Color-Coded Serial Terminal & MDI**: Real-time logging of sent commands (Cyan), hardware responses (Green), and errors (Red), with Up/Down arrow command history navigation.
- **Manual Control D-Pad**: Axis jogging with selectable step sizes (`0.1`, `1`, `10`, `50` mm), Homing (`G28 XY`), Origin Reset (`G92 X0 Y0`), and Big Red **Emergency Stop (`M112`)**.
- **Powder Vibration Motor Control (Fan Header)**: PWM slider (`0-255`), quick presets, and manual toggle (`M106 S<pwm>` / `M107`).

### 2. Interactive 2D Bed Visualizer & Vector CAD
- **2D Gantry Bed**: Customizable dimensions (default `200mm x 200mm`) with mm grid, major/minor divisions, origin marker `(0,0)` at lower-left, and mouse coordinate tracking.
- **CAD Drawing Tools**:
  - `Select / Move`: Select, translate, drag, resize, and inspect shapes.
  - `Rectangle`: 2-point box generator.
  - `Circle`: Center + radius generator with smooth segmented interpolation.
  - `Polyline`: Multi-vertex open paths.
  - `Polygon`: Arbitrary closed polygons.
  - `Dispense Dot`: Single-point powder dwell dots (`G4 P<dwell>`).
- **Shape Fill & Hatching Engine**:
  - **Outline Only**: Dispenses outer boundary only.
  - **Line Hatching**: Configurable hatch angle (0° to 360°) and step-over spacing in mm with zig-zag continuous travel.
  - **Cross Hatching**: Bidirectional cross-hatched grid (+90° offset).
  - **Inward Spiral Fill**: Concentric inward offset paths down to the core to minimize non-dispensing rapid travels.
- **Live Toolhead Tracking**: Real-time neon green crosshair and nozzle ring following gantry motion across the bed.

### 3. Automatic Powder Dispenser Sequencing
- Pre-moves to segment start with `G0` rapid travel (**Motor OFF via `M107`**).
- Fires `M106 S<pwm>` immediately before starting a dispensing pass (`G1`), with configurable pre-dispense dwell (`G4 P...`).
- Shuts off motor (`M107`) immediately upon finishing each segment and during rapid travel.
- **Dry Run Mode**: Executes the entire physical motion program safely with powder vibration disabled (`[DRY RUN]` tag) for dry validation.

### 4. File Management & G-Code Export/Import
- **Project Files (`.dpw` / `.json`)**: Save and load complete project workspaces including shape vectors, fill settings, dispenser parameters, and bed bounds.
- **Export G-Code**: Generates `.gcode` / `.nc` files for standalone execution on SD cards or OctoPrint.
- **Import External G-Code**: Load pre-made G-code files directly into the editor and 2D visualizer to stream to the board.

---

## Installation & Setup

### Requirements
- Python 3.9+
- Dependencies: `PySide6`, `pyserial`, `numpy`

### Quick Start
```bash
# Clone or navigate to the repository
cd DPW_gantry

# Install dependencies
pip install -r requirements.txt

# Launch Application
python main.py
```

### Running Tests
```bash
python -m unittest discover tests/
```

---

## Hardware Configuration (BTT SKR Mini E3 & Marlin)
- **USB Serial Connection**: Connect via USB Type-B / Mini-USB cable.
- **Fan Header (Vibration Motor)**: Connect 12V/24V vibration motor / dispensing actuator to the controllable Part Cooling Fan header (`FAN0`).
- **Baud Rate**: Default Marlin baud rate for SKR Mini E3 is `250000` or `115200`.
- **Homing**: Sensorless or physical endstops configured on X and Y axes.
