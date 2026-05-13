from __future__ import annotations

from src.env.grid_overlay import GridWorld
from src.env.models import ResourceStatus


def validate_assignments(world: GridWorld, assignments: list[dict[str, object]]) -> tuple[bool, str]:
    seen_robots: set[str] = set()
    for item in assignments:
        resource_id = item.get("resource_id")
        team = item.get("team")
        if not isinstance(resource_id, str) or resource_id not in world.resources:
            return False, f"Unknown resource_id: {resource_id}"
        if not isinstance(team, list) or not all(isinstance(robot_id, str) for robot_id in team):
            return False, f"Invalid team for resource {resource_id}"
        resource = world.resources[resource_id]
        if resource.status not in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED}:
            return False, f"Resource {resource_id} is not assignable."
        if len(team) != resource.required_agents:
            return False, f"Resource {resource_id} requires {resource.required_agents} robots, got {len(team)}."
        for robot_id in team:
            robot = world.robots.get(robot_id)
            if robot is None:
                return False, f"Unknown robot {robot_id}"
            if robot.failed or robot.carrying_resource is not None:
                return False, f"Robot {robot_id} is unavailable."
            if robot_id in seen_robots:
                return False, f"Robot {robot_id} assigned twice."
            seen_robots.add(robot_id)
    return True, "ok"


def filter_valid_assignments(world: GridWorld, assignments: list[dict[str, object]]) -> list[dict[str, object]]:
    accepted: list[dict[str, object]] = []
    seen_robots: set[str] = set()
    seen_resources: set[str] = set()
    for item in assignments:
        resource_id = item.get("resource_id")
        team = item.get("team")
        if not isinstance(resource_id, str) or resource_id not in world.resources:
            continue
        if resource_id in seen_resources:
            continue
        if not isinstance(team, list) or not all(isinstance(robot_id, str) for robot_id in team):
            continue
        resource = world.resources[resource_id]
        if resource.status not in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED}:
            continue
        if resource.assigned_team:
            continue
        if len(team) != resource.required_agents:
            continue
        valid_team = True
        for robot_id in team:
            robot = world.robots.get(robot_id)
            if robot is None or robot.failed or robot.carrying_resource is not None or robot.assignment is not None:
                valid_team = False
                break
            if robot_id in seen_robots:
                valid_team = False
                break
        if not valid_team:
            continue
        accepted.append(item)
        seen_resources.add(resource_id)
        seen_robots.update(team)
    return accepted
