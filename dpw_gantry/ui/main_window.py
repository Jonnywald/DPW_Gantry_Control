"""Main Application Window for 2D Powder-Dispensing Gantry Controller."""

from __future__ import annotations
import os
import copy
from typing import Optional, List, Dict
from PySide6.QtCore import Qt, QThread, Slot, QTimer
from PySide6.QtGui import QIcon, QAction, QKeySequence, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QToolBar, QStatusBar, QLabel, QMessageBox,
    QFileDialog, QButtonGroup, QToolButton, QComboBox, QCheckBox,
    QScrollArea, QFrame
)

from ..core.geometry import (
    BaseShape, RectangleShape, CircleShape, PolylineShape,
    PolygonShape, DispenseDotShape, FillMode, Point2D
)
from ..core.gcode_generator import GCodeGenerator, GCodeConfig
from ..core.gcode_parser import GCodeParser
from ..core.serial_worker import SerialWorker, SerialState
from ..core.project_manager import ProjectManager, ProjectData

from .canvas_view import CanvasView, CanvasTool
from .connection_panel import ConnectionPanel
from .manual_control_panel import ManualControlPanel
from .shape_properties_panel import ShapePropertiesPanel
from .gcode_preview_panel import GCodePreviewPanel
from .terminal_panel import TerminalPanel
from .settings_dialog import SettingsDialog
from .help_dialog import HelpDialog
from .theme import DARK_STYLESHEET, ThemeColors


class MainWindow(QMainWindow):
    """Main window integrating canvas, control panels, serial thread, and G-code engine."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DPW Gantry - 2D Powder Dispenser Controller")
        self.resize(1400, 900)
        self.setMinimumSize(900, 600)
        self.setStyleSheet(DARK_STYLESHEET)

        # Core Data
        self.project = ProjectData()
        self.current_project_file: Optional[str] = None
        self.gcode_generator = GCodeGenerator(self.project.gcode_config)
        self.gcode_parser = GCodeParser()
        self.tool_buttons: Dict[CanvasTool, QToolButton] = {}
        self._selected_shape: Optional[BaseShape] = None

        # Serial Thread Initialization
        self._init_serial_thread()

        # Build UI Layout
        self._init_ui()
        self._init_menus()
        self._init_toolbars()
        self._connect_signals()

        # Update initial canvas
        self.canvas_view.sync_shapes(self.project.shapes)
        self.statusBar().showMessage("Ready. Connect to BTT SKR Mini E3 or enable Virtual Board mode.", 5000)

    def _init_serial_thread(self):
        self.serial_thread = QThread(self)
        self.serial_worker = SerialWorker()
        self.serial_worker.moveToThread(self.serial_thread)
        self.serial_thread.started.connect(self.serial_worker.process_loop)
        self.serial_thread.start()

    def _init_ui(self):
        # Central widget with master horizontal splitter
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        master_splitter = QSplitter(Qt.Horizontal)

        # 1. Left Sidebar with bidirectional QScrollArea
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_scroll.setMinimumWidth(260)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)
        left_layout.setSpacing(10)
        
        self.connection_panel = ConnectionPanel()
        self.manual_panel = ManualControlPanel()
        left_layout.addWidget(self.connection_panel)
        left_layout.addWidget(self.manual_panel)
        left_layout.addStretch()
        left_scroll.setWidget(left_widget)
        master_splitter.addWidget(left_scroll)

        # 2. Center Area: Canvas Visualizer (Top) + Terminal (Bottom) Splitter
        center_splitter = QSplitter(Qt.Vertical)
        
        self.canvas_view = CanvasView()
        self.terminal_panel = TerminalPanel()
        
        center_splitter.addWidget(self.canvas_view)
        center_splitter.addWidget(self.terminal_panel)
        center_splitter.setStretchFactor(0, 4)
        center_splitter.setStretchFactor(1, 2)
        
        master_splitter.addWidget(center_splitter)

        # 3. Right Sidebar: Tabbed Inspector & G-Code Preview with QScrollAreas
        right_tabs = QTabWidget()
        right_tabs.setMinimumWidth(300)

        # Tab 1: Shape Inspector (Scrollable both axes)
        inspector_scroll = QScrollArea()
        inspector_scroll.setWidgetResizable(True)
        inspector_scroll.setFrameShape(QFrame.NoFrame)
        inspector_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        inspector_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.shape_properties_panel = ShapePropertiesPanel()
        inspector_scroll.setWidget(self.shape_properties_panel)
        right_tabs.addTab(inspector_scroll, "Inspector")

        # Tab 2: G-Code & Job (Scrollable both axes)
        gcode_scroll = QScrollArea()
        gcode_scroll.setWidgetResizable(True)
        gcode_scroll.setFrameShape(QFrame.NoFrame)
        gcode_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        gcode_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.gcode_preview_panel = GCodePreviewPanel()
        gcode_scroll.setWidget(self.gcode_preview_panel)
        right_tabs.addTab(gcode_scroll, "G-Code & Job")

        self.right_tabs = right_tabs
        master_splitter.addWidget(right_tabs)

        # Set Splitter proportions
        master_splitter.setStretchFactor(0, 0)
        master_splitter.setStretchFactor(1, 1)
        master_splitter.setStretchFactor(2, 0)
        master_splitter.setSizes([300, 740, 360])

        main_layout.addWidget(master_splitter)

        # Status Bar Coordinates Display
        self.lbl_coord_status = QLabel("X: 0.000 mm | Y: 0.000 mm")
        self.lbl_coord_status.setStyleSheet(f"color: {ThemeColors.CYAN_ACCENT}; font-family: monospace; font-weight: bold;")
        self.statusBar().addPermanentWidget(self.lbl_coord_status)

    def _init_menus(self):
        menubar = self.menuBar()

        # File Menu
        file_menu = menubar.addMenu("&File")
        
        act_new = QAction("New Project", self)
        act_new.setShortcut(QKeySequence.New)
        act_new.triggered.connect(self._new_project)
        file_menu.addAction(act_new)

        act_open = QAction("Open Project...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self._open_project)
        file_menu.addAction(act_open)

        act_save = QAction("Save Project", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._save_project)
        file_menu.addAction(act_save)

        act_save_as = QAction("Save Project As...", self)
        act_save_as.setShortcut(QKeySequence.SaveAs)
        act_save_as.triggered.connect(self._save_project_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()

        act_import_gcode = QAction("Import External G-Code...", self)
        act_import_gcode.triggered.connect(self.gcode_preview_panel._on_import_clicked)
        file_menu.addAction(act_import_gcode)

        act_export_gcode = QAction("Export G-Code...", self)
        act_export_gcode.triggered.connect(self.gcode_preview_panel._on_export_clicked)
        file_menu.addAction(act_export_gcode)

        file_menu.addSeparator()

        act_exit = QAction("Exit", self)
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # Edit Menu
        edit_menu = menubar.addMenu("&Edit")
        
        act_clear_shapes = QAction("Clear All Shapes", self)
        act_clear_shapes.triggered.connect(self._clear_all_shapes)
        edit_menu.addAction(act_clear_shapes)

        act_settings = QAction("Settings...", self)
        act_settings.setShortcut(QKeySequence.Preferences)
        act_settings.triggered.connect(self._open_settings)
        edit_menu.addAction(act_settings)

        # View Menu
        view_menu = menubar.addMenu("&View")
        
        act_fit = QAction("Fit Bed in View", self)
        act_fit.setShortcut(QKeySequence("F"))
        act_fit.triggered.connect(self.canvas_view.fit_bed_in_view)
        view_menu.addAction(act_fit)

        # Help Menu
        help_menu = menubar.addMenu("&Help")

        act_quickstart = QAction("Quick Start & User Guide...", self)
        act_quickstart.setShortcut(QKeySequence.HelpContents)  # F1
        act_quickstart.triggered.connect(lambda: self._open_help(0))
        help_menu.addAction(act_quickstart)

        act_gcode_ref = QAction("Supported G-Code Reference...", self)
        act_gcode_ref.triggered.connect(lambda: self._open_help(1))
        help_menu.addAction(act_gcode_ref)

        act_hw_guide = QAction("Hardware & Wiring Guide...", self)
        act_hw_guide.triggered.connect(lambda: self._open_help(2))
        help_menu.addAction(act_hw_guide)

        help_menu.addSeparator()

        act_about = QAction("About DPW Gantry", self)
        act_about.triggered.connect(self._open_about)
        help_menu.addAction(act_about)

    def _init_toolbars(self):
        toolbar = QToolBar("CAD & Drawing Tools")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self.tool_group = QButtonGroup(self)
        self.tool_group.setExclusive(True)

        tools = [
            (CanvasTool.SELECT, "🖱️ Select / Move", True),
            (CanvasTool.RECTANGLE, "⬛ Rectangle", False),
            (CanvasTool.CIRCLE, "⭕ Circle", False),
            (CanvasTool.POLYLINE, "〰️ Polyline", False),
            (CanvasTool.POLYGON, "⬡ Polygon", False),
            (CanvasTool.DISPENSE_DOT, "📍 Dispense Dot", False)
        ]

        self.tool_buttons.clear()
        for tool_enum, label, is_default in tools:
            btn = QToolButton()
            btn.setText(label)
            btn.setCheckable(True)
            btn.setChecked(is_default)
            self.tool_group.addButton(btn)
            toolbar.addWidget(btn)
            self.tool_buttons[tool_enum] = btn
            btn.clicked.connect(lambda chk=False, t=tool_enum: self._on_tool_btn_clicked(t))

        toolbar.addSeparator()

        # Snap to grid toggle & interval
        self.chk_snap = QCheckBox("Snap to Grid:")
        self.chk_snap.setChecked(True)
        self.chk_snap.toggled.connect(self._on_snap_toggled)
        toolbar.addWidget(self.chk_snap)

        self.combo_snap_interval = QComboBox()
        self.combo_snap_interval.addItems(["0.5 mm", "1.0 mm", "2.0 mm", "5.0 mm", "10.0 mm"])
        self.combo_snap_interval.setCurrentText("1.0 mm")
        self.combo_snap_interval.currentTextChanged.connect(self._on_snap_interval_changed)
        toolbar.addWidget(self.combo_snap_interval)

        toolbar.addSeparator()

        # Fit Bed button
        btn_fit = QToolButton()
        btn_fit.setText("🔍 Fit Bed")
        btn_fit.clicked.connect(self.canvas_view.fit_bed_in_view)
        toolbar.addWidget(btn_fit)

        # Clear Canvas button
        btn_clear = QToolButton()
        btn_clear.setText("🗑️ Clear Canvas")
        btn_clear.clicked.connect(self._clear_all_shapes)
        toolbar.addWidget(btn_clear)

    def _connect_signals(self):
        # Canvas -> MainWindow & Panels
        self.canvas_view.mouse_coords_changed.connect(self._on_mouse_coords)
        self.canvas_view.shape_selected.connect(self.shape_properties_panel.set_shape)
        self.canvas_view.shape_selected.connect(self._on_shape_selected)
        self.canvas_view.shape_added.connect(self._on_shape_added)
        self.canvas_view.shape_modified.connect(self._on_shape_modified)
        self.canvas_view.tool_changed.connect(self._sync_active_tool_button)
        self.canvas_view.delete_selected_requested.connect(self._on_delete_key_pressed)

        # Shape Properties Panel -> Canvas
        self.shape_properties_panel.property_changed.connect(self._on_shape_modified)
        self.shape_properties_panel.delete_requested.connect(self._on_shape_deleted)
        self.shape_properties_panel.duplicate_requested.connect(self._on_shape_duplicated)

        # Connection Panel -> Serial Worker
        self.connection_panel.connect_requested.connect(self.serial_worker.connect_serial)
        self.connection_panel.disconnect_requested.connect(self.serial_worker.disconnect_serial)

        # Manual Control & Terminal MDI -> Serial Worker
        self.manual_panel.send_command.connect(self.serial_worker.send_mdi)
        self.manual_panel.emergency_stop_requested.connect(self.serial_worker.emergency_stop)
        self.terminal_panel.send_command.connect(self.serial_worker.send_mdi)

        # G-Code Preview Panel -> Actions
        self.gcode_preview_panel.generate_gcode_requested.connect(self._generate_gcode)
        self.gcode_preview_panel.dry_run_requested.connect(self._execute_dry_run)
        self.gcode_preview_panel.execute_job_requested.connect(self._execute_dispense_job)
        self.gcode_preview_panel.pause_job_requested.connect(self.serial_worker.pause_job)
        self.gcode_preview_panel.resume_job_requested.connect(self.serial_worker.resume_job)
        self.gcode_preview_panel.abort_job_requested.connect(self.serial_worker.abort_job)
        self.gcode_preview_panel.import_gcode_requested.connect(self._import_gcode_file)

        # Serial Worker -> UI Panels
        self.serial_worker.connected.connect(self.connection_panel.on_connected)
        self.serial_worker.disconnected.connect(self.connection_panel.on_disconnected)
        self.serial_worker.state_changed.connect(self.connection_panel.on_state_changed)
        self.serial_worker.connection_error.connect(self.terminal_panel.append_error)

        self.serial_worker.tx_line.connect(self.terminal_panel.append_tx)
        self.serial_worker.rx_line.connect(self.terminal_panel.append_rx)

        self.serial_worker.position_updated.connect(self.manual_panel.update_position)
        self.serial_worker.position_updated.connect(self.canvas_view.set_head_position)

        self.serial_worker.job_started.connect(self.gcode_preview_panel.on_job_started)
        self.serial_worker.job_progress.connect(self.gcode_preview_panel.on_job_progress)
        self.serial_worker.job_paused.connect(self.gcode_preview_panel.on_job_paused)
        self.serial_worker.job_finished.connect(self.gcode_preview_panel.on_job_finished)

    # --- Tool switching helpers ---
    def _on_tool_btn_clicked(self, tool: CanvasTool):
        self.canvas_view.set_active_tool(tool)

    def _sync_active_tool_button(self, tool: CanvasTool):
        if tool in self.tool_buttons:
            self.tool_buttons[tool].setChecked(True)

    def _set_active_cad_tool(self, tool: CanvasTool):
        self.canvas_view.set_active_tool(tool)
        self._sync_active_tool_button(tool)

    # --- Slots & Handlers ---
    @Slot(float, float)
    def _on_mouse_coords(self, x: float, y: float):
        self.lbl_coord_status.setText(f"X: {x:7.3f} mm | Y: {y:7.3f} mm")

    @Slot(bool)
    def _on_snap_toggled(self, checked: bool):
        self.canvas_view.snap_to_grid = checked

    @Slot(str)
    def _on_snap_interval_changed(self, text: str):
        val = float(text.replace("mm", "").strip())
        self.canvas_view.snap_interval_mm = val

    @Slot(object)
    def _on_shape_added(self, shape: BaseShape):
        self.project.shapes.append(shape)
        self.canvas_view.sync_shapes(self.project.shapes)
        self.canvas_view.select_shape_by_id(shape.id)
        self.shape_properties_panel.set_shape(shape)
        self._auto_generate_toolpaths()
        # Automatically switch back to Select/Move tool
        self._set_active_cad_tool(CanvasTool.SELECT)

    @Slot(object)
    def _on_shape_modified(self, shape: BaseShape):
        self.canvas_view.update_shape_visuals()
        self._auto_generate_toolpaths()

    @Slot(object)
    def _on_shape_selected(self, shape):
        """Track the currently selected shape for Delete key handling."""
        self._selected_shape = shape

    @Slot()
    def _on_delete_key_pressed(self):
        """Delete the currently selected shape when Delete/Backspace is pressed."""
        if self._selected_shape is not None:
            self._on_shape_deleted(self._selected_shape)
            self._selected_shape = None

    @Slot(object)
    def _on_shape_deleted(self, shape: BaseShape):
        if shape in self.project.shapes:
            self.project.shapes.remove(shape)
        self.canvas_view.sync_shapes(self.project.shapes)
        self.shape_properties_panel.set_shape(None)
        self._auto_generate_toolpaths()

    @Slot(object)
    def _on_shape_duplicated(self, shape: BaseShape):
        d = shape.to_dict()
        d["id"] = None
        new_shape = type(shape).from_dict(d)
        new_shape.translate(5.0, 5.0)
        new_shape.name = f"{shape.name}_Copy"
        self._on_shape_added(new_shape)

    def _auto_generate_toolpaths(self):
        """Silently compiles G-code to update the 2D toolpath overlay."""
        if self.project.shapes:
            gcode, stats = self.gcode_generator.generate(self.project.shapes, dry_run=False)
            parsed = self.gcode_parser.parse(gcode)
            self.canvas_view.set_toolpath_moves(parsed.moves)
            self.gcode_preview_panel.set_gcode(gcode, stats)
        else:
            self.canvas_view.clear_toolpath_moves()
            self.gcode_preview_panel.set_gcode("")

    def _generate_gcode(self):
        if not self.project.shapes:
            QMessageBox.information(self, "No Shapes", "Please draw or add shapes to the canvas first.")
            return

        gcode, stats = self.gcode_generator.generate(self.project.shapes, dry_run=False)
        self.gcode_preview_panel.set_gcode(gcode, stats)
        
        parsed = self.gcode_parser.parse(gcode)
        self.canvas_view.set_toolpath_moves(parsed.moves)
        
        self.right_tabs.setCurrentIndex(1)  # G-code tab
        self.statusBar().showMessage(f"G-Code generated ({stats.total_lines} lines, est. {int(stats.estimated_time_sec)}s)", 4000)

    def _execute_dry_run(self, lines: List[str]):
        if not self.serial_worker.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a COM port or enable Virtual Board mode.")
            return
        
        gcode, stats = self.gcode_generator.generate(self.project.shapes, dry_run=True)
        self.serial_worker.start_job(gcode.splitlines())

    def _execute_dispense_job(self, lines: List[str]):
        if not self.serial_worker.is_connected():
            QMessageBox.warning(self, "Not Connected", "Please connect to a COM port or enable Virtual Board mode.")
            return

        ret = QMessageBox.question(
            self,
            "Confirm Powder Dispensing",
            "This will start active powder dispensing motion with vibration motor enabled.\n\nEnsure gantry bed is clear. Proceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        if ret == QMessageBox.Yes:
            self.serial_worker.start_job(lines)

    def _import_gcode_file(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                gcode_text = f.read()
            
            parsed = self.gcode_parser.parse(gcode_text)
            self.canvas_view.set_toolpath_moves(parsed.moves)
            self.gcode_preview_panel.set_gcode(gcode_text)
            self.right_tabs.setCurrentIndex(1)  # G-code tab
            self.statusBar().showMessage(f"Loaded external G-Code: {os.path.basename(file_path)}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse G-code file:\n{str(e)}")

    def _clear_all_shapes(self):
        if not self.project.shapes:
            return
        ret = QMessageBox.question(self, "Clear Canvas", "Delete all shapes from canvas?", QMessageBox.Yes | QMessageBox.No)
        if ret == QMessageBox.Yes:
            self.project.shapes.clear()
            self.canvas_view.sync_shapes(self.project.shapes)
            self.shape_properties_panel.set_shape(None)
            self.canvas_view.clear_toolpath_moves()
            self.gcode_preview_panel.set_gcode("")

    def _new_project(self):
        self.project = ProjectData()
        self.current_project_file = None
        self.canvas_view.set_bed_size(self.project.bed_width_mm, self.project.bed_height_mm, self.project.grid_spacing_mm)
        self.canvas_view.sync_shapes(self.project.shapes)
        self.shape_properties_panel.set_shape(None)
        self.canvas_view.clear_toolpath_moves()
        self.gcode_preview_panel.set_gcode("")
        self.setWindowTitle("DPW Gantry - Untitled Project")

    def _open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project File", "", "DPW Gantry Project (*.dpw *.json);;All Files (*.*)"
        )
        if file_path:
            proj = ProjectManager.load_project(file_path)
            if proj:
                self.project = proj
                self.current_project_file = file_path
                self.gcode_generator = GCodeGenerator(self.project.gcode_config)
                self.canvas_view.set_bed_size(self.project.bed_width_mm, self.project.bed_height_mm, self.project.grid_spacing_mm)
                self.canvas_view.sync_shapes(self.project.shapes)
                self.shape_properties_panel.set_shape(None)
                self._auto_generate_toolpaths()
                self.setWindowTitle(f"DPW Gantry - {os.path.basename(file_path)}")
                self.statusBar().showMessage(f"Project loaded: {file_path}", 4000)
            else:
                QMessageBox.critical(self, "Load Error", "Failed to load project file.")

    def _save_project(self):
        if self.current_project_file:
            success = ProjectManager.save_project(self.project, self.current_project_file)
            if success:
                self.statusBar().showMessage(f"Project saved: {self.current_project_file}", 4000)
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save project.")
        else:
            self._save_project_as()

    def _save_project_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project File", "my_dispense_project.dpw", "DPW Gantry Project (*.dpw *.json);;All Files (*.*)"
        )
        if file_path:
            success = ProjectManager.save_project(self.project, file_path)
            if success:
                self.current_project_file = file_path
                self.setWindowTitle(f"DPW Gantry - {os.path.basename(file_path)}")
                self.statusBar().showMessage(f"Project saved to {file_path}", 4000)
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save project.")

    def _open_settings(self):
        dlg = SettingsDialog(
            bed_w=self.project.bed_width_mm,
            bed_h=self.project.bed_height_mm,
            grid_sp=self.project.grid_spacing_mm,
            gcode_config=self.project.gcode_config,
            parent=self
        )
        if dlg.exec():
            self.project.bed_width_mm = dlg.bed_width
            self.project.bed_height_mm = dlg.bed_height
            self.project.grid_spacing_mm = dlg.grid_spacing
            self.project.gcode_config = dlg.gcode_config
            self.gcode_generator = GCodeGenerator(self.project.gcode_config)

            self.canvas_view.set_bed_size(self.project.bed_width_mm, self.project.bed_height_mm, self.project.grid_spacing_mm)
            self._auto_generate_toolpaths()
            self.statusBar().showMessage("Settings updated.", 3000)

    def _open_help(self, tab_index: int = 0):
        dlg = HelpDialog(initial_tab=tab_index, parent=self)
        dlg.exec()

    def _open_about(self):
        QMessageBox.about(
            self,
            "About DPW Gantry Controller",
            "<h3>DPW Gantry Controller v1.0.0</h3>"
            "<p>A precision 2D Powder-Dispensing Gantry control software designed for BigTreeTech SKR Mini E3 and Marlin firmware.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Interactive 2D vector CAD with line hatching and concentric spiral fills</li>"
            "<li>Automatic M106/M107 vibration motor sequencing</li>"
            "<li>Real-time serial streaming with emergency stop</li>"
            "<li>Project file management and G-code export/import</li>"
            "</ul>"
            "<p>© 2026 Powder Dispensing Systems.</p>"
        )

    def closeEvent(self, event):
        """Ensure serial connection and thread terminate gracefully."""
        self.serial_worker.abort_job()
        self.serial_worker.disconnect_serial()
        self.serial_worker.stop_loop()
        self.serial_thread.quit()
        self.serial_thread.wait(1000)
        event.accept()
