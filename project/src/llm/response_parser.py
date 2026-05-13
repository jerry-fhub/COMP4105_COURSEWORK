from __future__ import annotations

import json


def parse_response(raw_response: str) -> list[dict[str, object]]:
    payload = json.loads(raw_response)
    assignments = payload.get("assignments", [])
    if not isinstance(assignments, list):
        raise ValueError("LLM response does not contain a list under 'assignments'.")
    parsed: list[dict[str, object]] = []
    for item in assignments:
        if not isinstance(item, dict):
            raise ValueError("Each assignment must be a JSON object.")
        parsed.append(item)
    return parsed
