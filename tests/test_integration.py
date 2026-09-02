"""Integration tests for project serialization, toolpath compilation, and parser."""

import os
import tempfile
import unittest
from dpw_gantry.core.geometry import (
    RectangleShape, CircleShape, PolylineShape, PolygonShape,
    DispenseDotShape, Point2D, FillMode
)
from dpw_gantry.core.gcode_generator import GCodeGenerator, GCodeConfig
from dpw_gantry.core.gcode_parser import GCodeParser
from dpw_gantry.core.project_manager import ProjectManager, ProjectData


class TestIntegration(unittest.TestCase):

    def test_full_project_save_load_lifecycle(self):
        shapes = [
            RectangleShape(x=10, y=10, width=40, height=30, fill_mode=FillMode.LINE_HATCH, hatch_angle_deg=30.0, motor_pwm=200),
            CircleShape(cx=100, cy=100, radius=25, fill_mode=FillMode.INWARD_SPIRAL, motor_pwm=255),
            PolylineShape(points=[Point2D(0, 0), Point2D(50, 0), Point2D(50, 50)], motor_pwm=180),
            PolygonShape(points=[Point2D(150, 10), Point2D(190, 10), Point2D(170, 40)], fill_mode=FillMode.CROSS_HATCH),
            DispenseDotShape(x=120, y=150, dot_dwell_ms=800, motor_pwm=220)
        ]

        cfg = GCodeConfig(
            travel_feedrate=4000.0,
            default_dispense_feedrate=600.0,
            pre_dispense_dwell_ms=75
        )

        project = ProjectData(
            project_name="Integration Test Project",
            bed_width_mm=250.0,
            bed_height_mm=250.0,
            grid_spacing_mm=5.0,
            shapes=shapes,
            gcode_config=cfg
        )

        with tempfile.NamedTemporaryFile(suffix=".dpw", delete=False) as tf:
            temp_path = tf.name

        try:
            # 1. Save
            saved = ProjectManager.save_project(project, temp_path)
            self.assertTrue(saved)

            # 2. Load
            loaded = ProjectManager.load_project(temp_path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.project_name, "Integration Test Project")
            self.assertEqual(loaded.bed_width_mm, 250.0)
            self.assertEqual(len(loaded.shapes), 5)
            self.assertEqual(loaded.gcode_config.travel_feedrate, 4000.0)

            # 3. Generate G-code
            generator = GCodeGenerator(loaded.gcode_config)
            gcode, stats = generator.generate(loaded.shapes, dry_run=False)

            self.assertGreater(stats.total_lines, 20)
            self.assertGreater(stats.total_dispense_dist_mm, 0)
            self.assertIn("M106 S200", gcode)
            self.assertIn("M106 S255", gcode)
            self.assertIn("G4 P800", gcode)  # Dot dwell

            # 4. Parse generated G-code
            parser = GCodeParser()
            parsed_res = parser.parse(gcode)
            self.assertGreater(len(parsed_res.moves), 10)
            self.assertGreater(parsed_res.total_dispense_dist_mm, 0.0)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


if __name__ == "__main__":
    unittest.main()
