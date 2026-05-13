from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.env.grid_overlay import GridWorld
from src.env.models import FailureEvent, Robot, ScenarioConfig
from src.env.resource_manager import generate_resources
from src.utils.seeds import seed_everything


def _rectangles_to_obstacles(rectangles: list[tuple[int, int, int, int]]) -> set[tuple[int, int]]:
    obstacles: set[tuple[int, int]] = set()
    for x, y, width, height in rectangles:
        for dx in range(width):
            for dy in range(height):
                obstacles.add((x + dx, y + dy))
    return obstacles


def load_config(path: str | Path) -> ScenarioConfig:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    failure_events = [FailureEvent(**item) for item in data.get("failure_events", [])]
    return ScenarioConfig(
        name=data["name"],
        width=data["width"],
        height=data["height"],
        depot=tuple(data["depot"]),
        robot_count=data["robot_count"],
        sensor_range=data["sensor_range"],
        max_steps=data["max_steps"],
        resource_count=data["resource_count"],
        obstacle_rectangles=[tuple(item) for item in data.get("obstacle_rectangles", [])],
        resource_required_agents=list(data.get("resource_required_agents", [1, 2, 3])),
        resource_required_weights=list(data.get("resource_required_weights", [0.4, 0.4, 0.2])),
        resource_value_range=tuple(data.get("resource_value_range", [5, 15])),
        replan_interval=data.get("replan_interval", 3),
        llm_replan_interval=data.get("llm_replan_interval", 5),
        team_timeout=data.get("team_timeout", 8),
        seed=data.get("seed", 0),
        failure_events=failure_events,
        output_dir=Path(data.get("output_dir", "results_openai_gpt54")),
        environment_backend=data.get("environment_backend", "stage_world"),
        cell_size_m=float(data.get("cell_size_m", 1.0)),
        stage_pixels_per_cell=int(data.get("stage_pixels_per_cell", 20)),
        stage_smoketest=bool(data.get("stage_smoketest", False)),
        stage_smoketest_timeout_s=float(data.get("stage_smoketest_timeout_s", 3.0)),
        llm_backend=data.get("llm_backend", "openai"),
        llm_model=data.get("llm_model", "gpt-5.4"),
        llm_cache_path=Path(data.get("llm_cache_path", "results_openai_gpt54/raw/llm_cache_openai_gpt54.json")),
        notes=data.get("notes", {}),
    )


def build_world(config: ScenarioConfig, seed: int | None = None) -> GridWorld:
    run_seed = config.seed if seed is None else seed
    rng = seed_everything(run_seed)
    obstacles = _rectangles_to_obstacles(config.obstacle_rectangles)
    resources = generate_resources(config, obstacles, rng)
    robots = {
        f"robot_{index}": Robot(
            robot_id=f"robot_{index}",
            position=config.depot,
            sensor_range=config.sensor_range,
            depot=config.depot,
        )
        for index in range(config.robot_count)
    }
    return GridWorld(
        width=config.width,
        height=config.height,
        depot=config.depot,
        obstacles=obstacles,
        resources=resources,
        robots=robots,
    )
