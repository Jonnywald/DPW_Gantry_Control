"""Unit tests for G-code parser."""

import unittest
from dpw_gantry.core.gcode_parser import GCodeParser


class TestGCodeParser(unittest.TestCase):

    def test_gcode_parser_basic_moves(self):
        raw_gcode = """
        G21 ; metric
        G90 ; absolute
        G28 XY ; home
        G0 X10.0 Y15.0 F3000
        M106 S255
        G4 P100
        G1 X50.0 Y15.0 F500
        G1 X50.0 Y50.0
        M107
        G0 X0 Y0
        """
        parser = GCodeParser()
        res = parser.parse(raw_gcode)

        self.assertGreaterEqual(len(res.moves), 4)
        # Check bounds
        self.assertLessEqual(res.bounds[0], 0.0)
        self.assertLessEqual(res.bounds[1], 0.0)
        self.assertGreaterEqual(res.bounds[2], 50.0)
        self.assertGreaterEqual(res.bounds[3], 50.0)
        self.assertGreater(res.total_dispense_dist_mm, 0.0)
        self.assertGreater(res.total_travel_dist_mm, 0.0)


if __name__ == "__main__":
    unittest.main()
