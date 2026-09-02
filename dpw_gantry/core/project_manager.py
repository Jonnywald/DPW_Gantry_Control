"""Project serialization and file management for 2D Powder-Dispensing Gantry."""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from .geometry import BaseShape, shape_from_dict
from .gcode_generator import GCodeConfig


@dataclass
class ProjectData:
    version: str = "1.0.0"
    project_name: str = "Untitled Project"
    bed_width_mm: float = 177.0
    bed_height_mm: float = 101.0
    grid_spacing_mm: float = 10.0
    shapes: List[BaseShape] = field(default_factory=list)
    gcode_config: GCodeConfig = field(default_factory=GCodeConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "project_name": self.project_name,
            "bed_width_mm": self.bed_width_mm,
            "bed_height_mm": self.bed_height_mm,
            "grid_spacing_mm": self.grid_spacing_mm,
            "shapes": [s.to_dict() for s in self.shapes],
            "gcode_config": asdict(self.gcode_config)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectData:
        proj = cls(
            version=data.get("version", "1.0.0"),
            project_name=data.get("project_name", "Untitled Project"),
            bed_width_mm=data.get("bed_width_mm", 177.0),
            bed_height_mm=data.get("bed_height_mm", 101.0),
            grid_spacing_mm=data.get("grid_spacing_mm", 10.0)
        )
        
        # Load shapes
        shapes_data = data.get("shapes", [])
        proj.shapes = []
        for sd in shapes_data:
            shape = shape_from_dict(sd)
            if shape:
                proj.shapes.append(shape)

        # Load GCodeConfig
        gc_data = data.get("gcode_config", {})
        if gc_data:
            proj.gcode_config = GCodeConfig(**gc_data)

        return proj


class ProjectManager:
    """Manages saving, loading, and exporting projects."""

    @staticmethod
    def save_project(project: ProjectData, file_path: str) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(project.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(file_path: str) -> Optional[ProjectData]:
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ProjectData.from_dict(data)
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
