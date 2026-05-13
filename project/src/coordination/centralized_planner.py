from __future__ import annotations

import random

from src.coordination.assignment_utils import (
    assign_team,
    available_robots,
    greedy_resource_order,
    invalidate_broken_assignments,
    select_nearest_team,
)
from src.coordination.base import BaseCoordinator
from src.env.grid_overlay import GridWorld
from src.env.models import ScenarioConfig


class CentralizedPlanner(BaseCoordinator):
    def __init__(self, config: ScenarioConfig, rng: random.Random) -> None:
        super().__init__(config, rng)

    def step(self, world: GridWorld) -> None:
        invalidate_broken_assignments(world)
        if world.step_count % self.config.replan_interval != 0:
            world.coordinator_messages += len(world.robots)
            return

        free_robot_ids = {robot.robot_id for robot in available_robots(world) if robot.assignment is None}
        planning_changed = False
        for resource in greedy_resource_order(world):
            if resource.assigned_team:
                continue
            team = select_nearest_team(world, resource, free_robot_ids)
            if len(team) != resource.required_agents:
                continue
            if assign_team(world, resource, team, world.step_count):
                planning_changed = True
                for robot_id in team:
                    free_robot_ids.discard(robot_id)

        world.coordinator_messages += len(world.robots)
        if planning_changed:
            self.replans += 1
            world.coordinator_replans = self.replans
            world.coordinator_messages += sum(len(resource.assigned_team) for resource in world.resources.values())
