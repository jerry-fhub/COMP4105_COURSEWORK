from __future__ import annotations

import random
import time

from src.agents.pathfinding import manhattan
from src.coordination.assignment_utils import assign_team, available_robots, invalidate_broken_assignments
from src.coordination.base import BaseCoordinator
from src.env.grid_overlay import GridWorld
from src.env.models import ResourceStatus, ScenarioConfig
from src.llm.cache import PromptCache
from src.llm.openai_backend import OpenAIBackend, OpenAIBackendError
from src.llm.prompt_builder import build_prompt
from src.llm.response_parser import parse_response
from src.llm.validator import filter_valid_assignments, validate_assignments


class MockLLMBackend:
    """Deterministic JSON-producing backend that mimics structured LLM outputs."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng

    def generate(self, world: GridWorld) -> str:
        available = [
            robot
            for robot in available_robots(world)
            if robot.assignment is None
        ]
        available_ids = {robot.robot_id for robot in available}
        resources = [
            resource
            for resource in world.resources.values()
            if resource.status in {ResourceStatus.DISCOVERED, ResourceStatus.ASSIGNED}
            and not resource.assigned_team
        ]
        resources.sort(
            key=lambda resource: (
                -resource.required_agents,
                -resource.value,
                resource.discovered_at or 0,
            )
        )

        assignments = []
        for priority, resource in enumerate(resources, start=1):
            if len(available_ids) < resource.required_agents:
                continue
            team = sorted(
                available_ids,
                key=lambda robot_id: (
                    world.robots[robot_id].distance_travelled,
                    robot_id,
                ),
            )[: resource.required_agents]
            if len(team) != resource.required_agents:
                continue
            for robot_id in team:
                available_ids.discard(robot_id)
            assignments.append(
                {
                    "resource_id": resource.resource_id,
                    "team": team,
                    "priority": priority,
                    "reason": "Prefer high-value collaborative tasks while keeping travel cost bounded.",
                }
            )
        import json

        return json.dumps({"assignments": assignments}, ensure_ascii=True)


class LLMCoordinator(BaseCoordinator):
    def __init__(self, config: ScenarioConfig, rng: random.Random) -> None:
        super().__init__(config, rng)
        self.cache = PromptCache(config.llm_cache_path)
        self.backend_mode = config.llm_backend
        self.backend = self._build_backend(config, rng)
        self.cache_namespace = f"{config.llm_backend}:{config.llm_model}"

    def _build_backend(self, config: ScenarioConfig, rng: random.Random):
        if config.llm_backend == "openai":
            return OpenAIBackend.from_environment(model=config.llm_model)
        return MockLLMBackend(rng)

    def _fallback(self, world: GridWorld) -> bool:
        free_robot_ids = {
            robot.robot_id
            for robot in available_robots(world)
            if robot.assignment is None
        }
        changed = False
        resources = [
            resource
            for resource in world.resources.values()
            if resource.status == ResourceStatus.DISCOVERED and not resource.assigned_team
        ]
        resources.sort(key=lambda resource: (-resource.value, resource.required_agents))
        for resource in resources:
            if len(free_robot_ids) < resource.required_agents:
                continue
            team = sorted(
                free_robot_ids,
                key=lambda robot_id: (
                    manhattan(world.robots[robot_id].position, resource.position),
                    robot_id,
                ),
            )[: resource.required_agents]
            if assign_team(world, resource, team, world.step_count):
                changed = True
                for robot_id in team:
                    free_robot_ids.discard(robot_id)
        return changed

    def step(self, world: GridWorld) -> None:
        invalidate_broken_assignments(world)
        if world.step_count % self.config.llm_replan_interval != 0:
            return

        prompt = build_prompt(world, self.config)
        cached = self.cache.get_namespaced(self.cache_namespace, prompt)
        start = time.perf_counter()
        if cached is not None:
            raw_response = cached
        else:
            try:
                if isinstance(self.backend, OpenAIBackend):
                    raw_response = self.backend.generate(world, self.config, prompt)
                else:
                    raw_response = self.backend.generate(world)
            except OpenAIBackendError:
                raise
        latency_ms = (time.perf_counter() - start) * 1000.0 + 120.0
        if cached is None:
            self.cache.put_namespaced(self.cache_namespace, prompt, raw_response)

        world.coordinator_messages += 2
        world.llm_token_usage += max(len(prompt) // 4, 1) + max(len(raw_response) // 4, 1)
        world.llm_latencies_ms.append(latency_ms)

        try:
            assignments = parse_response(raw_response)
            valid, _ = validate_assignments(world, assignments)
        except Exception:
            valid = False
            assignments = []

        changed = False
        if not valid:
            filtered = filter_valid_assignments(world, assignments)
            if filtered:
                for item in sorted(filtered, key=lambda entry: int(entry.get("priority", 999))):
                    resource = world.resources[item["resource_id"]]
                    if resource.assigned_team:
                        continue
                    team = [str(robot_id) for robot_id in item["team"]]
                    if assign_team(world, resource, team, world.step_count):
                        changed = True
                        world.coordinator_messages += len(team)
                world.invalid_llm_outputs += 1
            else:
                world.invalid_llm_outputs += 1
                changed = self._fallback(world)
        else:
            for item in sorted(assignments, key=lambda entry: int(entry.get("priority", 999))):
                resource = world.resources[item["resource_id"]]
                if resource.assigned_team:
                    continue
                team = [str(robot_id) for robot_id in item["team"]]
                if assign_team(world, resource, team, world.step_count):
                    changed = True
                    world.coordinator_messages += len(team)

        if changed:
            self.replans += 1
            world.coordinator_replans = self.replans
