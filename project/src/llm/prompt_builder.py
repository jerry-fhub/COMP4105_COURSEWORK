from __future__ import annotations

import json

from src.env.grid_overlay import GridWorld
from src.env.models import ScenarioConfig


def build_prompt(world: GridWorld, config: ScenarioConfig) -> str:
    snapshot = world.serialize_snapshot()
    instructions = {
        "objective": "Assign robots to discovered resources to maximise delivered value while respecting required team sizes.",
        "constraints": [
            "Only assign non-failed robots.",
            "A robot may appear in at most one team.",
            "Each team size must equal the resource required_agents value.",
            "Prefer shorter travel distance but allow higher-value collaborative resources to be prioritised.",
        ],
        "output_schema": {
            "assignments": [
                {"resource_id": "res_00", "team": ["robot_0", "robot_1"], "priority": 1}
            ]
        },
        "state": snapshot,
        "llm_model": config.llm_model,
    }
    return json.dumps(instructions, separators=(",", ":"), ensure_ascii=True)
