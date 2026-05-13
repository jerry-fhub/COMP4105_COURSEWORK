from __future__ import annotations

import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from src.env.grid_overlay import GridWorld
from src.env.models import Position, ScenarioConfig
from src.utils.logging_utils import write_json


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


@dataclass(slots=True)
class StageArtifactBundle:
    world_path: Path
    bitmap_path: Path
    manifest_path: Path
    stage_available: bool
    stage_binary: Path | None
    smoke_test_ran: bool
    smoke_test_passed: bool | None
    smoke_test_return_code: int | None
    smoke_test_output: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "world_path": str(self.world_path),
            "bitmap_path": str(self.bitmap_path),
            "manifest_path": str(self.manifest_path),
            "stage_available": self.stage_available,
            "stage_binary": None if self.stage_binary is None else str(self.stage_binary),
            "smoke_test_ran": self.smoke_test_ran,
            "smoke_test_passed": self.smoke_test_passed,
            "smoke_test_return_code": self.smoke_test_return_code,
            "smoke_test_output": self.smoke_test_output,
        }


class StageInterface:
    """Generate concrete Stage worlds from the discrete experiment state."""

    @staticmethod
    def _candidate_stage_roots() -> list[Path]:
        candidates: list[Path] = []
        env_root = os.environ.get("STAGE_ROOT")
        if env_root:
            candidates.append(Path(env_root))
        candidates.append(_WORKSPACE_ROOT / "stage-install")
        return candidates

    @classmethod
    def _stage_root(cls) -> Path | None:
        for root in cls._candidate_stage_roots():
            if (root / "bin" / "stage").exists():
                return root
        binary = shutil.which("stage")
        if binary is None:
            return None
        return Path(binary).resolve().parents[1]

    @classmethod
    def _stage_binary(cls) -> Path | None:
        root = cls._stage_root()
        if root is not None:
            candidate = root / "bin" / "stage"
            if candidate.exists():
                return candidate
        binary = shutil.which("stage")
        return None if binary is None else Path(binary).resolve()

    @classmethod
    def _stage_support_dir(cls) -> Path | None:
        root = cls._stage_root()
        if root is None:
            return None
        candidate = root / "share" / "stage" / "worlds"
        return candidate if candidate.exists() else None

    @classmethod
    def _stage_env(cls) -> dict[str, str]:
        env = os.environ.copy()
        root = cls._stage_root()
        if root is None:
            return env

        env["STAGE_ROOT"] = str(root)
        env["PATH"] = f"{root / 'bin'}:{env.get('PATH', '')}"

        ld_parts = [str(root / "lib")]
        deps_root = os.environ.get("STAGE_DEPS_ROOT")
        if deps_root:
            deps_path = Path(deps_root)
            ld_parts.append(str(deps_path / "lib" if (deps_path / "lib").exists() else deps_path))
        workspace_deps = _WORKSPACE_ROOT / "stage-deps" / "lib"
        if workspace_deps.exists():
            ld_parts.append(str(workspace_deps))
        existing_ld = env.get("LD_LIBRARY_PATH")
        if existing_ld:
            ld_parts.append(existing_ld)
        env["LD_LIBRARY_PATH"] = ":".join(part for part in ld_parts if part)

        stagepath = root / "lib" / "Stage-4.3"
        if stagepath.exists():
            env["STAGEPATH"] = str(stagepath)
        return env

    @staticmethod
    def is_available() -> bool:
        return StageInterface._stage_binary() is not None

    @staticmethod
    def _grid_to_stage(position: Position, config: ScenarioConfig) -> tuple[float, float]:
        world_width_m = config.width * config.cell_size_m
        world_height_m = config.height * config.cell_size_m
        x, y = position
        stage_x = (x + 0.5) * config.cell_size_m - (world_width_m / 2.0)
        stage_y = (world_height_m / 2.0) - (y + 0.5) * config.cell_size_m
        return (stage_x, stage_y)

    @staticmethod
    def _robot_pose_offsets(count: int, cell_size_m: float) -> list[tuple[float, float, float]]:
        if count <= 1:
            return [(0.0, 0.0, 0.0)]
        radius = min(0.22, max(cell_size_m * 0.22, 0.12))
        offsets: list[tuple[float, float, float]] = []
        for index in range(count):
            angle = (2.0 * math.pi * index) / count
            offsets.append((radius * math.cos(angle), radius * math.sin(angle), math.degrees(angle)))
        return offsets

    @classmethod
    def _export_bitmap(cls, config: ScenarioConfig, bitmap_path: Path) -> None:
        pixels_per_cell = max(config.stage_pixels_per_cell, 1)
        image = Image.new("RGB", (config.width * pixels_per_cell, config.height * pixels_per_cell), color="white")
        draw = ImageDraw.Draw(image)

        for x, y, width, height in config.obstacle_rectangles:
            left = x * pixels_per_cell
            top = y * pixels_per_cell
            right = (x + width) * pixels_per_cell - 1
            bottom = (y + height) * pixels_per_cell - 1
            draw.rectangle((left, top, right, bottom), fill="black")

        image.save(bitmap_path)

    @classmethod
    def _copy_support_files(cls, asset_dir: Path) -> None:
        support_dir = cls._stage_support_dir()
        if support_dir is None:
            support_dir = _PROJECT_ROOT / "worlds"
        for name in ("pioneer.inc", "map.inc"):
            source = support_dir / name
            if not source.exists():
                raise FileNotFoundError(
                    f"Stage support file {name} was not found in {support_dir}. "
                    "Install Stage or keep the bundled support files under project/worlds/."
                )
            shutil.copyfile(source, asset_dir / name)

    @classmethod
    def _world_text(cls, config: ScenarioConfig, world: GridWorld, bitmap_path: Path) -> str:
        world_width_m = config.width * config.cell_size_m
        world_height_m = config.height * config.cell_size_m
        map_resolution = config.cell_size_m / max(config.stage_pixels_per_cell, 1)
        marker_size = max(0.28, config.cell_size_m * 0.4)
        resource_size = max(0.22, config.cell_size_m * 0.28)
        window_scale = max(18.0, 900.0 / max(world_width_m, world_height_m, 1.0))

        lines = [
            "# Generated Stage world for the COMP3004/4105 coursework project.",
            f"# scenario={config.name}",
            f"# backend={config.environment_backend}",
            f"# cell_size_m={config.cell_size_m}",
            'include "pioneer.inc"',
            'include "map.inc"',
            "",
            f"resolution {map_resolution:.3f}",
            "speedup 0",
            "paused 0",
            "",
            "window",
            "(",
            "  size [ 900.000 900.000 ]",
            f"  scale {window_scale:.3f}",
            "  center [ 0.000 0.000 ]",
            "  rotate [ 0 0 ]",
            "  show_data 1",
            ")",
            "",
            "define depot_marker model",
            "(",
            f"  size [ {marker_size:.3f} {marker_size:.3f} 0.040 ]",
            '  color "blue"',
            "  gui_nose 0",
            "  gui_move 0",
            "  gui_outline 1",
            "  obstacle_return 0",
            "  ranger_return -1",
            "  gripper_return 0",
            "  fiducial_return 0",
            ")",
            "",
            "define resource_marker model",
            "(",
            f"  size [ {resource_size:.3f} {resource_size:.3f} 0.040 ]",
            '  color "green"',
            "  gui_nose 0",
            "  gui_move 0",
            "  gui_outline 1",
            "  obstacle_return 0",
            "  ranger_return -1",
            "  gripper_return 0",
            "  fiducial_return 0",
            ")",
            "",
            "floorplan",
            "(",
            f'  name "{config.name}_floorplan"',
            f'  bitmap "{bitmap_path.name}"',
            f"  size [ {world_width_m:.3f} {world_height_m:.3f} 0.600 ]",
            "  pose [ 0.000 0.000 0.000 0.000 ]",
            f"  map_resolution {map_resolution:.3f}",
            '  color "gray40"',
            "  gui_grid 1",
            "  gui_outline 1",
            ")",
            "",
        ]

        depot_x, depot_y = cls._grid_to_stage(config.depot, config)
        lines.append(
            f'depot_marker( name "depot" pose [ {depot_x:.3f} {depot_y:.3f} 0.000 0.000 ] )'
        )
        lines.append("")

        resource_colors = {1: "green", 2: "orange", 3: "red"}
        for resource in sorted(world.resources.values(), key=lambda item: item.resource_id):
            x, y = cls._grid_to_stage(resource.position, config)
            color = resource_colors.get(resource.required_agents, "yellow")
            lines.append(
                "resource_marker("
                f' name "{resource.resource_id}"'
                f" pose [ {x:.3f} {y:.3f} 0.000 0.000 ]"
                f' color "{color}"'
                ")"
            )
        lines.append("")

        grouped: dict[Position, list[Any]] = {}
        for robot in world.robots.values():
            grouped.setdefault(robot.position, []).append(robot)

        palette = ["red", "cyan", "magenta", "yellow", "navyblue", "purple", "orange"]
        color_index = 0
        for position, robots in sorted(grouped.items(), key=lambda item: item[0]):
            base_x, base_y = cls._grid_to_stage(position, config)
            offsets = cls._robot_pose_offsets(len(robots), config.cell_size_m)
            for robot, (offset_x, offset_y, heading) in zip(
                sorted(robots, key=lambda item: item.robot_id),
                offsets,
                strict=True,
            ):
                lines.extend(
                    [
                        "pioneer2dx",
                        "(",
                        f'  name "{robot.robot_id}"',
                        f'  color "{palette[color_index % len(palette)]}"',
                        f"  pose [ {base_x + offset_x:.3f} {base_y + offset_y:.3f} 0.000 {heading:.3f} ]",
                        '  localization "gps"',
                        "  localization_origin [ 0 0 0 0 ]",
                        "  trail_length 250",
                        ")",
                        "",
                    ]
                )
                color_index += 1

        return "\n".join(lines).rstrip() + "\n"

    @classmethod
    def smoke_test_world(cls, world_path: str | Path, timeout_s: float = 3.0) -> tuple[bool, int | None, str]:
        binary = cls._stage_binary()
        if binary is None:
            return (False, None, "Stage binary not found.")

        target = Path(world_path)
        try:
            completed = subprocess.run(
                [str(binary), "-g", target.name],
                cwd=target.parent,
                env=cls._stage_env(),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_s,
            )
            output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
            return (completed.returncode == 0, completed.returncode, output)
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = "\n".join(part for part in (stdout.strip(), stderr.strip()) if part)
            return (True, 124, output)

    @classmethod
    def materialize_assets(
        cls,
        config: ScenarioConfig,
        world: GridWorld,
        output_dir: str | Path,
        stem: str,
        *,
        smoke_test: bool = False,
        timeout_s: float | None = None,
    ) -> StageArtifactBundle:
        asset_dir = Path(output_dir)
        asset_dir.mkdir(parents=True, exist_ok=True)
        cls._copy_support_files(asset_dir)

        bitmap_path = asset_dir / f"{stem}_floorplan.png"
        world_path = asset_dir / f"{stem}.world"
        manifest_path = asset_dir / f"{stem}_stage_manifest.json"

        cls._export_bitmap(config, bitmap_path)
        world_text = cls._world_text(config, world, bitmap_path)
        world_path.write_text(world_text, encoding="utf-8")

        smoke_test_ran = smoke_test and cls.is_available()
        smoke_test_passed: bool | None = None
        smoke_test_return_code: int | None = None
        smoke_test_output = ""
        if smoke_test_ran:
            smoke_test_passed, smoke_test_return_code, smoke_test_output = cls.smoke_test_world(
                world_path,
                timeout_s=config.stage_smoketest_timeout_s if timeout_s is None else timeout_s,
            )

        bundle = StageArtifactBundle(
            world_path=world_path,
            bitmap_path=bitmap_path,
            manifest_path=manifest_path,
            stage_available=cls.is_available(),
            stage_binary=cls._stage_binary(),
            smoke_test_ran=smoke_test_ran,
            smoke_test_passed=smoke_test_passed,
            smoke_test_return_code=smoke_test_return_code,
            smoke_test_output=smoke_test_output,
        )
        write_json(
            manifest_path,
            {
                "scenario": config.name,
                "backend": config.environment_backend,
                "cell_size_m": config.cell_size_m,
                "bitmap_path": bitmap_path,
                "world_path": world_path,
                "project_root": "project",
                "workspace_root": ".",
                "stage": bundle.as_dict(),
                "resource_positions": {
                    resource.resource_id: resource.position for resource in sorted(world.resources.values(), key=lambda item: item.resource_id)
                },
                "robot_positions": {
                    robot.robot_id: robot.position for robot in sorted(world.robots.values(), key=lambda item: item.robot_id)
                },
            },
        )
        return bundle
