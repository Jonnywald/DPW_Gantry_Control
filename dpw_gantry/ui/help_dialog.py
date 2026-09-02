"""Help, User Guide, and Hardware Documentation Dialog."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QPushButton, QTabWidget, QWidget
)


class HelpDialog(QDialog):
    """Help dialog containing Quick Start guide, G-Code reference, and hardware wiring notes."""

    def __init__(self, initial_tab: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("DPW Gantry - User Guide & Hardware Reference")
        self.resize(750, 580)
        self._init_ui(initial_tab)

    def _init_ui(self, initial_tab: int):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        tabs = QTabWidget()

        # Tab 1: Quick Start & Drawing Guide
        tb_quickstart = QTextBrowser()
        tb_quickstart.setOpenExternalLinks(True)
        tb_quickstart.setHtml("""
        <h2 style='color: #8be9fd;'>🚀 Quick Start Guide</h2>
        <p>This software controls a 2D Powder-Dispensing Gantry driven by a BigTreeTech SKR Mini E3 running Marlin firmware.</p>
        
        <h3 style='color: #50fa7b;'>1. Hardware Connection</h3>
        <ul>
            <li>Select your board's COM port (or check <b>Virtual / Simulation Board</b> if hardware is not connected).</li>
            <li>Default baud rate is <b>250000</b>. Click <b>Connect</b>.</li>
        </ul>

        <h3 style='color: #50fa7b;'>2. Drawing Shapes & Paths</h3>
        <ul>
            <li><b>Select / Move:</b> Click any shape on the bed to view or modify its dimensions and fill settings. Drag to translate.</li>
            <li><b>Rectangle:</b> Click and drag on the bed to create a rectangle.</li>
            <li><b>Circle:</b> Click the center point and drag outward to define the radius.</li>
            <li><b>Polyline:</b> Left-click to add path vertices; right-click or double-click to finish open line.</li>
            <li><b>Polygon:</b> Left-click vertices; right-click or double-click to close polygon.</li>
            <li><b>Dispense Dot:</b> Single-click to place a powder dot dispense location.</li>
        </ul>

        <h3 style='color: #50fa7b;'>3. Fill Patterns</h3>
        <ul>
            <li><b>Outline Only:</b> Dispenses along the outer boundary.</li>
            <li><b>Line Hatching:</b> Generates parallel raster lines with configurable angle (0°–360°) and step-over spacing.</li>
            <li><b>Cross Hatching:</b> Bidirectional grid pass (+90° offset).</li>
            <li><b>Inward Spiral:</b> Concentric inward offset paths down to the core to minimize non-dispensing travel lifts.</li>
        </ul>

        <h3 style='color: #50fa7b;'>4. G-Code Generation & Execution</h3>
        <ul>
            <li>Click <b>Generate G-Code</b> to compile toolpaths into Marlin commands with automatic <code>M106</code> / <code>M107</code> injection.</li>
            <li>Click <b>Dry Run</b> to verify motion with the powder vibration motor safely disabled.</li>
            <li>Click <b>Execute Dispense</b> to start active powder dispensing.</li>
        </ul>
        """)
        tabs.addTab(tb_quickstart, "Quick Start")

        # Tab 2: G-Code Reference
        tb_gcode = QTextBrowser()
        tb_gcode.setHtml("""
        <h2 style='color: #8be9fd;'>📜 Supported Marlin G-Code Commands</h2>
        <table border='1' cellpadding='6' cellspacing='0' style='border-collapse: collapse; border-color: #414458; width: 100%;'>
            <tr style='background-color: #282a36; color: #8be9fd;'>
                <th>Command</th><th>Description</th><th>Usage in DPW Gantry</th>
            </tr>
            <tr>
                <td><code>G0 X.. Y.. F..</code></td>
                <td>Rapid Linear Travel</td>
                <td>Non-dispensing positioning moves. Powder motor is forced OFF (<code>M107</code>).</td>
            </tr>
            <tr>
                <td><code>G1 X.. Y.. F..</code></td>
                <td>Linear Dispense Move</td>
                <td>Active dispensing move with powder vibration motor ON (<code>M106 S...</code>).</td>
            </tr>
            <tr>
                <td><code>G4 P&lt;ms&gt;</code></td>
                <td>Dwell / Pause</td>
                <td>Pre-dispense and post-dispense stabilization delays.</td>
            </tr>
            <tr>
                <td><code>G28 XY</code></td>
                <td>Home X & Y Axes</td>
                <td>Homes the gantry to the physical limit switches or sensorless stops.</td>
            </tr>
            <tr>
                <td><code>G90 / G91</code></td>
                <td>Absolute / Relative Mode</td>
                <td>Switches between absolute work coordinates and relative jogging.</td>
            </tr>
            <tr>
                <td><code>G92 X0 Y0</code></td>
                <td>Set Coordinate Origin</td>
                <td>Zeros current position as the workspace origin (0,0).</td>
            </tr>
            <tr>
                <td><code>M106 S&lt;0-255&gt;</code></td>
                <td>Part Cooling Fan / PWM Motor</td>
                <td>Turns ON powder dispenser vibration motor with specified PWM duty cycle.</td>
            </tr>
            <tr>
                <td><code>M107</code></td>
                <td>Fan / Motor OFF</td>
                <td>Immediately turns OFF the vibration motor.</td>
            </tr>
            <tr>
                <td><code>M112</code></td>
                <td>Emergency Stop</td>
                <td>Instantly halts all stepper movement and shuts down heater/motor outputs.</td>
            </tr>
        </table>
        """)
        tabs.addTab(tb_gcode, "G-Code Reference")

        # Tab 3: Hardware & Wiring Guide
        tb_hw = QTextBrowser()
        tb_hw.setHtml("""
        <h2 style='color: #8be9fd;'>🔌 Hardware & Wiring (BTT SKR Mini E3)</h2>
        <p>The system utilizes the BigTreeTech SKR Mini E3 mainboard with TMC2209 silent stepper drivers.</p>
        
        <h3 style='color: #ffb86c;'>Port & Header Assignments:</h3>
        <ul>
            <li><b>USB Serial:</b> Connect to PC via USB cable. Default Marlin baud: <b>250000</b>.</li>
            <li><b>X Stepper (XM):</b> X-axis gantry motor.</li>
            <li><b>Y Stepper (YM):</b> Y-axis gantry motor.</li>
            <li><b>FAN0 Header:</b> Connect the 12V/24V powder vibration motor / eccentric actuator here. Controlled via <code>M106 S...</code> / <code>M107</code>.</li>
            <li><b>Endstops (X-STOP, Y-STOP):</b> Physical microswitches or configured for sensorless homing via TMC2209 stallGuard.</li>
        </ul>

        <h3 style='color: #ff5555;'>Safety Instructions:</h3>
        <ul>
            <li>Keep hands clear of the gantry axes during active dispensing.</li>
            <li>The large red <b>Emergency Stop (M112)</b> button in the UI or physical reset button will halt motion immediately.</li>
        </ul>
        """)
        tabs.addTab(tb_hw, "Hardware & Wiring")

        tabs.setCurrentIndex(initial_tab)
        layout.addWidget(tabs)

        # Close button
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
