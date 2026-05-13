from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any


Position = tuple[int, int]


class RobotMode(StrEnum):
    IDLE = "idle"
    EXPLORE = "explore"
    MOVE_TO_TASK = "move_to_task"
    WAIT_FOR_TEAM = "wait_for_team"
    CARRYING = "carrying"
    FAILED = "failed"


class ResourceStatus(StrEnum):
    HIDDEN = "hidden"
    DISCOVERED = "discovered"
    ASSIGNED = "assigned"
    CARRYING = "carrying"
    DELIVERED = "delivered"


@dataclass(slots=True)
class FailureEvent:
    step: int
    robot_id: str


@dataclass(slots=True)
class ScenarioConfig:
    name: str
    width: int
    height: int
    depot: Position
    robot_count: int
    sensor_range: int
    max_steps: int
    resource_count: int
    obstacle_rectangles: list[tuple[int, int, int, int]] = field(default_factory=list)
    resource_required_agents: list[int] = field(default_factory=lambda: [1, 2, 3])
    resource_required_weights: list[float] = field(default_factory=lambda: [0.4, 0.4, 0.2])
    resource_value_range: tuple[int, int] = (5, 15)
    replan_interval: int = 3
    llm_replan_interval: int = 5
    team_timeout: int = 8
    seed: int = 0
    failure_events: list[FailureEvent] = field(default_factory=list)
    output_dir: Path = Path("results_openai_gpt54")
    environment_backend: str = "stage_world"
    cell_size_m: float = 1.0
    stage_pixels_per_cell: int = 20
    stage_smoketest: bool = False
    stage_smoketest_timeout_s: float = 3.0
    llm_backend: str = "openai"
    llm_model: str = "gpt-5.4"
    llm_cache_path: Path = Path("results_openai_gpt54/raw/llm_cache_openai_gpt54.json")
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Resource:
    resource_id: str
    position: Position
    required_agents: int
    value: int
    status: ResourceStatus = ResourceStatus.HIDDEN
    discovered_at: int | None = None
    discovered_by: str | None = None
    assigned_team: list[str] = field(default_factory=list)
    first_assignment_at: int | None = None
    team_formed_at: int | None = None
    collection_started_at: int | None = None
    delivered_at: int | None = None
    carrier_ids: list[str] = field(default_factory=list)
    reassignments: int = 0
    needs_recovery: bool = False


@dataclass(slots=True)
class Robot:
    robot_id: str
    position: Position
    sensor_range: int
    depot: Position
    mode: RobotMode = RobotMode.IDLE
    assignment: str | None = None
    carrying_resource: str | None = None
    current_target: Position | None = None
    path: list[Position] = field(default_factory=list)
    failed: bool = False
    distance_travelled: int = 0
    idle_steps: int = 0
    messages_sent: int = 0
    assignments_received: int = 0
    task_wait_start: int | None = None
    observed_resources: set[str] = field(default_factory=set)


@dataclass(slots=True)
class SimulationResult:
    strategy: str
    scenario: str
    seed: int
    max_steps: int
    environment_backend: str
    completed: bool
    completion_rate: float
    makespan: int
    delivered_resources: int
    total_resources: int
    total_collected_value: int
    average_travel_distance: float
    idle_time_ratio: float
    average_team_formation_time: float
    replans: int
    communication_messages: int
    llm_token_usage: int
    average_llm_latency_ms: float
    invalid_llm_outputs: int
    failure_recovery_time: float | None
    stage_available: bool = False
    stage_world_path: str | None = None
    stage_bitmap_path: str | None = None
    stage_manifest_path: str | None = None
    stage_smoketest_passed: bool | None = None
    notes: dict[str, Any] = field(default_factory=dict)
