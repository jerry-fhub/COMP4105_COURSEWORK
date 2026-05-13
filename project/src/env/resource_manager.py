from __future__ import annotations

import random

from src.env.models import Resource, ScenarioConfig


def generate_resources(
    config: ScenarioConfig,
    obstacle_cells: set[tuple[int, int]],
    rng: random.Random,
) -> dict[str, Resource]:
    """Generate hidden resources on valid free cells."""
    resources: dict[str, Resource] = {}
    used_cells = {config.depot, *obstacle_cells}
    min_value, max_value = config.resource_value_range

    for index in range(config.resource_count):
        while True:
            candidate = (rng.randrange(config.width), rng.randrange(config.height))
            if candidate in used_cells:
                continue
            used_cells.add(candidate)
            break

        required_agents = rng.choices(
            population=config.resource_required_agents,
            weights=config.resource_required_weights,
            k=1,
        )[0]
        value = rng.randint(min_value, max_value) + (required_agents - 1) * 2
        resource_id = f"res_{index:02d}"
        resources[resource_id] = Resource(
            resource_id=resource_id,
            position=candidate,
            required_agents=required_agents,
            value=value,
        )

    return resources
