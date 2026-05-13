from __future__ import annotations

import random
from abc import ABC, abstractmethod

from src.env.grid_overlay import GridWorld
from src.env.models import ScenarioConfig


class BaseCoordinator(ABC):
    def __init__(self, config: ScenarioConfig, rng: random.Random) -> None:
        self.config = config
        self.rng = rng
        self.last_plan_step = -1
        self.replans = 0

    @abstractmethod
    def step(self, world: GridWorld) -> None:
        raise NotImplementedError
