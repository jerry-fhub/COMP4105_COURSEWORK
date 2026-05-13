from __future__ import annotations

import random
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.agents.robot_agent import RobotController
from src.coordination.centralized_planner import CentralizedPlanner
from src.coordination.contract_net import ContractNetCoordinator
from src.coordination.llm_coordinator import LLMCoordinator
from src.env.grid_overlay import GridWorld
from src.env.models import ResourceStatus, RobotMode, ScenarioConfig, SimulationResult
from src.env.scenario_loader import build_world
from src.env.stage_interface import StageArtifactBundle, StageInterface
from src.utils.logging_utils import write_json
from src.utils.seeds import seed_everything


def make_coordinator(strategy: str, config: ScenarioConfig, rng: random.Random):
    if strategy == "centralized":
        return CentralizedPlanner(config, rng)
    if strategy == "contract_net":
        return ContractNetCoordinator(config, rng)
    if strategy == "llm":
        return LLMCoordinator(config, rng)
    raise ValueError(f"Unsupported strategy: {strategy}")


class SimulationRunner:
    def __init__(
        self,
        config: ScenarioConfig,
        strategy: str,
        seed: int | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        self.seed = config.seed if seed is None else seed
        self.rng = seed_everything(self.seed)
        self.config = config
        self.strategy = strategy
        self.output_dir = Path(config.output_dir if output_dir is None else output_dir)
        self.world = build_world(config, self.seed)
        self.world.environment_backend = config.environment_backend
        self.coordinator = make_coordinator(strategy, config, self.rng)
        self.controller = RobotController(self.rng)
        self.stage_artifacts = self._materialize_environment_artifacts()
        self.world.environment_artifacts = self.stage_artifacts.as_dict()

    def _materialize_environment_artifacts(self) -> StageArtifactBundle:
        stem = f"{self.config.name}_{self.strategy}_seed{self.seed}"
        asset_dir = self.output_dir / "stage" / self.config.name / self.strategy
        return StageInterface.materialize_assets(
            self.config,
            self.world,
            asset_dir,
            stem,
            smoke_test=self.config.stage_smoketest,
        )

    def _apply_failures(self) -> None:
        for event in self.config.failure_events:
            if event.step != self.world.step_count:
                continue
            robot = self.world.robots[event.robot_id]
            robot.failed = True
            robot.mode = RobotMode.FAILED
            robot.path = []
            robot.current_target = None
            self.world.failure_step = self.world.step_count
            self.world.log_event("robot_failed", robot_id=robot.robot_id)

    def _perceive(self) -> None:
        for robot in self.world.robots.values():
            if robot.failed:
                continue
            self.world.perceive(robot)

    def _plan_targets(self) -> None:
        claimed_frontiers: set[tuple[int, int]] = set()
        for robot in self.world.robots.values():
            target = self.controller.choose_target(robot, self.world, claimed_frontiers)
            if target is not None and robot.assignment is None and robot.carrying_resource is None:
                claimed_frontiers.add(target)
            self.controller.refresh_path(robot, self.world, target)

    def _move_robots(self) -> None:
        for robot in self.world.robots.values():
            self.controller.step(robot, self.world)

    def _check_team_formations(self) -> None:
        for resource in self.world.resources.values():
            if resource.status != ResourceStatus.ASSIGNED:
                continue
            team = [self.world.robots[robot_id] for robot_id in resource.assigned_team]
            if len(team) != resource.required_agents:
                continue
            ready = [robot for robot in team if not robot.failed and robot.position == resource.position]
            if len(ready) != resource.required_agents:
                continue
            resource.status = ResourceStatus.CARRYING
            resource.carrier_ids = list(resource.assigned_team)
            resource.team_formed_at = self.world.step_count
            resource.collection_started_at = self.world.step_count
            for robot in ready:
                robot.carrying_resource = resource.resource_id
                robot.current_target = self.world.depot
                robot.path = []
            self.world.log_event("resource_collected", resource_id=resource.resource_id, team=resource.carrier_ids)

    def _check_deliveries(self) -> None:
        for resource in self.world.resources.values():
            if resource.status != ResourceStatus.CARRYING:
                continue
            carriers = [self.world.robots[robot_id] for robot_id in resource.carrier_ids]
            if not carriers:
                continue
            if all(not robot.failed and robot.position == self.world.depot for robot in carriers):
                resource.status = ResourceStatus.DELIVERED
                resource.delivered_at = self.world.step_count
                for robot in carriers:
                    robot.assignment = None
                    robot.carrying_resource = None
                    robot.current_target = None
                    robot.path = []
                self.world.log_event("resource_delivered", resource_id=resource.resource_id, team=resource.carrier_ids)
                resource.carrier_ids = []
                resource.assigned_team = []

    def run(self) -> tuple[SimulationResult, GridWorld]:
        self._perceive()
        for step in range(self.config.max_steps):
            self.world.step_count = step
            self._apply_failures()
            self._perceive()
            self.coordinator.step(self.world)
            self._plan_targets()
            self._move_robots()
            self._check_team_formations()
            self._check_deliveries()
            if all(resource.status == ResourceStatus.DELIVERED for resource in self.world.resources.values()):
                break

        result = self._result()
        return result, self.world

    def _result(self) -> SimulationResult:
        delivered = [resource for resource in self.world.resources.values() if resource.status == ResourceStatus.DELIVERED]
        team_formation_times = [
            resource.team_formed_at - resource.first_assignment_at
            for resource in delivered
            if resource.team_formed_at is not None and resource.first_assignment_at is not None
        ]
        travel_distances = [robot.distance_travelled for robot in self.world.robots.values()]
        idle_steps = sum(robot.idle_steps for robot in self.world.robots.values())
        total_steps = max((self.world.step_count + 1) * len(self.world.robots), 1)
        result = SimulationResult(
            strategy=self.strategy,
            scenario=self.config.name,
            seed=self.seed,
            max_steps=self.config.max_steps,
            environment_backend=self.config.environment_backend,
            completed=len(delivered) == len(self.world.resources),
            completion_rate=len(delivered) / len(self.world.resources),
            makespan=self.world.step_count + 1,
            delivered_resources=len(delivered),
            total_resources=len(self.world.resources),
            total_collected_value=sum(resource.value for resource in delivered),
            average_travel_distance=sum(travel_distances) / len(travel_distances),
            idle_time_ratio=idle_steps / total_steps,
            average_team_formation_time=(
                sum(team_formation_times) / len(team_formation_times) if team_formation_times else 0.0
            ),
            replans=self.world.coordinator_replans + sum(resource.reassignments for resource in self.world.resources.values()),
            communication_messages=self.world.coordinator_messages,
            llm_token_usage=self.world.llm_token_usage,
            average_llm_latency_ms=(
                sum(self.world.llm_latencies_ms) / len(self.world.llm_latencies_ms)
                if self.world.llm_latencies_ms
                else 0.0
            ),
            invalid_llm_outputs=self.world.invalid_llm_outputs,
            failure_recovery_time=(
                None
                if self.world.failure_step is None or self.world.recovery_step is None
                else float(self.world.recovery_step - self.world.failure_step)
            ),
            stage_available=self.stage_artifacts.stage_available,
            stage_world_path=str(self.stage_artifacts.world_path),
            stage_bitmap_path=str(self.stage_artifacts.bitmap_path),
            stage_manifest_path=str(self.stage_artifacts.manifest_path),
            stage_smoketest_passed=self.stage_artifacts.smoke_test_passed,
            notes={
                "explored_ratio": len(self.world.explored_cells)
                / max(self.world.width * self.world.height - len(self.world.obstacles), 1),
                "stage_smoke_test_ran": self.stage_artifacts.smoke_test_ran,
                "stage_smoke_test_return_code": self.stage_artifacts.smoke_test_return_code,
            },
        )
        return result

    def persist(self, output_dir: str | Path, world: GridWorld, result: SimulationResult) -> None:
        base = Path(output_dir)
        stem = f"{result.scenario}_{result.strategy}_seed{result.seed}"
        write_json(base / "raw" / f"{stem}_summary.json", asdict(result))
        write_json(base / "raw" / f"{stem}_trace.json", world.metrics_dict())
