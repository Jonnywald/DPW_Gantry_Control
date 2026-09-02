"""Shape Inspector and Parameter Editing Panel."""

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox,
    QPushButton, QGroupBox, QStackedWidget
)
from ..core.geometry import (
    BaseShape, RectangleShape, CircleShape, PolylineShape,
    PolygonShape, DispenseDotShape, FillMode, ShapeType
)
from .theme import ThemeColors


class ShapePropertiesPanel(QGroupBox):
    """Panel for inspecting and editing selected shape properties."""

    property_changed = Signal(object)  # BaseShape
    delete_requested = Signal(object)  # BaseShape
    duplicate_requested = Signal(object)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__("Shape Inspector & Dispenser Parameters", parent)
        self._current_shape: Optional[BaseShape] = None
        self._is_updating_ui = False
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self.lbl_no_selection = QLabel("No shape selected.\nClick a shape on the bed to edit its properties.")
        self.lbl_no_selection.setAlignment(Qt.AlignCenter)
        self.lbl_no_selection.setStyleSheet(f"color: {ThemeColors.TEXT_SECONDARY}; padding: 20px;")
        layout.addWidget(self.lbl_no_selection)

        # Container for shape editor
        self.editor_container = QWidget()
        editor_layout = QVBoxLayout(self.editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.setSpacing(10)

        # 1. Identity & Geometry Form
        geom_group = QGroupBox("Geometry")
        geom_form = QFormLayout(geom_group)

        self.txt_name = QLineEdit()
        self.txt_name.textChanged.connect(self._on_name_changed)
        geom_form.addRow("Name:", self.txt_name)

        self.lbl_type = QLabel("Type:")
        geom_form.addRow("Type:", self.lbl_type)

        # Dynamic dimension spinboxes
        self.spin_x = QDoubleSpinBox()
        self.spin_x.setRange(-500.0, 500.0)
        self.spin_x.setSingleStep(1.0)
        self.spin_x.setDecimals(2)
        self.spin_x.valueChanged.connect(self._on_geometry_changed)
        geom_form.addRow("X Pos (mm):", self.spin_x)

        self.spin_y = QDoubleSpinBox()
        self.spin_y.setRange(-500.0, 500.0)
        self.spin_y.setSingleStep(1.0)
        self.spin_y.setDecimals(2)
        self.spin_y.valueChanged.connect(self._on_geometry_changed)
        geom_form.addRow("Y Pos (mm):", self.spin_y)

        # Dimensions: Width & Height for Rectangle
        self.spin_w = QDoubleSpinBox()
        self.spin_w.setRange(0.1, 500.0)
        self.spin_w.setValue(40.0)
        self.spin_w.valueChanged.connect(self._on_geometry_changed)
        self.lbl_w = QLabel("Width (mm):")
        geom_form.addRow(self.lbl_w, self.spin_w)

        self.spin_h = QDoubleSpinBox()
        self.spin_h.setRange(0.1, 500.0)
        self.spin_h.setValue(30.0)
        self.spin_h.valueChanged.connect(self._on_geometry_changed)
        self.lbl_h = QLabel("Height (mm):")
        geom_form.addRow(self.lbl_h, self.spin_h)

        # Radius for Circle
        self.spin_r = QDoubleSpinBox()
        self.spin_r.setRange(0.1, 250.0)
        self.spin_r.setValue(20.0)
        self.spin_r.valueChanged.connect(self._on_geometry_changed)
        self.lbl_r = QLabel("Radius (mm):")
        geom_form.addRow(self.lbl_r, self.spin_r)

        editor_layout.addWidget(geom_group)

        # 2. Fill Options Form
        self.fill_group = QGroupBox("Fill & Hatching Pattern")
        fill_form = QFormLayout(self.fill_group)

        self.combo_fill_mode = QComboBox()
        for mode in FillMode:
            self.combo_fill_mode.addItem(mode.value, mode)
        self.combo_fill_mode.currentIndexChanged.connect(self._on_fill_mode_changed)
        fill_form.addRow("Fill Mode:", self.combo_fill_mode)

        self.spin_stepover = QDoubleSpinBox()
        self.spin_stepover.setRange(0.1, 50.0)
        self.spin_stepover.setSingleStep(0.2)
        self.spin_stepover.setValue(1.0)
        self.spin_stepover.setDecimals(2)
        self.spin_stepover.valueChanged.connect(self._on_fill_params_changed)
        fill_form.addRow("Step-over (mm):", self.spin_stepover)

        self.spin_hatch_angle = QDoubleSpinBox()
        self.spin_hatch_angle.setRange(0.0, 360.0)
        self.spin_hatch_angle.setSingleStep(15.0)
        self.spin_hatch_angle.setValue(45.0)
        self.spin_hatch_angle.valueChanged.connect(self._on_fill_params_changed)
        self.lbl_angle = QLabel("Hatch Angle (°):")
        fill_form.addRow(self.lbl_angle, self.spin_hatch_angle)

        editor_layout.addWidget(self.fill_group)

        # 3. Dispenser & Feedrate Parameters
        disp_group = QGroupBox("Dispense & Powder Control")
        disp_form = QFormLayout(disp_group)

        self.spin_motor_pwm = QSpinBox()
        self.spin_motor_pwm.setRange(0, 255)
        self.spin_motor_pwm.setValue(255)
        self.spin_motor_pwm.valueChanged.connect(self._on_dispenser_params_changed)
        disp_form.addRow("Vibration PWM:", self.spin_motor_pwm)

        self.spin_feedrate = QDoubleSpinBox()
        self.spin_feedrate.setRange(10.0, 10000.0)
        self.spin_feedrate.setSingleStep(50.0)
        self.spin_feedrate.setValue(500.0)
        self.spin_feedrate.valueChanged.connect(self._on_dispenser_params_changed)
        disp_form.addRow("Dispense Feed (mm/min):", self.spin_feedrate)

        self.spin_dwell = QSpinBox()
        self.spin_dwell.setRange(0, 5000)
        self.spin_dwell.setSingleStep(50)
        self.spin_dwell.setValue(100)
        self.spin_dwell.valueChanged.connect(self._on_dispenser_params_changed)
        disp_form.addRow("Pre-dwell (ms):", self.spin_dwell)

        editor_layout.addWidget(disp_group)

        # 4. Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.clicked.connect(self._duplicate)

        self.btn_delete = QPushButton("Delete Shape")
        self.btn_delete.setObjectName("btn_danger")
        self.btn_delete.clicked.connect(self._delete)

        btn_layout.addWidget(self.btn_duplicate)
        btn_layout.addWidget(self.btn_delete)
        editor_layout.addLayout(btn_layout)

        layout.addWidget(self.editor_container)
        self.editor_container.setVisible(False)

    @Slot(object)
    def set_shape(self, shape: Optional[BaseShape]):
        self._current_shape = shape
        if shape is None:
            self.lbl_no_selection.setVisible(True)
            self.editor_container.setVisible(False)
            return

        self._is_updating_ui = True
        self.lbl_no_selection.setVisible(False)
        self.editor_container.setVisible(True)

        self.txt_name.setText(shape.name)
        self.lbl_type.setText(shape.shape_type.value)

        # Populate coordinates
        if isinstance(shape, RectangleShape):
            self.spin_x.setValue(shape.x)
            self.spin_y.setValue(shape.y)
            self.spin_w.setValue(shape.width)
            self.spin_h.setValue(shape.height)
            self.lbl_w.setVisible(True)
            self.spin_w.setVisible(True)
            self.lbl_h.setVisible(True)
            self.spin_h.setVisible(True)
            self.lbl_r.setVisible(False)
            self.spin_r.setVisible(False)
            self.fill_group.setVisible(True)
        elif isinstance(shape, CircleShape):
            self.spin_x.setValue(shape.cx)
            self.spin_y.setValue(shape.cy)
            self.spin_r.setValue(shape.radius)
            self.lbl_w.setVisible(False)
            self.spin_w.setVisible(False)
            self.lbl_h.setVisible(False)
            self.spin_h.setVisible(False)
            self.lbl_r.setVisible(True)
            self.spin_r.setVisible(True)
            self.fill_group.setVisible(True)
        elif isinstance(shape, (PolylineShape, PolygonShape)):
            min_x, min_y, _, _ = shape.get_bounds()
            self.spin_x.setValue(min_x)
            self.spin_y.setValue(min_y)
            self.lbl_w.setVisible(False)
            self.spin_w.setVisible(False)
            self.lbl_h.setVisible(False)
            self.spin_h.setVisible(False)
            self.lbl_r.setVisible(False)
            self.spin_r.setVisible(False)
            self.fill_group.setVisible(isinstance(shape, PolygonShape))
        elif isinstance(shape, DispenseDotShape):
            self.spin_x.setValue(shape.x)
            self.spin_y.setValue(shape.y)
            self.lbl_w.setVisible(False)
            self.spin_w.setVisible(False)
            self.lbl_h.setVisible(False)
            self.spin_h.setVisible(False)
            self.lbl_r.setVisible(False)
            self.spin_r.setVisible(False)
            self.fill_group.setVisible(False)

        # Fill Settings
        idx = self.combo_fill_mode.findData(shape.fill_mode)
        if idx != -1:
            self.combo_fill_mode.setCurrentIndex(idx)
        self.spin_stepover.setValue(shape.stepover_mm)
        self.spin_hatch_angle.setValue(shape.hatch_angle_deg)

        # Dispenser Settings
        self.spin_motor_pwm.setValue(shape.motor_pwm)
        self.spin_feedrate.setValue(shape.dispense_feedrate)
        self.spin_dwell.setValue(shape.dwell_ms)

        self._is_updating_ui = False

    def _on_name_changed(self, text: str):
        if self._is_updating_ui or not self._current_shape:
            return
        self._current_shape.name = text
        self.property_changed.emit(self._current_shape)

    def _on_geometry_changed(self):
        if self._is_updating_ui or not self._current_shape:
            return

        if isinstance(self._current_shape, RectangleShape):
            self._current_shape.x = self.spin_x.value()
            self._current_shape.y = self.spin_y.value()
            self._current_shape.width = self.spin_w.value()
            self._current_shape.height = self.spin_h.value()
        elif isinstance(self._current_shape, CircleShape):
            self._current_shape.cx = self.spin_x.value()
            self._current_shape.cy = self.spin_y.value()
            self._current_shape.radius = self.spin_r.value()
        elif isinstance(self._current_shape, DispenseDotShape):
            self._current_shape.x = self.spin_x.value()
            self._current_shape.y = self.spin_y.value()

        self.property_changed.emit(self._current_shape)

    def _on_fill_mode_changed(self, index: int):
        if self._is_updating_ui or not self._current_shape:
            return
        mode = self.combo_fill_mode.currentData()
        self._current_shape.fill_mode = mode
        self.property_changed.emit(self._current_shape)

    def _on_fill_params_changed(self):
        if self._is_updating_ui or not self._current_shape:
            return
        self._current_shape.stepover_mm = self.spin_stepover.value()
        self._current_shape.hatch_angle_deg = self.spin_hatch_angle.value()
        self.property_changed.emit(self._current_shape)

    def _on_dispenser_params_changed(self):
        if self._is_updating_ui or not self._current_shape:
            return
        self._current_shape.motor_pwm = self.spin_motor_pwm.value()
        self._current_shape.dispense_feedrate = self.spin_feedrate.value()
        self._current_shape.dwell_ms = self.spin_dwell.value()
        self.property_changed.emit(self._current_shape)

    def _duplicate(self):
        if self._current_shape:
            self.duplicate_requested.emit(self._current_shape)

    def _delete(self):
        if self._current_shape:
            self.delete_requested.emit(self._current_shape)
