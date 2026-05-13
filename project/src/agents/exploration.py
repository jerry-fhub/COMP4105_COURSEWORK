from __future__ import annotations

import random

from src.agents.pathfinding import manhattan
from src.env.grid_overlay import GridWorld
from src.env.models import Position, Robot


def choose_frontier_target(
    world: GridWorld,
    robot: Robot,
    claimed_targets: set[Position],
    rng: random.Random,
) -> Position | None:
    frontiers = list(world.frontier_cells())
    if not frontiers:
        unexplored = [
            (x, y)
            for x in range(world.width)
            for y in range(world.height)
            if (x, y) not in world.obstacles and (x, y) not in world.explored_cells
        ]
        if not unexplored:
            return None
        frontiers = unexplored

    def score(position: Position) -> tuple[int, int]:
        penalty = 3 if position in claimed_targets else 0
        return (manhattan(robot.position, position) + penalty, position[0] + position[1])

    frontiers.sort(key=score)
    best_score = score(frontiers[0])[0]
    best_candidates = [cell for cell in frontiers if score(cell)[0] == best_score]
    return rng.choice(best_candidates)
