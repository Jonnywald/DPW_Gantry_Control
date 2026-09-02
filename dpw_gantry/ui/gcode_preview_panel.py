"""G-code Preview, Statistics, and Job Execution Panel."""

from __future__ import annotations
import time
from typing import Optional, List
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QProgressBar, QGroupBox, QFileDialog,
    QMessageBox, QFrame
)
from ..core.gcode_generator import GCodeStats
from .theme import ThemeColors


class GCodePreviewPanel(QGroupBox):
    """Panel for viewing generated G-code, inspecting statistics, and launching jobs."""

    generate_gcode_requested = Signal()
    dry_run_requested = Signal(list)
    execute_job_requested = Signal(list)
    pause_job_requested = Signal()
    resume_job_requested = Signal()
    abort_job_requested = Signal()
    import_gcode_requested = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("G-Code Generation & Execution", parent)
        self._job_start_time: float = 0.0
        self._is_paused = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # 1. Action Toolbar Row
        tools_row = QHBoxLayout()
        
        self.btn_generate = QPushButton("⚡ Generate G-Code")
        self.btn_generate.setObjectName("btn_primary")
        self.btn_generate.clicked.connect(self.generate_gcode_requested.emit)
        
        self.btn_import = QPushButton("📂 Import G-Code")
        self.btn_import.clicked.connect(self._on_import_clicked)
        
        self.btn_export = QPushButton("💾 Export .gcode")
        self.btn_export.clicked.connect(self._on_export_clicked)

        tools_row.addWidget(self.btn_generate)
        tools_row.addWidget(self.btn_import)
        tools_row.addWidget(self.btn_export)
        layout.addLayout(tools_row)

        # 2. Statistics Card
        stats_frame = QFrame()
        stats_frame.setStyleSheet(f"background-color: {ThemeColors.BG_INPUT}; border-radius: 6px; padding: 6px;")
        stats_layout = QHBoxLayout(stats_frame)
        
        self.lbl_stats_lines = QLabel("Lines: 0")
        self.lbl_stats_travel = QLabel("Travel: 0.0 mm")
        self.lbl_stats_dispense = QLabel("Dispense: 0.0 mm")
        self.lbl_stats_time = QLabel("Est. Time: 00:00")

        for lbl in (self.lbl_stats_lines, self.lbl_stats_travel, self.lbl_stats_dispense, self.lbl_stats_time):
            lbl.setStyleSheet(f"color: {ThemeColors.TEXT_MUTED}; font-size: 11px; font-weight: bold;")
            stats_layout.addWidget(lbl)

        layout.addWidget(stats_frame)

        # 3. G-code Text Preview Editor
        self.txt_gcode = QPlainTextEdit()
        self.txt_gcode.setPlaceholderText("Generate or import G-code to preview program lines here...")
        self.txt_gcode.setLineWrapMode(QPlainTextEdit.NoWrap)
        layout.addWidget(self.txt_gcode, 1)

        # 4. Job Progress Section
        progress_layout = QVBoxLayout()
        
        prog_header = QHBoxLayout()
        self.lbl_progress_status = QLabel("Job Status: Idle")
        self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-weight: bold;")
        self.lbl_progress_time = QLabel("00:00 / 00:00")
        self.lbl_progress_time.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; font-family: monospace;")
        
        prog_header.addWidget(self.lbl_progress_status)
        prog_header.addStretch()
        prog_header.addWidget(self.lbl_progress_time)
        progress_layout.addLayout(prog_header)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(18)
        progress_layout.addWidget(self.progress_bar)

        layout.addLayout(progress_layout)

        # 5. Execution Controls (Dry Run, Execute, Pause, Abort)
        exec_row = QHBoxLayout()

        self.btn_dry_run = QPushButton("🔍 Dry Run (Motor OFF)")
        self.btn_dry_run.setToolTip("Stream motion without turning on powder vibration motor")
        self.btn_dry_run.clicked.connect(self._on_dry_run_clicked)

        self.btn_execute = QPushButton("▶ Execute Dispense")
        self.btn_execute.setObjectName("btn_success")
        self.btn_execute.clicked.connect(self._on_execute_clicked)

        self.btn_pause = QPushButton("⏸ Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)

        self.btn_abort = QPushButton("⏹ Abort")
        self.btn_abort.setObjectName("btn_danger")
        self.btn_abort.setEnabled(False)
        self.btn_abort.clicked.connect(self.abort_job_requested.emit)

        exec_row.addWidget(self.btn_dry_run)
        exec_row.addWidget(self.btn_execute)
        exec_row.addWidget(self.btn_pause)
        exec_row.addWidget(self.btn_abort)
        layout.addLayout(exec_row)

    def set_gcode(self, gcode_text: str, stats: Optional[GCodeStats] = None):
        self.txt_gcode.setPlainText(gcode_text)
        if stats:
            self.lbl_stats_lines.setText(f"Lines: {stats.total_lines}")
            self.lbl_stats_travel.setText(f"Travel: {stats.total_travel_dist_mm:.1f} mm")
            self.lbl_stats_dispense.setText(f"Dispense: {stats.total_dispense_dist_mm:.1f} mm")
            
            mins = int(stats.estimated_time_sec // 60)
            secs = int(stats.estimated_time_sec % 60)
            self.lbl_stats_time.setText(f"Est. Time: {mins:02d}:{secs:02d}")
        else:
            self.lbl_stats_lines.setText("Lines: 0")
            self.lbl_stats_travel.setText("Travel: 0.0 mm")
            self.lbl_stats_dispense.setText("Dispense: 0.0 mm")
            self.lbl_stats_time.setText("Est. Time: 00:00")

    def get_gcode_lines(self) -> List[str]:
        return self.txt_gcode.toPlainText().splitlines()

    def _on_dry_run_clicked(self):
        lines = self.get_gcode_lines()
        if not lines:
            QMessageBox.warning(self, "No G-Code", "Please generate or import G-code first.")
            return
        self.dry_run_requested.emit(lines)

    def _on_execute_clicked(self):
        lines = self.get_gcode_lines()
        if not lines:
            QMessageBox.warning(self, "No G-Code", "Please generate or import G-code first.")
            return
        self.execute_job_requested.emit(lines)

    def _toggle_pause(self):
        if not self._is_paused:
            self.pause_job_requested.emit()
        else:
            self.resume_job_requested.emit()

    def _on_import_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import G-Code File", "", "G-Code Files (*.gcode *.nc *.ngc *.tap);;All Files (*.*)"
        )
        if file_path:
            self.import_gcode_requested.emit(file_path)

    def _on_export_clicked(self):
        gcode = self.txt_gcode.toPlainText()
        if not gcode:
            QMessageBox.warning(self, "No G-Code", "Nothing to export.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export G-Code File", "dispense_job.gcode", "G-Code Files (*.gcode *.nc);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(gcode)
                QMessageBox.information(self, "Export Successful", f"Saved to {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", str(e))

    @Slot(int)
    def on_job_started(self, total_lines: int):
        self._job_start_time = time.time()
        self._is_paused = False
        self.progress_bar.setValue(0)
        self.lbl_progress_status.setText("Job Status: Dispensing in progress...")
        self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.GREEN_SUCCESS}; font-weight: bold;")
        
        self.btn_dry_run.setEnabled(False)
        self.btn_execute.setEnabled(False)
        self.btn_generate.setEnabled(False)
        self.btn_import.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏸ Pause")
        self.btn_abort.setEnabled(True)

    @Slot(int, int, float, float, float)
    def on_job_progress(self, cur_line: int, total_lines: int, pct: float, x: float, y: float):
        self.progress_bar.setValue(int(pct))
        elapsed = time.time() - self._job_start_time
        mins_el = int(elapsed // 60)
        secs_el = int(elapsed % 60)
        
        self.lbl_progress_status.setText(f"Line {cur_line} / {total_lines} ({pct:.1f}%)")
        self.lbl_progress_time.setText(f"Elapsed: {mins_el:02d}:{secs_el:02d}")

    @Slot(bool)
    def on_job_paused(self, is_paused: bool):
        self._is_paused = is_paused
        if is_paused:
            self.lbl_progress_status.setText("Job Status: PAUSED (Motor OFF)")
            self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.AMBER_WARNING}; font-weight: bold;")
            self.btn_pause.setText("▶ Resume")
        else:
            self.lbl_progress_status.setText("Job Status: Dispensing in progress...")
            self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.GREEN_SUCCESS}; font-weight: bold;")
            self.btn_pause.setText("⏸ Pause")

    @Slot(bool)
    def on_job_finished(self, success: bool):
        self.btn_dry_run.setEnabled(True)
        self.btn_execute.setEnabled(True)
        self.btn_generate.setEnabled(True)
        self.btn_import.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_abort.setEnabled(False)

        if success:
            self.progress_bar.setValue(100)
            self.lbl_progress_status.setText("Job Status: Finished Successfully! ✅")
            self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.GREEN_SUCCESS}; font-weight: bold;")
        else:
            self.lbl_progress_status.setText("Job Status: Aborted / Stopped ⚠️")
            self.lbl_progress_status.setStyleSheet(f"color: {ThemeColors.RED_ALERT}; font-weight: bold;")
