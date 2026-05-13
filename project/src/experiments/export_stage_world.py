from __future__ import annotations

import argparse
from pathlib import Path

from src.env.scenario_loader import build_world, load_config
from src.env.stage_interface import StageInterface


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a concrete Stage world for a scenario config.")
    parser.add_argument("--config", required=True, help="Path to scenario YAML config.")
    parser.add_argument("--output-dir", default="worlds", help="Directory for exported Stage assets.")
    parser.add_argument("--stem", default=None, help="Output filename stem. Defaults to warehouse_<scenario>.")
    parser.add_argument("--seed", type=int, default=None, help="Override the config seed for resource placement.")
    parser.add_argument("--smoke-test", action="store_true", help="Launch Stage headless to validate the export.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    seed = config.seed if args.seed is None else args.seed
    world = build_world(config, seed=seed)
    stem = args.stem or f"warehouse_{config.name}"
    bundle = StageInterface.materialize_assets(
        config,
        world,
        Path(args.output_dir),
        stem,
        smoke_test=args.smoke_test,
    )
    print(f"Exported {bundle.world_path}")
    print(f"Bitmap   {bundle.bitmap_path}")
    print(f"Manifest {bundle.manifest_path}")
    if bundle.smoke_test_ran:
        print(f"Smoke test passed={bundle.smoke_test_passed} return_code={bundle.smoke_test_return_code}")


if __name__ == "__main__":
    main()
