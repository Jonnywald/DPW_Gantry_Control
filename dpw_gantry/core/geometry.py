"""Computational geometry and vector fill algorithms for 2D powder dispensing."""

from __future__ import annotations
import math
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Any


class FillMode(Enum):
    OUTLINE_ONLY = "Outline Only"
    LINE_HATCH = "Line Hatching"
    CROSS_HATCH = "Cross Hatching"
    INWARD_SPIRAL = "Inward Spiral"


class ShapeType(Enum):
    POLYLINE = "Polyline"
    RECTANGLE = "Rectangle"
    CIRCLE = "Circle"
    POLYGON = "Polygon"
    DISPENSE_DOT = "Dispense Dot"


@dataclass
class Point2D:
    x: float
    y: float

    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

    def distance_to(self, other: Point2D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def rotated(self, angle_rad: float, origin: Point2D = None) -> Point2D:
        ox = origin.x if origin else 0.0
        oy = origin.y if origin else 0.0
        dx = self.x - ox
        dy = self.y - oy
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Point2D(
            ox + dx * cos_a - dy * sin_a,
            oy + dx * sin_a + dy * cos_a
        )


@dataclass
class ToolpathSegment:
    """Represents a continuous move in the toolpath."""
    points: List[Point2D]
    is_dispense: bool = True
    feedrate: Optional[float] = None
    motor_pwm: Optional[int] = None
    dwell_ms: int = 0  # Pre-dispense dwell time in ms (G4 P...)


def segment_intersection(p1: Point2D, p2: Point2D, p3: Point2D, p4: Point2D) -> Optional[Point2D]:
    """Finds intersection point between line segment p1-p2 and p3-p4 if it exists."""
    d = (p2.x - p1.x) * (p4.y - p3.y) - (p2.y - p1.y) * (p4.x - p3.x)
    if abs(d) < 1e-9:
        return None  # Parallel
    
    u = ((p3.x - p1.x) * (p4.y - p3.y) - (p3.y - p1.y) * (p4.x - p3.x)) / d
    v = ((p3.x - p1.x) * (p2.y - p1.y) - (p3.y - p1.y) * (p2.x - p1.x)) / d
    
    if 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0:
        return Point2D(p1.x + u * (p2.x - p1.x), p1.y + u * (p2.y - p1.y))
    return None


def horizontal_line_polygon_intersections(poly: List[Point2D], y_val: float) -> List[float]:
    """Find all x coordinates where horizontal line y=y_val intersects the closed polygon."""
    x_ints = []
    n = len(poly)
    if n < 3:
        return []

    for i in range(n):
        p1 = poly[i]
        p2 = poly[(i + 1) % n]
        
        # Check if segment crosses y_val
        if (p1.y <= y_val < p2.y) or (p2.y <= y_val < p1.y):
            dy = p2.y - p1.y
            if abs(dy) > 1e-9:
                t = (y_val - p1.y) / dy
                x_val = p1.x + t * (p2.x - p1.x)
                x_ints.append(x_val)
        elif abs(p1.y - y_val) < 1e-9 and abs(p2.y - y_val) < 1e-9:
            # Collinear horizontal segment: include both endpoints
            x_ints.append(p1.x)
            x_ints.append(p2.x)

    x_ints.sort()
    # Filter duplicates within tolerance
    filtered = []
    for x in x_ints:
        if not filtered or abs(x - filtered[-1]) > 1e-5:
            filtered.append(x)
    return filtered


def compute_hatch_lines(
    polygon_vertices: List[Point2D],
    stepover_mm: float,
    angle_deg: float,
    zig_zag: bool = True
) -> List[List[Point2D]]:
    """
    Computes scanline hatch lines inside a closed polygon.
    Returns list of line segments (each is [Point2D_start, Point2D_end]).
    """
    if len(polygon_vertices) < 3 or stepover_mm <= 0:
        return []

    # 1. Rotate polygon so scanlines are horizontal (angle 0)
    angle_rad = math.radians(angle_deg)
    rotated_poly = [p.rotated(-angle_rad) for p in polygon_vertices]

    # 2. Find min and max Y in rotated frame
    ys = [p.y for p in rotated_poly]
    min_y = min(ys)
    max_y = max(ys)

    if max_y - min_y < 1e-4:
        return []

    # Calculate scanline Y positions with half stepover margin
    start_y = min_y + stepover_mm * 0.5
    current_y = start_y
    scan_lines: List[List[Point2D]] = []
    line_index = 0

    while current_y < max_y:
        x_intersects = horizontal_line_polygon_intersections(rotated_poly, current_y)
        # Pair intersections: [x0, x1], [x2, x3], ...
        for i in range(0, len(x_intersects) - 1, 2):
            x0, x1 = x_intersects[i], x_intersects[i + 1]
            if x1 - x0 > 1e-4:
                # Rotate back to original coordinate system
                p_start = Point2D(x0, current_y).rotated(angle_rad)
                p_end = Point2D(x1, current_y).rotated(angle_rad)

                # Alternate direction for zig-zag dispensing
                if zig_zag and (line_index % 2 == 1):
                    scan_lines.append([p_end, p_start])
                else:
                    scan_lines.append([p_start, p_end])

        current_y += stepover_mm
        line_index += 1

    return scan_lines


def polygon_centroid(vertices: List[Point2D]) -> Point2D:
    """Computes centroid of a polygon."""
    n = len(vertices)
    if n == 0:
        return Point2D(0, 0)
    if n == 1:
        return Point2D(vertices[0].x, vertices[0].y)
    
    signed_area = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(n):
        p0 = vertices[i]
        p1 = vertices[(i + 1) % n]
        a = p0.x * p1.y - p1.x * p0.y
        signed_area += a
        cx += (p0.x + p1.x) * a
        cy += (p0.y + p1.y) * a
    
    signed_area *= 0.5
    if abs(signed_area) < 1e-9:
        # Fallback to arithmetic mean
        return Point2D(sum(p.x for p in vertices) / n, sum(p.y for p in vertices) / n)
    
    cx = cx / (6.0 * signed_area)
    cy = cy / (6.0 * signed_area)
    return Point2D(cx, cy)


def compute_concentric_spiral_fill(
    polygon_vertices: List[Point2D],
    stepover_mm: float
) -> List[List[Point2D]]:
    """
    Computes concentric inward offset loops / continuous spiral fill for a polygon.
    Returns list of paths.
    """
    if len(polygon_vertices) < 3 or stepover_mm <= 0:
        return []

    center = polygon_centroid(polygon_vertices)
    
    # Calculate approximate radius / max distance from center
    max_dist = max(p.distance_to(center) for p in polygon_vertices)
    if max_dist <= stepover_mm * 0.5:
        return []

    num_shells = int(math.floor(max_dist / stepover_mm))
    loops: List[List[Point2D]] = []

    for s in range(1, num_shells + 1):
        scale = max(0.01, 1.0 - (s * stepover_mm) / max_dist)
        if scale <= 0.02:
            break
        offset_poly = [
            Point2D(center.x + (p.x - center.x) * scale, center.y + (p.y - center.y) * scale)
            for p in polygon_vertices
        ]
        # Close loop
        if offset_poly:
            offset_poly.append(Point2D(offset_poly[0].x, offset_poly[0].y))
            loops.append(offset_poly)

    return loops


@dataclass
class BaseShape:
    """Base class for all canvas vector shapes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Shape"
    shape_type: ShapeType = ShapeType.RECTANGLE
    fill_mode: FillMode = FillMode.OUTLINE_ONLY
    
    # Fill settings
    hatch_angle_deg: float = 45.0
    stepover_mm: float = 1.0
    
    # Powder Dispenser & Motion Settings
    motor_pwm: int = 255  # 0 to 255 (M106 S<pwm>)
    dispense_feedrate: float = 500.0  # mm/min (G1 F<feedrate>)
    dwell_ms: int = 100  # Dwell before starting dispense move
    
    # Visibility and Selection
    is_visible: bool = True
    is_selected: bool = False

    def get_outline_points(self) -> List[Point2D]:
        """Returns ordered boundary points of the shape."""
        raise NotImplementedError

    def is_closed(self) -> bool:
        return True

    def get_bounds(self) -> Tuple[float, float, float, float]:
        """Returns (min_x, min_y, max_x, max_y)."""
        pts = self.get_outline_points()
        if not pts:
            return (0.0, 0.0, 0.0, 0.0)
        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        return (min(xs), min(ys), max(xs), max(ys))

    def translate(self, dx: float, dy: float):
        raise NotImplementedError

    def generate_toolpaths(self) -> List[ToolpathSegment]:
        """Generates all dispensing toolpath segments (outline + fills)."""
        segments: List[ToolpathSegment] = []
        outline = self.get_outline_points()

        # 1. Outline segment
        if outline:
            if self.is_closed() and (len(outline) > 1 and outline[0] != outline[-1]):
                closed_outline = outline + [Point2D(outline[0].x, outline[0].y)]
            else:
                closed_outline = outline
            
            segments.append(ToolpathSegment(
                points=closed_outline,
                is_dispense=True,
                feedrate=self.dispense_feedrate,
                motor_pwm=self.motor_pwm,
                dwell_ms=self.dwell_ms
            ))

        # 2. Fill segments if closed shape
        if self.is_closed() and len(outline) >= 3:
            if self.fill_mode == FillMode.LINE_HATCH:
                hatches = compute_hatch_lines(outline, self.stepover_mm, self.hatch_angle_deg, zig_zag=True)
                for h_line in hatches:
                    segments.append(ToolpathSegment(
                        points=h_line,
                        is_dispense=True,
                        feedrate=self.dispense_feedrate,
                        motor_pwm=self.motor_pwm,
                        dwell_ms=0
                    ))
            elif self.fill_mode == FillMode.CROSS_HATCH:
                # Pass 1
                hatches1 = compute_hatch_lines(outline, self.stepover_mm, self.hatch_angle_deg, zig_zag=True)
                for h_line in hatches1:
                    segments.append(ToolpathSegment(
                        points=h_line,
                        is_dispense=True,
                        feedrate=self.dispense_feedrate,
                        motor_pwm=self.motor_pwm,
                        dwell_ms=0
                    ))
                # Pass 2 (+90 degrees)
                hatches2 = compute_hatch_lines(outline, self.stepover_mm, self.hatch_angle_deg + 90.0, zig_zag=True)
                for h_line in hatches2:
                    segments.append(ToolpathSegment(
                        points=h_line,
                        is_dispense=True,
                        feedrate=self.dispense_feedrate,
                        motor_pwm=self.motor_pwm,
                        dwell_ms=0
                    ))
            elif self.fill_mode == FillMode.INWARD_SPIRAL:
                spirals = compute_concentric_spiral_fill(outline, self.stepover_mm)
                for s_loop in spirals:
                    segments.append(ToolpathSegment(
                        points=s_loop,
                        is_dispense=True,
                        feedrate=self.dispense_feedrate,
                        motor_pwm=self.motor_pwm,
                        dwell_ms=0
                    ))

        return segments

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "shape_type": self.shape_type.value,
            "fill_mode": self.fill_mode.value,
            "hatch_angle_deg": self.hatch_angle_deg,
            "stepover_mm": self.stepover_mm,
            "motor_pwm": self.motor_pwm,
            "dispense_feedrate": self.dispense_feedrate,
            "dwell_ms": self.dwell_ms,
            "is_visible": self.is_visible
        }


@dataclass
class RectangleShape(BaseShape):
    x: float = 0.0  # Bottom-left X (or top-left depending on coordinate convention)
    y: float = 0.0  # Bottom-left Y
    width: float = 40.0
    height: float = 30.0

    def __post_init__(self):
        self.shape_type = ShapeType.RECTANGLE
        if not self.name or self.name == "Shape":
            self.name = f"Rectangle_{self.id}"

    def get_outline_points(self) -> List[Point2D]:
        return [
            Point2D(self.x, self.y),
            Point2D(self.x + self.width, self.y),
            Point2D(self.x + self.width, self.y + self.height),
            Point2D(self.x, self.y + self.height)
        ]

    def translate(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RectangleShape:
        shape = cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Rectangle"),
            fill_mode=FillMode(data.get("fill_mode", FillMode.OUTLINE_ONLY.value)),
            hatch_angle_deg=data.get("hatch_angle_deg", 45.0),
            stepover_mm=data.get("stepover_mm", 1.0),
            motor_pwm=data.get("motor_pwm", 255),
            dispense_feedrate=data.get("dispense_feedrate", 500.0),
            dwell_ms=data.get("dwell_ms", 100),
            is_visible=data.get("is_visible", True),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            width=data.get("width", 40.0),
            height=data.get("height", 30.0)
        )
        return shape


@dataclass
class CircleShape(BaseShape):
    cx: float = 50.0
    cy: float = 50.0
    radius: float = 20.0
    segments_count: int = 64

    def __post_init__(self):
        self.shape_type = ShapeType.CIRCLE
        if not self.name or self.name == "Shape":
            self.name = f"Circle_{self.id}"

    def get_outline_points(self) -> List[Point2D]:
        pts = []
        for i in range(self.segments_count):
            theta = 2.0 * math.pi * i / self.segments_count
            pts.append(Point2D(
                self.cx + self.radius * math.cos(theta),
                self.cy + self.radius * math.sin(theta)
            ))
        return pts

    def generate_toolpaths(self) -> List[ToolpathSegment]:
        """Custom optimized spiral fill for circle when Spiral is selected."""
        if self.fill_mode == FillMode.INWARD_SPIRAL and self.stepover_mm > 0:
            segments = []
            # 1. Outer perimeter
            outline = self.get_outline_points()
            outline.append(Point2D(outline[0].x, outline[0].y))
            segments.append(ToolpathSegment(
                points=outline,
                is_dispense=True,
                feedrate=self.dispense_feedrate,
                motor_pwm=self.motor_pwm,
                dwell_ms=self.dwell_ms
            ))
            # 2. Continuous Archimedean Inward Spiral
            r = self.radius - self.stepover_mm
            spiral_pts: List[Point2D] = []
            total_turns = max(1, int(self.radius / self.stepover_mm))
            steps_per_turn = 36
            total_steps = total_turns * steps_per_turn
            
            for step in range(total_steps):
                fraction = step / float(total_steps)
                curr_r = self.radius * (1.0 - fraction)
                if curr_r < 0.2:
                    break
                theta = fraction * total_turns * 2.0 * math.pi
                spiral_pts.append(Point2D(
                    self.cx + curr_r * math.cos(theta),
                    self.cy + curr_r * math.sin(theta)
                ))
            
            if spiral_pts:
                segments.append(ToolpathSegment(
                    points=spiral_pts,
                    is_dispense=True,
                    feedrate=self.dispense_feedrate,
                    motor_pwm=self.motor_pwm,
                    dwell_ms=0
                ))
            return segments
        else:
            return super().generate_toolpaths()

    def translate(self, dx: float, dy: float):
        self.cx += dx
        self.cy += dy

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "cx": self.cx,
            "cy": self.cy,
            "radius": self.radius,
            "segments_count": self.segments_count
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CircleShape:
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Circle"),
            fill_mode=FillMode(data.get("fill_mode", FillMode.OUTLINE_ONLY.value)),
            hatch_angle_deg=data.get("hatch_angle_deg", 45.0),
            stepover_mm=data.get("stepover_mm", 1.0),
            motor_pwm=data.get("motor_pwm", 255),
            dispense_feedrate=data.get("dispense_feedrate", 500.0),
            dwell_ms=data.get("dwell_ms", 100),
            is_visible=data.get("is_visible", True),
            cx=data.get("cx", 50.0),
            cy=data.get("cy", 50.0),
            radius=data.get("radius", 20.0),
            segments_count=data.get("segments_count", 64)
        )


@dataclass
class PolylineShape(BaseShape):
    points: List[Point2D] = field(default_factory=list)

    def __post_init__(self):
        self.shape_type = ShapeType.POLYLINE
        self.fill_mode = FillMode.OUTLINE_ONLY
        if not self.name or self.name == "Shape":
            self.name = f"Polyline_{self.id}"

    def is_closed(self) -> bool:
        return False

    def get_outline_points(self) -> List[Point2D]:
        return self.points

    def translate(self, dx: float, dy: float):
        for p in self.points:
            p.x += dx
            p.y += dy

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "points": [{"x": p.x, "y": p.y} for p in self.points]
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolylineShape:
        pts = [Point2D(p["x"], p["y"]) for p in data.get("points", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Polyline"),
            fill_mode=FillMode.OUTLINE_ONLY,
            motor_pwm=data.get("motor_pwm", 255),
            dispense_feedrate=data.get("dispense_feedrate", 500.0),
            dwell_ms=data.get("dwell_ms", 100),
            is_visible=data.get("is_visible", True),
            points=pts
        )


@dataclass
class PolygonShape(BaseShape):
    points: List[Point2D] = field(default_factory=list)

    def __post_init__(self):
        self.shape_type = ShapeType.POLYGON
        if not self.name or self.name == "Shape":
            self.name = f"Polygon_{self.id}"

    def is_closed(self) -> bool:
        return True

    def get_outline_points(self) -> List[Point2D]:
        return self.points

    def translate(self, dx: float, dy: float):
        for p in self.points:
            p.x += dx
            p.y += dy

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "points": [{"x": p.x, "y": p.y} for p in self.points]
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PolygonShape:
        pts = [Point2D(p["x"], p["y"]) for p in data.get("points", [])]
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Polygon"),
            fill_mode=FillMode(data.get("fill_mode", FillMode.OUTLINE_ONLY.value)),
            hatch_angle_deg=data.get("hatch_angle_deg", 45.0),
            stepover_mm=data.get("stepover_mm", 1.0),
            motor_pwm=data.get("motor_pwm", 255),
            dispense_feedrate=data.get("dispense_feedrate", 500.0),
            dwell_ms=data.get("dwell_ms", 100),
            is_visible=data.get("is_visible", True),
            points=pts
        )


@dataclass
class DispenseDotShape(BaseShape):
    x: float = 0.0
    y: float = 0.0
    dot_dwell_ms: int = 500  # Vibration time at point

    def __post_init__(self):
        self.shape_type = ShapeType.DISPENSE_DOT
        self.fill_mode = FillMode.OUTLINE_ONLY
        if not self.name or self.name == "Shape":
            self.name = f"Dot_{self.id}"

    def is_closed(self) -> bool:
        return False

    def get_outline_points(self) -> List[Point2D]:
        return [Point2D(self.x, self.y)]

    def translate(self, dx: float, dy: float):
        self.x += dx
        self.y += dy

    def generate_toolpaths(self) -> List[ToolpathSegment]:
        return [ToolpathSegment(
            points=[Point2D(self.x, self.y)],
            is_dispense=True,
            feedrate=self.dispense_feedrate,
            motor_pwm=self.motor_pwm,
            dwell_ms=self.dot_dwell_ms
        )]

    def to_dict(self) -> Dict[str, Any]:
        d = super().to_dict()
        d.update({
            "x": self.x,
            "y": self.y,
            "dot_dwell_ms": self.dot_dwell_ms
        })
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> DispenseDotShape:
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Dot"),
            motor_pwm=data.get("motor_pwm", 255),
            dispense_feedrate=data.get("dispense_feedrate", 500.0),
            is_visible=data.get("is_visible", True),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            dot_dwell_ms=data.get("dot_dwell_ms", 500)
        )


def shape_from_dict(data: Dict[str, Any]) -> Optional[BaseShape]:
    st = data.get("shape_type")
    if st == ShapeType.RECTANGLE.value:
        return RectangleShape.from_dict(data)
    elif st == ShapeType.CIRCLE.value:
        return CircleShape.from_dict(data)
    elif st == ShapeType.POLYLINE.value:
        return PolylineShape.from_dict(data)
    elif st == ShapeType.POLYGON.value:
        return PolygonShape.from_dict(data)
    elif st == ShapeType.DISPENSE_DOT.value:
        return DispenseDotShape.from_dict(data)
    return None
