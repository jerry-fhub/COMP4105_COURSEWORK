from __future__ import annotations

import argparse
from pathlib import Path

from src.env.scenario_loader import load_config
from src.env.simulator import SimulationRunner
from src.experiments.metrics import records_to_frame, result_to_record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run batch experiments across scenarios, strategies and seeds.")
    parser.add_argument(
        "--config",
        action="append",
        required=True,
        help="Path to a scenario YAML. Pass multiple times for multiple scenarios.",
    )
    parser.add_argument(
        "--strategy",
        action="append",
        required=True,
        choices=["centralized", "contract_net", "llm"],
        help="Strategy to evaluate. Pass multiple times for multiple strategies.",
    )
    parser.add_argument("--seeds", type=int, default=20, help="Number of seeds starting from --seed-offset.")
    parser.add_argument("--seed-offset", type=int, default=0, help="Starting seed value.")
    parser.add_argument("--output-dir", default="results_openai_gpt54", help="Directory used for output artifacts.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "processed").mkdir(parents=True, exist_ok=True)

    records: list[dict[str, object]] = []
    for config_path in args.config:
        config = load_config(config_path)
        for strategy in args.strategy:
            for seed in range(args.seed_offset, args.seed_offset + args.seeds):
                runner = SimulationRunner(config, strategy, seed=seed, output_dir=output_dir)
                result, world = runner.run()
                runner.persist(output_dir, world, result)
                records.append(result_to_record(result))
                print(
                    f"scenario={config.name} strategy={strategy} seed={seed} "
                    f"completion={result.completion_rate:.2f} makespan={result.makespan}"
                )

    frame = records_to_frame(records)
    frame.to_csv(output_dir / "processed" / "batch_results.csv", index=False)
    print(f"Wrote {len(frame)} rows to {output_dir / 'processed' / 'batch_results.csv'}")


if __name__ == "__main__":
    main()
