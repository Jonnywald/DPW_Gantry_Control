"""Serial Connection Management Panel."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QCheckBox, QGroupBox, QFrame
)
from ..core.serial_worker import SerialWorker, SerialState
from .theme import ThemeColors


class ConnectionPanel(QGroupBox):
    """Panel for managing serial COM port connection and board status."""

    connect_requested = Signal(str, int, bool)  # port, baud, is_virtual
    disconnect_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Hardware Connection (BTT SKR Mini E3)", parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Row 1: Port selector + Refresh
        port_layout = QHBoxLayout()
        port_label = QLabel("Port:")
        port_label.setFixedWidth(50)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(140)
        
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setToolTip("Refresh COM ports")
        self.btn_refresh.setFixedWidth(36)
        self.btn_refresh.clicked.connect(self.refresh_ports)

        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo, 1)
        port_layout.addWidget(self.btn_refresh)
        layout.addLayout(port_layout)

        # Row 2: Baud rate selector + Virtual board toggle
        baud_layout = QHBoxLayout()
        baud_label = QLabel("Baud:")
        baud_label.setFixedWidth(50)
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["250000", "115200", "57600", "38400", "19200", "9600"])
        self.baud_combo.setCurrentText("250000")  # Default Marlin / SKR Mini E3 baud

        baud_layout.addWidget(baud_label)
        baud_layout.addWidget(self.baud_combo, 1)
        layout.addLayout(baud_layout)

        # Row 3: Virtual Mode Checkbox
        self.chk_virtual = QCheckBox("Virtual / Simulation Board")
        self.chk_virtual.setToolTip("Simulate Marlin firmware response without physical USB connection")
        self.chk_virtual.toggled.connect(self._on_virtual_toggled)
        layout.addWidget(self.chk_virtual)

        # Row 4: Connect / Disconnect button
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setObjectName("btn_primary")
        self.btn_connect.setFixedHeight(34)
        self.btn_connect.clicked.connect(self._toggle_connection)
        layout.addWidget(self.btn_connect)

        # Row 5: Status Indicator
        status_box = QHBoxLayout()
        self.status_dot = QFrame()
        self.status_dot.setFixedSize(12, 12)
        self.status_dot.setStyleSheet(f"background-color: {ThemeColors.RED_ALERT}; border-radius: 6px;")
        
        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: 500;")
        
        status_box.addWidget(self.status_dot)
        status_box.addWidget(self.lbl_status, 1)
        layout.addLayout(status_box)

        # Populate initial ports
        self.refresh_ports()

    def refresh_ports(self):
        current_text = self.port_combo.currentText()
        self.port_combo.clear()
        ports = SerialWorker.get_available_ports()
        
        for dev, desc in ports:
            self.port_combo.addItem(desc, dev)
        
        if not ports:
            self.port_combo.addItem("No Ports Detected", "")

        # Try to restore selection
        idx = self.port_combo.findText(current_text)
        if idx != -1:
            self.port_combo.setCurrentIndex(idx)

    def _on_virtual_toggled(self, checked: bool):
        self.port_combo.setEnabled(not checked)
        self.btn_refresh.setEnabled(not checked)

    def _toggle_connection(self):
        if self.btn_connect.text() == "Connect":
            baud = int(self.baud_combo.currentText())
            is_virtual = self.chk_virtual.isChecked()
            port = self.port_combo.currentData()
            if not port:
                import re
                match = re.search(r"(COM\d+|/dev/\S+)", self.port_combo.currentText())
                port = match.group(1) if match else self.port_combo.currentText()
            self.connect_requested.emit(str(port), baud, is_virtual)
        else:
            self.disconnect_requested.emit()

    @Slot(str, int)
    def on_connected(self, port: str, baud: int):
        self.btn_connect.setText("Disconnect")
        self.btn_connect.setObjectName("btn_danger")
        self.btn_connect.setStyle(self.btn_connect.style())
        self.port_combo.setEnabled(False)
        self.baud_combo.setEnabled(False)
        self.chk_virtual.setEnabled(False)
        self.btn_refresh.setEnabled(False)

        self.status_dot.setStyleSheet(f"background-color: {ThemeColors.GREEN_SUCCESS}; border-radius: 6px;")
        self.lbl_status.setText(f"Connected: {port} ({baud})")
        self.lbl_status.setStyleSheet(f"color: {ThemeColors.GREEN_SUCCESS}; font-weight: bold;")

    @Slot()
    def on_disconnected(self):
        self.btn_connect.setText("Connect")
        self.btn_connect.setObjectName("btn_primary")
        self.btn_connect.setStyle(self.btn_connect.style())
        self.port_combo.setEnabled(not self.chk_virtual.isChecked())
        self.baud_combo.setEnabled(True)
        self.chk_virtual.setEnabled(True)
        self.btn_refresh.setEnabled(not self.chk_virtual.isChecked())

        self.status_dot.setStyleSheet(f"background-color: {ThemeColors.RED_ALERT}; border-radius: 6px;")
        self.lbl_status.setText("Status: Disconnected")
        self.lbl_status.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: 500;")

    @Slot(str)
    def on_state_changed(self, state: str):
        if state == SerialState.STREAMING:
            self.status_dot.setStyleSheet(f"background-color: {ThemeColors.CYAN_ACCENT}; border-radius: 6px;")
            self.lbl_status.setText("Status: Streaming Job...")
        elif state == SerialState.PAUSED:
            self.status_dot.setStyleSheet(f"background-color: {ThemeColors.AMBER_WARNING}; border-radius: 6px;")
            self.lbl_status.setText("Status: Job Paused")
        elif state == SerialState.ESTOP:
            self.status_dot.setStyleSheet(f"background-color: {ThemeColors.RED_ALERT}; border-radius: 6px;")
            self.lbl_status.setText("Status: EMERGENCY STOP")
