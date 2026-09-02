"""Interactive 2D QGraphicsView for bed visualization and vector drawing."""

from __future__ import annotations
import math
from enum import Enum
from typing import List, Optional, Tuple, Dict
from PySide6.QtCore import Qt, QPointF, QRectF, Signal, Slot
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QWheelEvent,
    QMouseEvent, QKeyEvent, QPainterPath
)
from PySide6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QWidget
)

from ..core.geometry import (
    BaseShape, RectangleShape, CircleShape, PolylineShape,
    PolygonShape, DispenseDotShape, Point2D, FillMode
)
from ..core.gcode_parser import ParsedMove
from .canvas_items import (
    BedGraphicsItem, ShapeGraphicsItem, ToolpathOverlayItem,
    DispenserHeadItem
)
from .theme import ThemeColors


class CanvasTool(Enum):
    SELECT = "Select"
    RECTANGLE = "Rectangle"
    CIRCLE = "Circle"
    POLYLINE = "Polyline"
    POLYGON = "Polygon"
    DISPENSE_DOT = "Dispense Dot"


class CanvasView(QGraphicsView):
    """Interactive vector canvas view with zoom, pan, grid snapping, and shape creation."""

    mouse_coords_changed = Signal(float, float)      # x_mm, y_mm
    shape_selected = Signal(object)                  # BaseShape or None
    shape_added = Signal(object)                     # BaseShape
    shape_modified = Signal(object)                  # BaseShape
    tool_changed = Signal(object)                    # CanvasTool
    delete_selected_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setFocusPolicy(Qt.StrongFocus)

        # Rendering options
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform | QPainter.TextAntialiasing)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor(18, 19, 23)))

        # Configuration
        self.bed_width_mm = 177.0
        self.bed_height_mm = 101.0
        self.grid_spacing_mm = 10.0
        self.snap_to_grid = True
        self.snap_interval_mm = 1.0

        # State
        self.current_tool: CanvasTool = CanvasTool.SELECT
        self._is_panning = False
        self._pan_start = QPointF()

        # Drag state for Select/Move
        self._dragged_shape: Optional[BaseShape] = None
        self._drag_start_pos: Optional[Point2D] = None

        # Drawing state
        self._drawing_start_pos: Optional[Point2D] = None
        self._current_mouse_pos: Point2D = Point2D(0, 0)
        self._multi_points: List[Point2D] = []

        # Scene Items
        self._bed_item = BedGraphicsItem(self.bed_width_mm, self.bed_height_mm, self.grid_spacing_mm)
        self._scene.addItem(self._bed_item)

        self._toolpath_item = ToolpathOverlayItem()
        self._scene.addItem(self._toolpath_item)

        self._head_item = DispenserHeadItem()
        self._scene.addItem(self._head_item)

        self._shape_items: Dict[str, ShapeGraphicsItem] = {}

        # Reset initial view to bed
        self.fit_bed_in_view()

    def clear_all(self):
        """Clears all shapes and toolpaths from the canvas safely."""
        self._dragged_shape = None
        self._drag_start_pos = None
        self._drawing_start_pos = None
        self._multi_points.clear()
        for item in self._shape_items.values():
            self._scene.removeItem(item)
        self._shape_items.clear()
        self.clear_toolpath_moves()
        self.viewport().update()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selected_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def set_bed_size(self, width: float, height: float, grid_spacing: float = 10.0):
        self.bed_width_mm = width
        self.bed_height_mm = height
        self.grid_spacing_mm = grid_spacing
        self._scene.removeItem(self._bed_item)
        self._bed_item = BedGraphicsItem(width, height, grid_spacing)
        self._scene.addItem(self._bed_item)
        self.fit_bed_in_view()

    def set_active_tool(self, tool: CanvasTool):
        self.current_tool = tool
        self._drawing_start_pos = None
        self._dragged_shape = None
        self._drag_start_pos = None
        self._multi_points.clear()
        
        if tool == CanvasTool.SELECT:
            self.setCursor(Qt.ArrowCursor)
        else:
            self.setCursor(Qt.CrossCursor)
            self._unselect_all_shapes()

        self.viewport().update()
        self.tool_changed.emit(tool)

    def fit_bed_in_view(self):
        """Zooms and centers view to fit the 200x200mm bed with comfortable margin."""
        margin = 30.0
        rect = QRectF(-margin, -self.bed_height_mm - margin, self.bed_width_mm + 2 * margin, self.bed_height_mm + 2 * margin)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def set_head_position(self, x: float, y: float):
        self._head_item.set_position(x, y)

    def set_toolpath_moves(self, moves: List[ParsedMove]):
        self._toolpath_item.set_moves(moves)

    def clear_toolpath_moves(self):
        self._toolpath_item.clear()

    def _unselect_all_shapes(self):
        for item in self._shape_items.values():
            item.set_selected(False)

    def select_shape_by_id(self, shape_id: Optional[str]):
        self._unselect_all_shapes()
        if shape_id and shape_id in self._shape_items:
            self._shape_items[shape_id].set_selected(True)

    def sync_shapes(self, shapes: List[BaseShape]):
        """Synchronizes graphics items with current shape list cleanly."""
        current_ids = {s.id for s in shapes}
        
        # Remove items no longer present
        to_remove = [sid for sid in self._shape_items if sid not in current_ids]
        for sid in to_remove:
            self._scene.removeItem(self._shape_items[sid])
            del self._shape_items[sid]

        # Add or update
        for shape in shapes:
            if shape.id not in self._shape_items:
                item = ShapeGraphicsItem(shape)
                self._scene.addItem(item)
                self._shape_items[shape.id] = item
            else:
                self._shape_items[shape.id].shape = shape
                self._shape_items[shape.id].prepareGeometryChange()
                self._shape_items[shape.id].update()

    def update_shape_visuals(self):
        for item in self._shape_items.values():
            item.prepareGeometryChange()
            item.update()

    def snap_coordinate(self, val: float) -> float:
        if not self.snap_to_grid or self.snap_interval_mm <= 0:
            return round(val, 3)
        return round(round(val / self.snap_interval_mm) * self.snap_interval_mm, 3)

    def scene_to_gantry_point(self, scene_pos: QPointF) -> Point2D:
        x = self.snap_coordinate(scene_pos.x())
        y = self.snap_coordinate(-scene_pos.y())
        return Point2D(x, y)

    # --- Mouse Events ---
    def wheelEvent(self, event: QWheelEvent):
        zoom_factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
        self.scale(zoom_factor, zoom_factor)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self._is_panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return

        scene_pos = self.mapToScene(event.pos())
        g_pt = self.scene_to_gantry_point(scene_pos)

        if self.current_tool == CanvasTool.SELECT:
            # Hit test for shapes
            clicked_shape: Optional[BaseShape] = None
            # Check in reverse order so top-most shape gets selected
            for sid, item in reversed(list(self._shape_items.items())):
                min_x, min_y, max_x, max_y = item.shape.get_bounds()
                pad = 2.0
                if (min_x - pad <= g_pt.x <= max_x + pad) and (min_y - pad <= g_pt.y <= max_y + pad):
                    clicked_shape = item.shape
                    break

            if clicked_shape:
                self.select_shape_by_id(clicked_shape.id)
                self._dragged_shape = clicked_shape
                self._drag_start_pos = g_pt
                self.shape_selected.emit(clicked_shape)
            else:
                self._unselect_all_shapes()
                self._dragged_shape = None
                self._drag_start_pos = None
                self.shape_selected.emit(None)

        elif self.current_tool == CanvasTool.DISPENSE_DOT:
            if event.button() == Qt.LeftButton:
                dot = DispenseDotShape(x=g_pt.x, y=g_pt.y)
                self.shape_added.emit(dot)

        elif self.current_tool in (CanvasTool.RECTANGLE, CanvasTool.CIRCLE):
            if event.button() == Qt.LeftButton:
                self._drawing_start_pos = g_pt

        elif self.current_tool in (CanvasTool.POLYLINE, CanvasTool.POLYGON):
            if event.button() == Qt.LeftButton:
                self._multi_points.append(g_pt)
                self.viewport().update()
            elif event.button() == Qt.RightButton:
                self._finish_multi_point_shape()

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._is_panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - int(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - int(delta.y()))
            event.accept()
            return

        scene_pos = self.mapToScene(event.pos())
        self._current_mouse_pos = self.scene_to_gantry_point(scene_pos)
        self.mouse_coords_changed.emit(self._current_mouse_pos.x, self._current_mouse_pos.y)

        # Dragging selected shape
        if self.current_tool == CanvasTool.SELECT and self._dragged_shape and self._drag_start_pos:
            dx = self._current_mouse_pos.x - self._drag_start_pos.x
            dy = self._current_mouse_pos.y - self._drag_start_pos.y
            if abs(dx) > 1e-4 or abs(dy) > 1e-4:
                self._dragged_shape.translate(dx, dy)
                self._drag_start_pos = self._current_mouse_pos
                self.update_shape_visuals()
                self.shape_modified.emit(self._dragged_shape)

        elif self.current_tool in (CanvasTool.RECTANGLE, CanvasTool.CIRCLE, CanvasTool.POLYLINE, CanvasTool.POLYGON):
            self.viewport().update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton and self._is_panning:
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor if self.current_tool == CanvasTool.SELECT else Qt.CrossCursor)
            event.accept()
            return

        if self.current_tool == CanvasTool.SELECT:
            if self._dragged_shape:
                shape = self._dragged_shape
                self._dragged_shape = None
                self._drag_start_pos = None
                self.shape_modified.emit(shape)
            return

        if self._drawing_start_pos is not None:
            p1 = self._drawing_start_pos
            p2 = self._current_mouse_pos
            self._drawing_start_pos = None

            new_shape = None
            if self.current_tool == CanvasTool.RECTANGLE:
                x = min(p1.x, p2.x)
                y = min(p1.y, p2.y)
                w = abs(p2.x - p1.x)
                h = abs(p2.y - p1.y)
                if w > 0.5 and h > 0.5:
                    new_shape = RectangleShape(x=x, y=y, width=w, height=h)

            elif self.current_tool == CanvasTool.CIRCLE:
                r = p1.distance_to(p2)
                if r > 0.5:
                    new_shape = CircleShape(cx=p1.x, cy=p1.y, radius=r)

            if new_shape is not None:
                self.shape_added.emit(new_shape)

            self.viewport().update()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if self.current_tool in (CanvasTool.POLYLINE, CanvasTool.POLYGON):
            self._finish_multi_point_shape()

    def _finish_multi_point_shape(self):
        new_shape = None
        if len(self._multi_points) >= 2:
            if self.current_tool == CanvasTool.POLYLINE:
                new_shape = PolylineShape(points=list(self._multi_points))
            elif self.current_tool == CanvasTool.POLYGON and len(self._multi_points) >= 3:
                new_shape = PolygonShape(points=list(self._multi_points))

        self._multi_points.clear()
        self.viewport().update()

        if new_shape is not None:
            self.shape_added.emit(new_shape)

    def drawForeground(self, painter: QPainter, rect: QRectF):
        """Draws temporary creation previews while user is dragging/clicking."""
        super().drawForeground(painter, rect)
        painter.setRenderHint(QPainter.Antialiasing, True)

        preview_pen = QPen(QColor(ThemeColors.AMBER_WARNING), 1.2, Qt.DashLine)
        painter.setPen(preview_pen)
        painter.setBrush(Qt.NoBrush)

        # 1. Rectangle Preview
        if self.current_tool == CanvasTool.RECTANGLE and self._drawing_start_pos:
            p1 = self._drawing_start_pos
            p2 = self._current_mouse_pos
            min_x = min(p1.x, p2.x)
            max_y = max(p1.y, p2.y)
            w = abs(p2.x - p1.x)
            h = abs(p2.y - p1.y)
            painter.drawRect(QRectF(min_x, -max_y, w, h))

        # 2. Circle Preview
        elif self.current_tool == CanvasTool.CIRCLE and self._drawing_start_pos:
            p1 = self._drawing_start_pos
            p2 = self._current_mouse_pos
            r = p1.distance_to(p2)
            painter.drawEllipse(QPointF(p1.x, -p1.y), r, r)
            painter.drawLine(QPointF(p1.x, -p1.y), QPointF(p2.x, -p2.y))

        # 3. Polyline / Polygon Preview
        elif self.current_tool in (CanvasTool.POLYLINE, CanvasTool.POLYGON) and self._multi_points:
            path = QPainterPath()
            path.moveTo(self._multi_points[0].x, -self._multi_points[0].y)
            for pt in self._multi_points[1:]:
                path.lineTo(pt.x, -pt.y)
            path.lineTo(self._current_mouse_pos.x, -self._current_mouse_pos.y)
            
            if self.current_tool == CanvasTool.POLYGON and len(self._multi_points) >= 2:
                path.lineTo(self._multi_points[0].x, -self._multi_points[0].y)

            painter.drawPath(path)
            
            # Vertex handles
            painter.setBrush(QBrush(QColor(ThemeColors.AMBER_WARNING)))
            for pt in self._multi_points:
                painter.drawEllipse(QPointF(pt.x, -pt.y), 2.5, 2.5)
