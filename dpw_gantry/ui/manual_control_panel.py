"""Manual Gantry Control Panel (Jogging, Homing, E-Stop, Dispenser PWM)."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QRadioButton, QButtonGroup, QSlider,
    QSpinBox, QGroupBox, QFrame
)
from .theme import ThemeColors


class ManualControlPanel(QGroupBox):
    """Panel for manual gantry jogging, homing, coordinate zeroing, and dispenser testing."""

    send_command = Signal(str)
    emergency_stop_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Manual Gantry & Dispenser Control", parent)
        self._step_size: float = 10.0
        self._jog_feedrate: float = 2000.0
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # 1. Live Position Readout Box
        pos_frame = QFrame()
        pos_frame.setStyleSheet(f"background-color: {ThemeColors.BG_INPUT}; border-radius: 6px; padding: 6px;")
        pos_layout = QHBoxLayout(pos_frame)
        
        self.lbl_pos_x = QLabel("X: 0.000 mm")
        self.lbl_pos_x.setStyleSheet(f"color: {ThemeColors.CYAN_ACCENT}; font-size: 14px; font-weight: bold; font-family: monospace;")
        self.lbl_pos_y = QLabel("Y: 0.000 mm")
        self.lbl_pos_y.setStyleSheet(f"color: {ThemeColors.CYAN_ACCENT}; font-size: 14px; font-weight: bold; font-family: monospace;")

        pos_layout.addWidget(self.lbl_pos_x)
        pos_layout.addWidget(self.lbl_pos_y)
        layout.addWidget(pos_frame)

        # 2. Step Size Selector
        step_group_box = QGroupBox("Jog Step Size (mm)")
        step_layout = QHBoxLayout(step_group_box)
        self.step_button_group = QButtonGroup(self)
        
        steps = [0.1, 1.0, 10.0, 50.0]
        for s in steps:
            rb = QRadioButton(f"{s} mm")
            if s == 10.0:
                rb.setChecked(True)
            self.step_button_group.addButton(rb)
            step_layout.addWidget(rb)
            rb.toggled.connect(lambda chk, val=s: self._on_step_changed(chk, val))

        layout.addWidget(step_group_box)

        # 3. Jog D-Pad Matrix
        dpad_group = QGroupBox("Motion Jogging")
        dpad_layout = QGridLayout(dpad_group)
        dpad_layout.setSpacing(6)

        self.btn_yp = QPushButton("▲ Y+")
        self.btn_yp.setFixedHeight(36)
        self.btn_yp.clicked.connect(lambda: self._jog(0, self._step_size))

        self.btn_ym = QPushButton("▼ Y-")
        self.btn_ym.setFixedHeight(36)
        self.btn_ym.clicked.connect(lambda: self._jog(0, -self._step_size))

        self.btn_xp = QPushButton("X+ ▶")
        self.btn_xp.setFixedHeight(36)
        self.btn_xp.clicked.connect(lambda: self._jog(self._step_size, 0))

        self.btn_xm = QPushButton("◀ X-")
        self.btn_xm.setFixedHeight(36)
        self.btn_xm.clicked.connect(lambda: self._jog(-self._step_size, 0))

        self.btn_home_xy = QPushButton("⌂ Home XY")
        self.btn_home_xy.setStyleSheet("font-weight: bold;")
        self.btn_home_xy.clicked.connect(self._home_xy)

        dpad_layout.addWidget(self.btn_yp, 0, 1)
        dpad_layout.addWidget(self.btn_xm, 1, 0)
        dpad_layout.addWidget(self.btn_home_xy, 1, 1)
        dpad_layout.addWidget(self.btn_xp, 1, 2)
        dpad_layout.addWidget(self.btn_ym, 2, 1)

        layout.addWidget(dpad_group)

        # 4. Origin / Zeroing Actions
        origin_layout = QHBoxLayout()
        self.btn_zero = QPushButton("Set Zero (G92 X0 Y0)")
        self.btn_zero.setToolTip("Set current physical coordinates as Origin (0,0)")
        self.btn_zero.clicked.connect(lambda: self.send_command.emit("G92 X0 Y0"))

        self.btn_goto_origin = QPushButton("Go To (0,0)")
        self.btn_goto_origin.clicked.connect(lambda: self.send_command.emit("G0 X0 Y0 F2000"))

        origin_layout.addWidget(self.btn_zero)
        origin_layout.addWidget(self.btn_goto_origin)
        layout.addLayout(origin_layout)

        # 5. Powder Dispenser (Fan Header) Manual Control
        dispenser_group = QGroupBox("Powder Vibration Motor (Fan Header)")
        disp_layout = QVBoxLayout(dispenser_group)

        slider_row = QHBoxLayout()
        slider_label = QLabel("PWM:")
        self.slider_pwm = QSlider(Qt.Horizontal)
        self.slider_pwm.setRange(0, 255)
        self.slider_pwm.setValue(255)

        self.spin_pwm = QSpinBox()
        self.spin_pwm.setRange(0, 255)
        self.spin_pwm.setValue(255)
        self.spin_pwm.setFixedWidth(60)

        self.slider_pwm.valueChanged.connect(self.spin_pwm.setValue)
        self.spin_pwm.valueChanged.connect(self.slider_pwm.setValue)

        slider_row.addWidget(slider_label)
        slider_row.addWidget(self.slider_pwm, 1)
        slider_row.addWidget(self.spin_pwm)
        disp_layout.addLayout(slider_row)

        # Toggle Button
        self.btn_motor_toggle = QPushButton("Start Vibration (M106)")
        self.btn_motor_toggle.setStyleSheet(f"background-color: {ThemeColors.AMBER_WARNING}; color: #18191f; font-weight: bold;")
        self.btn_motor_toggle.setCheckable(True)
        self.btn_motor_toggle.clicked.connect(self._toggle_vibration)
        disp_layout.addWidget(self.btn_motor_toggle)

        layout.addWidget(dispenser_group)

        # 6. Big Emergency Stop Button (M112)
        self.btn_estop = QPushButton("🛑 EMERGENCY STOP (M112)")
        self.btn_estop.setObjectName("btn_danger")
        self.btn_estop.setFixedHeight(44)
        self.btn_estop.clicked.connect(self.emergency_stop_requested.emit)
        layout.addWidget(self.btn_estop)

    def _on_step_changed(self, checked: bool, val: float):
        if checked:
            self._step_size = val

    def _jog(self, dx: float, dy: float):
        """Sends relative motion command."""
        cmd = f"G91\nG0 X{dx:.3f} Y{dy:.3f} F{self._jog_feedrate:.0f}\nG90"
        self.send_command.emit(cmd)

    def _home_xy(self):
        self.send_command.emit("G28 XY")

    def _toggle_vibration(self, checked: bool):
        if checked:
            pwm = self.spin_pwm.value()
            self.send_command.emit(f"M106 S{pwm}")
            self.btn_motor_toggle.setText("Stop Vibration (M107)")
            self.btn_motor_toggle.setStyleSheet(f"background-color: {ThemeColors.RED_ALERT}; color: #ffffff; font-weight: bold;")
        else:
            self.send_command.emit("M107")
            self.btn_motor_toggle.setText("Start Vibration (M106)")
            self.btn_motor_toggle.setStyleSheet(f"background-color: {ThemeColors.AMBER_WARNING}; color: #18191f; font-weight: bold;")

    @Slot(float, float)
    def update_position(self, x: float, y: float):
        self.lbl_pos_x.setText(f"X: {x:.3f} mm")
        self.lbl_pos_y.setText(f"Y: {y:.3f} mm")
