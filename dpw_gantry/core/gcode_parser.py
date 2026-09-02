"""G-code Parser for visualization, path simulation, and external file import."""

from __future__ import annotations
import re
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from .geometry import Point2D


@dataclass
class ParsedMove:
    command: str              # G0, G1, G28, G4, M106, M107, etc.
    start_pos: Point2D
    end_pos: Point2D
    feedrate: float = 3000.0
    motor_on: bool = False
    motor_pwm: int = 0
    dwell_ms: int = 0
    line_number: int = 0
    raw_line: str = ""

    @property
    def distance(self) -> float:
        return self.start_pos.distance_to(self.end_pos)


@dataclass
class ParsedGCodeResult:
    moves: List[ParsedMove] = field(default_factory=list)
    total_travel_dist_mm: float = 0.0
    total_dispense_dist_mm: float = 0.0
    estimated_time_sec: float = 0.0
    bounds: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)  # min_x, min_y, max_x, max_y
    warnings: List[str] = field(default_factory=list)


class GCodeParser:
    """Parses standard Marlin G-code into visualizable moves and metrics."""

    _CMD_REGEX = re.compile(r"([A-Z])([-+]?[0-9]*\.?[0-9]+)")

    def parse(self, gcode_text: str) -> ParsedGCodeResult:
        result = ParsedGCodeResult()
        
        current_x = 0.0
        current_y = 0.0
        current_feedrate = 3000.0
        current_motor_on = False
        current_motor_pwm = 0
        is_relative = False

        min_x, min_y = float("inf"), float("inf")
        max_x, max_y = float("-inf"), float("-inf")
        has_coords = False

        lines = gcode_text.splitlines()

        for line_idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            # Strip comments
            comment_idx = line.find(";")
            if comment_idx != -1:
                line = line[:comment_idx].strip()
            if not line:
                continue

            # Tokenize command and arguments
            tokens = self._CMD_REGEX.findall(line.upper())
            if not tokens:
                continue

            cmd_letter, cmd_num = tokens[0]
            main_cmd = f"{cmd_letter}{cmd_num}"
            params: Dict[str, float] = {}
            for letter, val in tokens[1:]:
                params[letter] = float(val)

            start_pt = Point2D(current_x, current_y)

            # Process state commands
            if main_cmd == "G90":
                is_relative = False
                continue
            elif main_cmd == "G91":
                is_relative = True
                continue
            elif main_cmd == "G92":
                # Set coordinate position
                if "X" in params:
                    current_x = params["X"]
                if "Y" in params:
                    current_y = params["Y"]
                continue
            elif main_cmd == "G28":
                # Homing
                current_x = 0.0
                current_y = 0.0
                move = ParsedMove(
                    command="G28",
                    start_pos=start_pt,
                    end_pos=Point2D(0.0, 0.0),
                    feedrate=current_feedrate,
                    motor_on=False,
                    motor_pwm=0,
                    line_number=line_idx,
                    raw_line=raw_line
                )
                result.moves.append(move)
                min_x = min(min_x, 0.0)
                min_y = min(min_y, 0.0)
                max_x = max(max_x, 0.0)
                max_y = max(max_y, 0.0)
                has_coords = True
                continue
            elif main_cmd == "M106":
                # Fan / Vibration motor ON
                current_motor_on = True
                current_motor_pwm = int(params.get("S", 255))
                continue
            elif main_cmd == "M107":
                # Fan / Vibration motor OFF
                current_motor_on = False
                current_motor_pwm = 0
                continue
            elif main_cmd == "G4":
                # Dwell
                dwell_ms = int(params.get("P", params.get("S", 0) * 1000))
                result.estimated_time_sec += (dwell_ms / 1000.0)
                move = ParsedMove(
                    command="G4",
                    start_pos=start_pt,
                    end_pos=start_pt,
                    feedrate=current_feedrate,
                    motor_on=current_motor_on,
                    motor_pwm=current_motor_pwm,
                    dwell_ms=dwell_ms,
                    line_number=line_idx,
                    raw_line=raw_line
                )
                result.moves.append(move)
                continue

            # Motion commands (G0, G1)
            if main_cmd in ("G0", "G1"):
                if "F" in params:
                    current_feedrate = params["F"]

                target_x = current_x
                target_y = current_y

                if "X" in params:
                    target_x = (current_x + params["X"]) if is_relative else params["X"]
                if "Y" in params:
                    target_y = (current_y + params["Y"]) if is_relative else params["Y"]

                end_pt = Point2D(target_x, target_y)
                move = ParsedMove(
                    command=main_cmd,
                    start_pos=start_pt,
                    end_pos=end_pt,
                    feedrate=current_feedrate,
                    motor_on=(main_cmd == "G1" and current_motor_on),
                    motor_pwm=current_motor_pwm if current_motor_on else 0,
                    line_number=line_idx,
                    raw_line=raw_line
                )
                result.moves.append(move)

                dist = start_pt.distance_to(end_pt)
                if main_cmd == "G0" or not current_motor_on:
                    result.total_travel_dist_mm += dist
                else:
                    result.total_dispense_dist_mm += dist

                if current_feedrate > 0:
                    result.estimated_time_sec += (dist / (current_feedrate / 60.0))

                current_x = target_x
                current_y = target_y

                min_x = min(min_x, target_x)
                min_y = min(min_y, target_y)
                max_x = max(max_x, target_x)
                max_y = max(max_y, target_y)
                has_coords = True

        if has_coords:
            result.bounds = (min_x, min_y, max_x, max_y)
        else:
            result.bounds = (0.0, 0.0, 200.0, 200.0)

        return result
