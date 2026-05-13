from __future__ import annotations

import random

from src.agents.exploration import choose_frontier_target
from src.agents.pathfinding import a_star
from src.agents.worker_fsm import update_robot_mode
from src.env.grid_overlay import GridWorld
from src.env.models import Position, ResourceStatus, Robot, RobotMode


class RobotController:
    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def choose_target(
        self,
        robot: Robot,
        world: GridWorld,
        claimed_frontiers: set[Position],
    ) -> Position | None:
        update_robot_mode(robot, world)
        if robot.mode == RobotMode.FAILED:
            return None
        if robot.carrying_resource is not None:
            return world.depot
        if robot.assignment is not None:
            resource = world.resources[robot.assignment]
            if resource.status in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED, ResourceStatus.CARRYING}:
                return resource.position
        return choose_frontier_target(world, robot, claimed_frontiers, self.rng)

    def refresh_path(self, robot: Robot, world: GridWorld, target: Position | None) -> None:
        if target is None:
            robot.path = []
            robot.current_target = None
            return

        if robot.current_target == target and robot.path:
            return

        path = a_star(robot.position, target, world.neighbors)
        robot.path = path[1:] if len(path) > 1 else []
        robot.current_target = target

    def step(self, robot: Robot, world: GridWorld) -> None:
        if robot.failed:
            robot.idle_steps += 1
            return
        if not robot.path:
            robot.idle_steps += 1
            return
        next_position = robot.path.pop(0)
        if next_position != robot.position:
            robot.position = next_position
            robot.distance_travelled += 1
