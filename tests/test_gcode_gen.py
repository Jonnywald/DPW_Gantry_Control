"""Unit tests for G-code generation and M106/M107 dispenser sequencing."""

import unittest
from dpw_gantry.core.geometry import RectangleShape, Point2D, PolylineShape, FillMode
from dpw_gantry.core.gcode_generator import GCodeGenerator, GCodeConfig


class TestGCodeGenerator(unittest.TestCase):

    def test_gcode_generator_m106_m107_injection(self):
        poly = PolylineShape(
            points=[Point2D(10, 10), Point2D(50, 10), Point2D(50, 50)],
            motor_pwm=200,
            dispense_feedrate=600.0
        )
        
        generator = GCodeGenerator(GCodeConfig(travel_feedrate=3000.0))
        gcode, stats = generator.generate([poly], dry_run=False)

        self.assertIn("M106 S200", gcode)
        self.assertIn("M107", gcode)
        self.assertIn("G0 X10.000 Y10.000 F3000.0", gcode)
        self.assertIn("G1 X50.000 Y10.000 F600.0", gcode)
        self.assertIn("G1 X50.000 Y50.000", gcode)
        
        # Motor ON must occur after travel G0 and before G1
        idx_g0 = gcode.find("G0 X10.000 Y10.000")
        idx_m106 = gcode.find("M106 S200")
        idx_g1 = gcode.find("G1 X50.000 Y10.000")
        idx_m107 = gcode.find("M107 ; Dispenser Motor OFF")

        self.assertTrue(idx_g0 < idx_m106 < idx_g1 < idx_m107)

    def test_gcode_generator_dry_run(self):
        poly = PolylineShape(
            points=[Point2D(0, 0), Point2D(20, 20)],
            motor_pwm=255
        )
        generator = GCodeGenerator()
        gcode, stats = generator.generate([poly], dry_run=True)

        # In dry run, M106 must be commented out
        self.assertIn("[DRY RUN]", gcode)
        self.assertNotIn("\nM106 ", gcode)

    def test_gcode_generator_hatched_rectangle(self):
        rect = RectangleShape(
            x=10, y=10, width=20, height=20,
            stepover_mm=5.0,
            fill_mode=FillMode.LINE_HATCH,
            motor_pwm=220
        )
        generator = GCodeGenerator()
        gcode, stats = generator.generate([rect])

        self.assertGreater(stats.total_dispense_dist_mm, 0)
        self.assertGreater(stats.total_travel_dist_mm, 0)
        self.assertGreater(stats.estimated_time_sec, 0)


if __name__ == "__main__":
    unittest.main()
