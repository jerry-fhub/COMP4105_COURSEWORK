from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from src.env.grid_overlay import GridWorld
from src.env.models import ScenarioConfig


@dataclass(slots=True)
class OpenAIBackendConfig:
    api_key: str | None
    base_url: str | None
    model: str
    max_output_tokens: int


class OpenAIBackendError(RuntimeError):
    pass


class OpenAIBackend:
    def __init__(self, config: OpenAIBackendConfig) -> None:
        if not config.api_key:
            raise OpenAIBackendError("Missing OPENAI_API_KEY.")
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.base_url, timeout=45.0)

    @classmethod
    def from_environment(cls, model: str, max_output_tokens: int = 1024) -> "OpenAIBackend":
        config = OpenAIBackendConfig(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
            model=model,
            max_output_tokens=max_output_tokens,
        )
        return cls(config)

    def generate(self, world: GridWorld, config: ScenarioConfig, prompt: str) -> str:
        del world, config
        system_message = (
            "You are a coordination planner for a multi-robot resource collection task. "
            "Return ONLY valid JSON with the schema {\"assignments\": [...]} and no markdown fences, prose, or explanation outside JSON. "
            "If no valid assignment is possible, return {\"assignments\": []}. "
            "Each assignment must contain resource_id, team, priority, and optional reason."
        )
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt},
            ],
            max_tokens=self.config.max_output_tokens,
            temperature=0,
        )
        output_text = response.choices[0].message.content if response.choices else None
        if not output_text:
            raise OpenAIBackendError("OpenAI response did not contain output text.")
        return output_text

    @staticmethod
    def is_configured() -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))
