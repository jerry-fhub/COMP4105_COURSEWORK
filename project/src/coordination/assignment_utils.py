from __future__ import annotations

from collections.abc import Iterable

from src.agents.pathfinding import manhattan
from src.env.grid_overlay import GridWorld
from src.env.models import Resource, ResourceStatus, Robot


def available_robots(world: GridWorld) -> list[Robot]:
    robots = []
    for robot in world.robots.values():
        if robot.failed or robot.carrying_resource is not None:
            continue
        robots.append(robot)
    return robots


def assignment_signature(resource: Resource) -> tuple[str, tuple[str, ...]]:
    return (resource.resource_id, tuple(sorted(resource.assigned_team)))


def invalidate_broken_assignments(world: GridWorld) -> None:
    for resource in world.resources.values():
        if resource.status == ResourceStatus.DELIVERED:
            continue
        if resource.status == ResourceStatus.CARRYING:
            failed_carrier = any(world.robots[robot_id].failed for robot_id in resource.carrier_ids)
            if not failed_carrier:
                continue
            for robot_id in list(resource.carrier_ids):
                robot = world.robots[robot_id]
                if robot.carrying_resource == resource.resource_id:
                    robot.carrying_resource = None
                    robot.assignment = None
                    robot.current_target = None
                    robot.path = []
            resource.status = ResourceStatus.DISCOVERED
            resource.assigned_team = []
            resource.carrier_ids = []
            resource.needs_recovery = True
            resource.reassignments += 1
            world.log_event("resource_dropped", resource_id=resource.resource_id)
            continue

        if resource.status == ResourceStatus.ASSIGNED:
            team = [robot_id for robot_id in resource.assigned_team if not world.robots[robot_id].failed]
            if len(team) == resource.required_agents:
                continue
            for robot_id in list(resource.assigned_team):
                robot = world.robots[robot_id]
                if robot.assignment == resource.resource_id:
                    robot.assignment = None
                    robot.current_target = None
                    robot.path = []
            resource.assigned_team = []
            resource.status = ResourceStatus.DISCOVERED
            resource.needs_recovery = True
            resource.reassignments += 1
            world.log_event("assignment_invalidated", resource_id=resource.resource_id)


def select_nearest_team(
    world: GridWorld,
    resource: Resource,
    candidate_robot_ids: Iterable[str],
) -> list[str]:
    candidates = list(candidate_robot_ids)
    candidates.sort(
        key=lambda robot_id: (
            manhattan(world.robots[robot_id].position, resource.position),
            world.robots[robot_id].distance_travelled,
            robot_id,
        )
    )
    return candidates[: resource.required_agents]


def assign_team(
    world: GridWorld,
    resource: Resource,
    team: list[str],
    step: int,
) -> bool:
    if len(team) != resource.required_agents:
        return False

    current_signature = assignment_signature(resource)
    next_signature = (resource.resource_id, tuple(sorted(team)))
    if current_signature == next_signature:
        return False

    for robot_id in list(resource.assigned_team):
        robot = world.robots[robot_id]
        if robot.assignment == resource.resource_id:
            robot.assignment = None
            robot.current_target = None
            robot.path = []

    resource.assigned_team = list(team)
    resource.status = ResourceStatus.ASSIGNED
    if resource.first_assignment_at is None:
        resource.first_assignment_at = step
    elif current_signature[1] and current_signature != next_signature:
        resource.reassignments += 1

    for robot_id in team:
        robot = world.robots[robot_id]
        robot.assignment = resource.resource_id
        robot.assignments_received += 1
        robot.current_target = resource.position
        robot.path = []

    if resource.needs_recovery and world.failure_step is not None and world.recovery_step is None:
        world.recovery_step = step
        resource.needs_recovery = False

    world.log_event("team_assigned", resource_id=resource.resource_id, team=team)
    return True


def greedy_resource_order(world: GridWorld) -> list[Resource]:
    candidates = [
        resource
        for resource in world.resources.values()
        if resource.status in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED}
    ]
    available = {robot.robot_id for robot in available_robots(world)}

    def score(resource: Resource) -> tuple[float, int]:
        if len(available) < resource.required_agents:
            return (-1.0, resource.required_agents)
        team = select_nearest_team(world, resource, available)
        if len(team) < resource.required_agents:
            return (-1.0, resource.required_agents)
        distance = sum(manhattan(world.robots[robot_id].position, resource.position) for robot_id in team)
        utility = resource.value / (distance + resource.required_agents)
        return (utility, -resource.required_agents)

    return sorted(candidates, key=score, reverse=True)
