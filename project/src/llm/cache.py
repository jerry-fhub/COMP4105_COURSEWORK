from __future__ import annotations

import hashlib
from pathlib import Path

from src.utils.logging_utils import load_json, write_json


class PromptCache:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: dict[str, str] = load_json(path, {})

    @staticmethod
    def key(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()

    @staticmethod
    def namespaced_key(namespace: str, prompt: str) -> str:
        payload = f"{namespace}::{prompt}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> str | None:
        return self.data.get(self.key(prompt))

    def put(self, prompt: str, response: str) -> None:
        self.data[self.key(prompt)] = response
        write_json(self.path, self.data)

    def get_namespaced(self, namespace: str, prompt: str) -> str | None:
        return self.data.get(self.namespaced_key(namespace, prompt))

    def put_namespaced(self, namespace: str, prompt: str, response: str) -> None:
        self.data[self.namespaced_key(namespace, prompt)] = response
        write_json(self.path, self.data)
