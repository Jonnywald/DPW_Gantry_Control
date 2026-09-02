"""Interactive Serial Terminal with MDI G-Code Command Prompt and Colorized Log."""

from __future__ import annotations
from typing import Optional, List
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QTextCursor, QKeyEvent
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QCheckBox, QGroupBox, QFileDialog
)
from .theme import ThemeColors


class HistoryLineEdit(QLineEdit):
    """QLineEdit with Up/Down arrow command history navigation."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._history: List[str] = []
        self._history_index: int = 0

    def add_history(self, cmd: str):
        if cmd and (not self._history or self._history[-1] != cmd):
            self._history.append(cmd)
        self._history_index = len(self._history)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Up:
            if self._history and self._history_index > 0:
                self._history_index -= 1
                self.setText(self._history[self._history_index])
            event.accept()
            return
        elif event.key() == Qt.Key_Down:
            if self._history and self._history_index < len(self._history) - 1:
                self._history_index += 1
                self.setText(self._history[self._history_index])
            else:
                self._history_index = len(self._history)
                self.clear()
            event.accept()
            return
        super().keyPressEvent(event)


class TerminalPanel(QGroupBox):
    """Panel for real-time serial logs and manual MDI command entry."""

    send_command = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Serial Terminal & MDI Command Prompt", parent)
        self._max_lines = 1500
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # 1. Header Toolbar
        top_row = QHBoxLayout()
        self.chk_autoscroll = QCheckBox("Auto-Scroll")
        self.chk_autoscroll.setChecked(True)

        self.chk_filter_ok = QCheckBox("Hide 'ok'")
        self.chk_filter_ok.setToolTip("Filter out spammy 'ok' acknowledgments from log view")
        self.chk_filter_ok.setChecked(False)

        self.btn_clear = QPushButton("Clear Log")
        self.btn_clear.clicked.connect(self._clear_log)

        self.btn_export = QPushButton("Save Log")
        self.btn_export.clicked.connect(self._save_log)

        top_row.addWidget(self.chk_autoscroll)
        top_row.addWidget(self.chk_filter_ok)
        top_row.addStretch()
        top_row.addWidget(self.btn_clear)
        top_row.addWidget(self.btn_export)
        layout.addLayout(top_row)

        # 2. Text Log Display
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(self.txt_log, 1)

        # 3. MDI Command Line
        cmd_row = QHBoxLayout()
        self.input_cmd = HistoryLineEdit()
        self.input_cmd.setPlaceholderText("Enter G-code command (e.g. G28 XY, M106 S200, G0 X50 Y50)...")
        self.input_cmd.returnPressed.connect(self._send_entered_cmd)

        self.btn_send = QPushButton("Send")
        self.btn_send.setObjectName("btn_primary")
        self.btn_send.clicked.connect(self._send_entered_cmd)

        cmd_row.addWidget(self.input_cmd, 1)
        cmd_row.addWidget(self.btn_send)
        layout.addLayout(cmd_row)

    def _send_entered_cmd(self):
        cmd = self.input_cmd.text().strip()
        if cmd:
            self.input_cmd.add_history(cmd)
            self.send_command.emit(cmd)
            self.input_cmd.clear()

    @Slot(str)
    def append_tx(self, line: str):
        """Logs transmitted command (Cyan)."""
        html = f"<span style='color: {ThemeColors.CYAN_ACCENT};'>&gt;&gt; {line}</span>"
        self._append_html(html)

    @Slot(str)
    def append_rx(self, line: str):
        """Logs received line (Green / Yellow / Red)."""
        if self.chk_filter_ok.isChecked() and (line == "ok" or line.startswith("ok ")):
            return

        if line.startswith("Error:") or line.startswith("!!"):
            html = f"<span style='color: {ThemeColors.RED_ALERT}; font-weight: bold;'>&lt;&lt; {line}</span>"
        elif line.startswith("[SYSTEM]"):
            html = f"<span style='color: {ThemeColors.AMBER_WARNING};'>&lt;&lt; {line}</span>"
        else:
            html = f"<span style='color: {ThemeColors.GREEN_SUCCESS};'>&lt;&lt; {line}</span>"
        self._append_html(html)

    @Slot(str)
    def append_error(self, err_msg: str):
        html = f"<span style='color: {ThemeColors.RED_ALERT}; font-weight: bold;'>[ERROR] {err_msg}</span>"
        self._append_html(html)

    def _append_html(self, html: str):
        self.txt_log.append(html)
        if self.chk_autoscroll.isChecked():
            cursor = self.txt_log.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.txt_log.setTextCursor(cursor)

    def _clear_log(self):
        self.txt_log.clear()

    def _save_log(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Terminal Log", "serial_log.txt", "Text Files (*.txt);;All Files (*.*)")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.txt_log.toPlainText())
