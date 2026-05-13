from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from src.env.scenario_loader import load_config
from src.env.simulator import SimulationRunner
from src.utils.logging_utils import write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a single multi-agent coordination simulation.")
    parser.add_argument("--config", required=True, help="Path to scenario YAML config.")
    parser.add_argument(
        "--strategy",
        required=True,
        choices=["centralized", "contract_net", "llm"],
        help="Coordination strategy to run.",
    )
    parser.add_argument("--seed", type=int, default=None, help="Override config seed.")
    parser.add_argument("--output-dir", default="results_openai_gpt54", help="Directory used for run artifacts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    runner = SimulationRunner(config, args.strategy, args.seed, output_dir=args.output_dir)
    result, world = runner.run()
    runner.persist(args.output_dir, world, result)
    print(asdict(result))


if __name__ == "__main__":
    main()
