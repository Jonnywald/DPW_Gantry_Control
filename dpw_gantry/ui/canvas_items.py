"""Custom QGraphicsItem components for 2D Bed Visualizer, Shapes, and Live Toolhead."""

from __future__ import annotations
import math
from typing import Optional, List
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPainterPath
)
from PySide6.QtWidgets import (
    QGraphicsItem, QStyleOptionGraphicsItem, QWidget
)
from ..core.geometry import (
    BaseShape, RectangleShape, CircleShape, PolylineShape,
    PolygonShape, DispenseDotShape, FillMode, Point2D
)
from ..core.gcode_parser import ParsedMove
from .theme import ThemeColors


class BedGraphicsItem(QGraphicsItem):
    """Draws the build bed boundary, mm grid, and origin."""

    def __init__(self, width_mm: float = 177.0, height_mm: float = 101.0, grid_spacing: float = 10.0):
        super().__init__()
        self.width_mm = width_mm
        self.height_mm = height_mm
        self.grid_spacing = grid_spacing
        self.setZValue(-100)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def boundingRect(self) -> QRectF:
        margin = 15.0
        return QRectF(-margin, -self.height_mm - margin, self.width_mm + 2 * margin, self.height_mm + 2 * margin)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.Antialiasing, False)

        # 1. Bed Background
        bed_rect = QRectF(0, -self.height_mm, self.width_mm, self.height_mm)
        painter.fillRect(bed_rect, ThemeColors.CANVAS_BED_BG)

        # 2. Minor Grid (2mm increments)
        if self.grid_spacing >= 5.0:
            minor_pen = QPen(ThemeColors.CANVAS_GRID_MINOR, 0.5)
            painter.setPen(minor_pen)
            
            x = 2.0
            while x < self.width_mm:
                if abs(x % self.grid_spacing) > 1e-4:
                    painter.drawLine(QPointF(x, 0), QPointF(x, -self.height_mm))
                x += 2.0
            
            y = 2.0
            while y < self.height_mm:
                if abs(y % self.grid_spacing) > 1e-4:
                    painter.drawLine(QPointF(0, -y), QPointF(self.width_mm, -y))
                y += 2.0

        # 3. Major Grid
        major_pen = QPen(ThemeColors.CANVAS_GRID_MAJOR, 0.8)
        painter.setPen(major_pen)
        
        x = self.grid_spacing
        while x <= self.width_mm:
            painter.drawLine(QPointF(x, 0), QPointF(x, -self.height_mm))
            x += self.grid_spacing

        y = self.grid_spacing
        while y <= self.height_mm:
            painter.drawLine(QPointF(0, -y), QPointF(self.width_mm, -y))
            y += self.grid_spacing

        # 4. Bed Outer Border
        border_pen = QPen(QColor(98, 114, 164, 255), 1.5)
        painter.setPen(border_pen)
        painter.drawRect(bed_rect)

        # 5. Origin Indicator (0,0) at Lower Left
        painter.setRenderHint(QPainter.Antialiasing, True)
        origin_pen = QPen(ThemeColors.CANVAS_ORIGIN, 2.0)
        painter.setPen(origin_pen)
        painter.drawLine(QPointF(-6, 0), QPointF(15, 0))    # +X Axis
        painter.drawLine(QPointF(0, 6), QPointF(0, -15))    # +Y Axis

        # Axis arrowheads
        painter.drawLine(QPointF(15, 0), QPointF(11, -3))
        painter.drawLine(QPointF(15, 0), QPointF(11, 3))
        painter.drawLine(QPointF(0, -15), QPointF(-3, -11))
        painter.drawLine(QPointF(0, -15), QPointF(3, -11))

        # Origin circle
        painter.setBrush(QBrush(ThemeColors.CANVAS_ORIGIN))
        painter.drawEllipse(QPointF(0, 0), 2.5, 2.5)


class ShapeGraphicsItem(QGraphicsItem):
    """
    Direct visual representation of a vector shape on the bed scene.
    Coordinates map directly to Gantry (X, -Y) in scene space.
    """

    def __init__(self, shape: BaseShape):
        super().__init__()
        self.shape = shape
        self.setZValue(50)
        self.setAcceptedMouseButtons(Qt.NoButton)  # CanvasView handles hit-testing and dragging cleanly
        self._is_selected = False

    def set_selected(self, selected: bool):
        self.prepareGeometryChange()
        self._is_selected = selected
        self.shape.is_selected = selected
        self.update()

    def boundingRect(self) -> QRectF:
        min_x, min_y, max_x, max_y = self.shape.get_bounds()
        pad = 6.0
        return QRectF(min_x - pad, -max_y - pad, max(1.0, (max_x - min_x) + 2 * pad), max(1.0, (max_y - min_y) + 2 * pad))

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        if not self.shape.is_visible:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)
        is_sel = self._is_selected or self.shape.is_selected

        # 1. Draw Fill Pattern (Hatch or Spiral)
        if self.shape.is_closed() and self.shape.fill_mode != FillMode.OUTLINE_ONLY:
            fill_pen = QPen(
                ThemeColors.PATH_FILL_SPIRAL if self.shape.fill_mode == FillMode.INWARD_SPIRAL else ThemeColors.PATH_FILL_HATCH,
                0.8
            )
            painter.setPen(fill_pen)

            toolpaths = self.shape.generate_toolpaths()
            for tp in toolpaths[1:]:
                if len(tp.points) > 1:
                    path = QPainterPath()
                    path.moveTo(tp.points[0].x, -tp.points[0].y)
                    for pt in tp.points[1:]:
                        path.lineTo(pt.x, -pt.y)
                    painter.drawPath(path)

        # 2. Draw Outline
        outline_pts = self.shape.get_outline_points()
        if outline_pts:
            outline_color = QColor(ThemeColors.CYAN_ACCENT) if not is_sel else QColor(ThemeColors.GREEN_SUCCESS)
            pen_width = 2.0 if is_sel else 1.2
            
            outline_pen = QPen(outline_color, pen_width)
            painter.setPen(outline_pen)

            if isinstance(self.shape, DispenseDotShape):
                painter.setBrush(QBrush(outline_color))
                painter.drawEllipse(QPointF(self.shape.x, -self.shape.y), 3.0, 3.0)
                painter.drawLine(QPointF(self.shape.x - 6, -self.shape.y), QPointF(self.shape.x + 6, -self.shape.y))
                painter.drawLine(QPointF(self.shape.x, -self.shape.y - 6), QPointF(self.shape.x, -self.shape.y + 6))
            else:
                path = QPainterPath()
                path.moveTo(outline_pts[0].x, -outline_pts[0].y)
                for pt in outline_pts[1:]:
                    path.lineTo(pt.x, -pt.y)
                if self.shape.is_closed() and len(outline_pts) > 2:
                    path.closeSubpath()
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(path)

        # 3. Draw Selection Bounding Box with Corner Grips
        if is_sel:
            sel_pen = QPen(QColor(ThemeColors.GREEN_SUCCESS), 1.0, Qt.DashLine)
            painter.setPen(sel_pen)
            min_x, min_y, max_x, max_y = self.shape.get_bounds()
            w = max_x - min_x
            h = max_y - min_y
            sel_rect = QRectF(min_x, -max_y, w, h)
            painter.drawRect(sel_rect)

            # Draw 4 corner handles
            painter.setBrush(QBrush(QColor(ThemeColors.GREEN_SUCCESS)))
            painter.setPen(Qt.NoPen)
            handle_size = 4.0
            corners = [
                QPointF(min_x, -min_y),
                QPointF(max_x, -min_y),
                QPointF(max_x, -max_y),
                QPointF(min_x, -max_y)
            ]
            for c in corners:
                painter.drawRect(QRectF(c.x() - handle_size/2, c.y() - handle_size/2, handle_size, handle_size))


class ToolpathOverlayItem(QGraphicsItem):
    """Renders parsed G-code toolpaths with color-coded moves (G0 rapid vs G1 dispense)."""

    def __init__(self):
        super().__init__()
        self.moves: List[ParsedMove] = []
        self.setZValue(10)
        self.setAcceptedMouseButtons(Qt.NoButton)

    def set_moves(self, moves: List[ParsedMove]):
        self.prepareGeometryChange()
        self.moves = moves
        self.update()

    def clear(self):
        self.prepareGeometryChange()
        self.moves = []
        self.update()

    def boundingRect(self) -> QRectF:
        if not self.moves:
            return QRectF(0, 0, 0, 0)
        xs = [m.start_pos.x for m in self.moves] + [m.end_pos.x for m in self.moves]
        ys = [m.start_pos.y for m in self.moves] + [m.end_pos.y for m in self.moves]
        if not xs or not ys:
            return QRectF(0, 0, 0, 0)
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        return QRectF(min_x - 5, -max_y - 5, (max_x - min_x) + 10, (max_y - min_y) + 10)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        if not self.moves:
            return

        painter.setRenderHint(QPainter.Antialiasing, True)

        rapid_pen = QPen(ThemeColors.PATH_RAPID_TRAVEL, 1.0, Qt.DashLine)
        dispense_pen = QPen(QColor(ThemeColors.BLUE_ACCENT), 1.6, Qt.SolidLine)
        motor_off_feed_pen = QPen(QColor(158, 163, 192, 180), 1.2, Qt.SolidLine)

        for m in self.moves:
            p1 = QPointF(m.start_pos.x, -m.start_pos.y)
            p2 = QPointF(m.end_pos.x, -m.end_pos.y)

            if m.command == "G0":
                painter.setPen(rapid_pen)
                painter.drawLine(p1, p2)
            elif m.command == "G1":
                if m.motor_on:
                    painter.setPen(dispense_pen)
                else:
                    painter.setPen(motor_off_feed_pen)
                painter.drawLine(p1, p2)
            elif m.command == "G4":
                painter.setBrush(QBrush(QColor(ThemeColors.AMBER_WARNING)))
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(p1, 2.0, 2.0)


class DispenserHeadItem(QGraphicsItem):
    """Renders real-time position crosshair and nozzle ring of the gantry."""

    def __init__(self):
        super().__init__()
        self.setZValue(200)
        self.setAcceptedMouseButtons(Qt.NoButton)
        self._x = 0.0
        self._y = 0.0

    def set_position(self, x: float, y: float):
        self.prepareGeometryChange()
        self._x = x
        self._y = y
        self.setPos(self._x, -self._y)
        self.update()

    def boundingRect(self) -> QRectF:
        r = 12.0
        return QRectF(-r, -r, 2 * r, 2 * r)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = None):
        painter.setRenderHint(QPainter.Antialiasing, True)

        # Outer glowing ring
        outer_pen = QPen(ThemeColors.PATH_NOZZLE_HEAD, 1.8)
        painter.setPen(outer_pen)
        painter.setBrush(QBrush(QColor(80, 250, 123, 50)))
        painter.drawEllipse(QPointF(0, 0), 6.0, 6.0)

        # Center dot
        painter.setBrush(QBrush(ThemeColors.PATH_NOZZLE_HEAD))
        painter.drawEllipse(QPointF(0, 0), 2.0, 2.0)

        # Crosshair lines
        ch_pen = QPen(ThemeColors.PATH_NOZZLE_HEAD, 1.2)
        painter.setPen(ch_pen)
        painter.drawLine(QPointF(-10, 0), QPointF(-4, 0))
        painter.drawLine(QPointF(4, 0), QPointF(10, 0))
        painter.drawLine(QPointF(0, -10), QPointF(0, -4))
        painter.drawLine(QPointF(0, 4), QPointF(0, 10))
