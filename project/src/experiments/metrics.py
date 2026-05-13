from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from src.env.models import SimulationResult


def result_to_record(result: SimulationResult) -> dict[str, object]:
    return asdict(result)


def records_to_frame(records: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame.from_records(records)
