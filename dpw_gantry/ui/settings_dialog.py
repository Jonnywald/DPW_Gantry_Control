"""Application and Hardware Settings Dialog."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QPlainTextEdit, QPushButton,
    QTabWidget, QWidget, QDialogButtonBox, QGroupBox
)
from ..core.gcode_generator import GCodeConfig


class SettingsDialog(QDialog):
    """Configuration dialog for gantry bed, default motion feeds, and G-code scripts."""

    def __init__(
        self,
        bed_w: float = 200.0,
        bed_h: float = 200.0,
        grid_sp: float = 10.0,
        gcode_config: Optional[GCodeConfig] = None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.setWindowTitle("Gantry & Dispenser Settings")
        self.resize(550, 480)

        self.bed_width = bed_w
        self.bed_height = bed_h
        self.grid_spacing = grid_sp
        self.gcode_config = gcode_config or GCodeConfig()

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        tabs = QTabWidget()

        # --- Tab 1: Gantry Bed & Motion ---
        tab_bed = QWidget()
        bed_layout = QVBoxLayout(tab_bed)

        # Bed Dimensions
        bed_group = QGroupBox("Gantry Physical Limits")
        bed_form = QFormLayout(bed_group)

        self.spin_bed_w = QDoubleSpinBox()
        self.spin_bed_w.setRange(10.0, 2000.0)
        self.spin_bed_w.setValue(self.bed_width)
        bed_form.addRow("Bed Width X (mm):", self.spin_bed_w)

        self.spin_bed_h = QDoubleSpinBox()
        self.spin_bed_h.setRange(10.0, 2000.0)
        self.spin_bed_h.setValue(self.bed_height)
        bed_form.addRow("Bed Height Y (mm):", self.spin_bed_h)

        self.spin_grid = QDoubleSpinBox()
        self.spin_grid.setRange(1.0, 100.0)
        self.spin_grid.setValue(self.grid_spacing)
        bed_form.addRow("Grid Spacing (mm):", self.spin_grid)

        bed_layout.addWidget(bed_group)

        # Feedrates & Defaults
        feed_group = QGroupBox("Default Feedrates & Dwells")
        feed_form = QFormLayout(feed_group)

        self.spin_travel_f = QDoubleSpinBox()
        self.spin_travel_f.setRange(100.0, 30000.0)
        self.spin_travel_f.setValue(self.gcode_config.travel_feedrate)
        feed_form.addRow("Rapid Travel Feed (G0 mm/min):", self.spin_travel_f)

        self.spin_disp_f = QDoubleSpinBox()
        self.spin_disp_f.setRange(10.0, 10000.0)
        self.spin_disp_f.setValue(self.gcode_config.default_dispense_feedrate)
        feed_form.addRow("Default Dispense Feed (G1 mm/min):", self.spin_disp_f)

        self.spin_def_pwm = QSpinBox()
        self.spin_def_pwm.setRange(0, 255)
        self.spin_def_pwm.setValue(self.gcode_config.default_motor_pwm)
        feed_form.addRow("Default Vibration PWM (0-255):", self.spin_def_pwm)

        self.spin_pre_dwell = QSpinBox()
        self.spin_pre_dwell.setRange(0, 5000)
        self.spin_pre_dwell.setValue(self.gcode_config.pre_dispense_dwell_ms)
        feed_form.addRow("Pre-dispense Dwell (ms):", self.spin_pre_dwell)

        self.spin_post_dwell = QSpinBox()
        self.spin_post_dwell.setRange(0, 5000)
        self.spin_post_dwell.setValue(self.gcode_config.post_dispense_dwell_ms)
        feed_form.addRow("Post-dispense Dwell (ms):", self.spin_post_dwell)

        bed_layout.addWidget(feed_group)
        bed_layout.addStretch()
        tabs.addTab(tab_bed, "Bed & Motion")

        # --- Tab 2: Custom G-Code Scripts ---
        tab_scripts = QWidget()
        scripts_layout = QVBoxLayout(tab_scripts)

        scripts_layout.addWidget(QLabel("Startup G-Code Script:"))
        self.txt_startup = QPlainTextEdit()
        self.txt_startup.setPlainText(self.gcode_config.startup_gcode)
        scripts_layout.addWidget(self.txt_startup)

        scripts_layout.addWidget(QLabel("Ending G-Code Script:"))
        self.txt_ending = QPlainTextEdit()
        self.txt_ending.setPlainText(self.gcode_config.ending_gcode)
        scripts_layout.addWidget(self.txt_ending)

        tabs.addTab(tab_scripts, "G-Code Scripts")

        main_layout.addWidget(tabs)

        # Dialog Buttons
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        btn_box.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self._restore_defaults)
        main_layout.addWidget(btn_box)

    def _on_accept(self):
        self.bed_width = self.spin_bed_w.value()
        self.bed_height = self.spin_bed_h.value()
        self.grid_spacing = self.spin_grid.value()

        self.gcode_config.travel_feedrate = self.spin_travel_f.value()
        self.gcode_config.default_dispense_feedrate = self.spin_disp_f.value()
        self.gcode_config.default_motor_pwm = self.spin_def_pwm.value()
        self.gcode_config.pre_dispense_dwell_ms = self.spin_pre_dwell.value()
        self.gcode_config.post_dispense_dwell_ms = self.spin_post_dwell.value()
        self.gcode_config.startup_gcode = self.txt_startup.toPlainText()
        self.gcode_config.ending_gcode = self.txt_ending.toPlainText()

        self.accept()

    def _restore_defaults(self):
        default_cfg = GCodeConfig()
        self.spin_bed_w.setValue(200.0)
        self.spin_bed_h.setValue(200.0)
        self.spin_grid.setValue(10.0)

        self.spin_travel_f.setValue(default_cfg.travel_feedrate)
        self.spin_disp_f.setValue(default_cfg.default_dispense_feedrate)
        self.spin_def_pwm.setValue(default_cfg.default_motor_pwm)
        self.spin_pre_dwell.setValue(default_cfg.pre_dispense_dwell_ms)
        self.spin_post_dwell.setValue(default_cfg.post_dispense_dwell_ms)
        self.txt_startup.setPlainText(default_cfg.startup_gcode)
        self.txt_ending.setPlainText(default_cfg.ending_gcode)
