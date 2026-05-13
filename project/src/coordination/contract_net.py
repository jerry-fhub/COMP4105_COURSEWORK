from __future__ import annotations

import random

from src.agents.pathfinding import manhattan
from src.coordination.assignment_utils import assign_team, available_robots, invalidate_broken_assignments
from src.coordination.base import BaseCoordinator
from src.env.grid_overlay import GridWorld
from src.env.models import ResourceStatus, ScenarioConfig


class ContractNetCoordinator(BaseCoordinator):
    def __init__(self, config: ScenarioConfig, rng: random.Random) -> None:
        super().__init__(config, rng)

    def step(self, world: GridWorld) -> None:
        invalidate_broken_assignments(world)
        free_robots = [robot for robot in available_robots(world) if robot.assignment is None]
        free_robot_ids = {robot.robot_id for robot in free_robots}
        if not free_robot_ids:
            return

        auction_resources = [
            resource
            for resource in world.resources.values()
            if resource.status == ResourceStatus.DISCOVERED and not resource.assigned_team
        ]
        auction_resources.sort(key=lambda resource: (resource.discovered_at or 0, -resource.value))

        changed = False
        for resource in auction_resources:
            if len(free_robot_ids) < resource.required_agents:
                continue
            manager = resource.discovered_by or min(free_robot_ids)
            eligible = list(free_robot_ids)
            world.coordinator_messages += len(eligible)  # CFP
            bids = sorted(
                eligible,
                key=lambda robot_id: (
                    manhattan(world.robots[robot_id].position, resource.position),
                    0 if robot_id == manager else 1,
                    robot_id,
                ),
            )
            world.coordinator_messages += len(eligible)  # bids
            winners = bids[: resource.required_agents]
            if assign_team(world, resource, winners, world.step_count):
                changed = True
                world.coordinator_messages += len(winners)  # awards
                for robot_id in winners:
                    free_robot_ids.discard(robot_id)

        if changed:
            self.replans += 1
            world.coordinator_replans = self.replans
