from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.env.models import Position, Resource, ResourceStatus, Robot


class GridWorld:
    """Discrete grid overlay used for reproducible experiments."""

    def __init__(
        self,
        width: int,
        height: int,
        depot: Position,
        obstacles: set[Position],
        resources: dict[str, Resource],
        robots: dict[str, Robot],
    ) -> None:
        self.width = width
        self.height = height
        self.depot = depot
        self.obstacles = obstacles
        self.resources = resources
        self.robots = robots
        self.step_count = 0
        self.explored_cells: set[Position] = set()
        self.event_log: list[dict[str, Any]] = []
        self.coordinator_messages = 0
        self.coordinator_replans = 0
        self.llm_token_usage = 0
        self.llm_latencies_ms: list[float] = []
        self.invalid_llm_outputs = 0
        self.failure_step: int | None = None
        self.recovery_step: int | None = None

    def in_bounds(self, position: Position) -> bool:
        x, y = position
        return 0 <= x < self.width and 0 <= y < self.height

    def passable(self, position: Position) -> bool:
        return position not in self.obstacles

    def neighbors(self, position: Position) -> list[Position]:
        x, y = position
        candidates = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        return [pos for pos in candidates if self.in_bounds(pos) and self.passable(pos)]

    def perceive(self, robot: Robot) -> None:
        x0, y0 = robot.position
        for dx in range(-robot.sensor_range, robot.sensor_range + 1):
            for dy in range(-robot.sensor_range, robot.sensor_range + 1):
                if abs(dx) + abs(dy) > robot.sensor_range:
                    continue
                pos = (x0 + dx, y0 + dy)
                if not self.in_bounds(pos) or not self.passable(pos):
                    continue
                self.explored_cells.add(pos)
                for resource in self.resources.values():
                    if resource.position == pos and resource.status == ResourceStatus.HIDDEN:
                        resource.status = ResourceStatus.DISCOVERED
                        resource.discovered_at = self.step_count
                        resource.discovered_by = robot.robot_id
                        robot.observed_resources.add(resource.resource_id)
                        self.log_event(
                            "resource_discovered",
                            resource_id=resource.resource_id,
                            robot_id=robot.robot_id,
                            position=resource.position,
                        )

    def frontier_cells(self) -> set[Position]:
        frontiers: set[Position] = set()
        for cell in self.explored_cells:
            if not self.passable(cell):
                continue
            for neighbor in self.neighbors(cell):
                if neighbor not in self.explored_cells:
                    frontiers.add(cell)
                    break
        return frontiers

    def discovered_resources(self) -> list[Resource]:
        return [
            resource
            for resource in self.resources.values()
            if resource.status in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED, ResourceStatus.CARRYING}
        ]

    def active_resources(self) -> list[Resource]:
        return [
            resource
            for resource in self.resources.values()
            if resource.status != ResourceStatus.DELIVERED
        ]

    def serialize_snapshot(self) -> dict[str, Any]:
        resources = []
        for resource in self.discovered_resources():
            resources.append(
                {
                    "resource_id": resource.resource_id,
                    "position": resource.position,
                    "required_agents": resource.required_agents,
                    "value": resource.value,
                    "status": resource.status.value,
                    "assigned_team": resource.assigned_team,
                }
            )

        robots = []
        for robot in self.robots.values():
            robots.append(
                {
                    "robot_id": robot.robot_id,
                    "position": robot.position,
                    "mode": robot.mode.value,
                    "failed": robot.failed,
                    "assignment": robot.assignment,
                    "carrying_resource": robot.carrying_resource,
                }
            )

        return {
            "step": self.step_count,
            "depot": self.depot,
            "explored_ratio": len(self.explored_cells) / max(self.width * self.height - len(self.obstacles), 1),
            "resources": resources,
            "robots": robots,
        }

    def log_event(self, event_type: str, **payload: Any) -> None:
        self.event_log.append({"step": self.step_count, "event": event_type, **payload})

    def metrics_dict(self) -> dict[str, Any]:
        world_metrics = {
            "width": self.width,
            "height": self.height,
            "depot": self.depot,
            "obstacle_count": len(self.obstacles),
            "explored_cells": len(self.explored_cells),
        }
        if hasattr(self, "environment_backend"):
            world_metrics["environment_backend"] = self.environment_backend
        if hasattr(self, "environment_artifacts"):
            world_metrics["environment_artifacts"] = self.environment_artifacts

        return {
            "world": world_metrics,
            "robots": [asdict(robot) for robot in self.robots.values()],
            "resources": [asdict(resource) for resource in self.resources.values()],
            "events": self.event_log,
        }
