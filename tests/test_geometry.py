"""Unit tests for geometry, fill hatching, and spiral offset algorithms."""

import math
import unittest
from dpw_gantry.core.geometry import (
    Point2D,
    RectangleShape,
    CircleShape,
    PolylineShape,
    PolygonShape,
    DispenseDotShape,
    FillMode,
    ShapeType,
    compute_hatch_lines,
    compute_concentric_spiral_fill,
    shape_from_dict
)


class TestGeometry(unittest.TestCase):

    def test_point_rotation(self):
        p = Point2D(10, 0)
        p_rot = p.rotated(math.pi / 2)
        self.assertAlmostEqual(p_rot.x, 0.0, places=5)
        self.assertAlmostEqual(p_rot.y, 10.0, places=5)

    def test_rectangle_hatch_lines_horizontal(self):
        rect = RectangleShape(x=0, y=0, width=20, height=10, stepover_mm=2.0, hatch_angle_deg=0.0)
        outline = rect.get_outline_points()
        hatches = compute_hatch_lines(outline, stepover_mm=2.0, angle_deg=0.0, zig_zag=True)
        
        # Height is 10mm, stepover is 2.0 -> expects 5 hatch lines
        self.assertEqual(len(hatches), 5)
        for line in hatches:
            p1, p2 = line[0], line[1]
            self.assertAlmostEqual(abs(p1.x - p2.x), 20.0, places=3)
            self.assertAlmostEqual(p1.y, p2.y, places=3)

    def test_rectangle_hatch_lines_angled(self):
        rect = RectangleShape(x=0, y=0, width=20, height=20, stepover_mm=2.0, hatch_angle_deg=45.0)
        outline = rect.get_outline_points()
        hatches = compute_hatch_lines(outline, stepover_mm=2.0, angle_deg=45.0, zig_zag=True)
        self.assertGreater(len(hatches), 0)
        for line in hatches:
            for pt in line:
                self.assertTrue(-0.1 <= pt.x <= 20.1)
                self.assertTrue(-0.1 <= pt.y <= 20.1)

    def test_circle_spiral_generation(self):
        circle = CircleShape(cx=50, cy=50, radius=10, stepover_mm=2.0, fill_mode=FillMode.INWARD_SPIRAL)
        toolpaths = circle.generate_toolpaths()
        self.assertGreaterEqual(len(toolpaths), 2)
        spiral_seg = toolpaths[1]
        self.assertGreater(len(spiral_seg.points), 10)
        p_start = spiral_seg.points[0]
        p_end = spiral_seg.points[-1]
        self.assertAlmostEqual(p_start.distance_to(Point2D(50, 50)), 10.0, delta=1.0)
        self.assertLess(p_end.distance_to(Point2D(50, 50)), 3.0)

    def test_polygon_concentric_fill(self):
        triangle = PolygonShape(
            points=[Point2D(0, 0), Point2D(30, 0), Point2D(15, 25)],
            stepover_mm=3.0,
            fill_mode=FillMode.INWARD_SPIRAL
        )
        toolpaths = triangle.generate_toolpaths()
        self.assertGreaterEqual(len(toolpaths), 2)

    def test_shape_serialization_roundtrip(self):
        rect = RectangleShape(x=15.5, y=25.0, width=50.0, height=30.0, motor_pwm=180, fill_mode=FillMode.CROSS_HATCH)
        d = rect.to_dict()
        restored = shape_from_dict(d)
        self.assertIsInstance(restored, RectangleShape)
        self.assertEqual(restored.x, 15.5)
        self.assertEqual(restored.y, 25.0)
        self.assertEqual(restored.width, 50.0)
        self.assertEqual(restored.height, 30.0)
        self.assertEqual(restored.motor_pwm, 180)
        self.assertEqual(restored.fill_mode, FillMode.CROSS_HATCH)


if __name__ == "__main__":
    unittest.main()
