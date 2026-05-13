from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.env.scenario_loader import load_config
from src.env.simulator import SimulationRunner


class SimulationTests(unittest.TestCase):
    def test_single_run_produces_metrics(self) -> None:
        config = load_config(Path("configs") / "baseline.yaml")
        with TemporaryDirectory() as tmp_dir:
            runner = SimulationRunner(config, "centralized", seed=7, output_dir=tmp_dir)
            result, _ = runner.run()
            self.assertEqual(result.strategy, "centralized")
            self.assertEqual(result.environment_backend, "stage_world")
            self.assertGreaterEqual(result.completion_rate, 0.0)
            self.assertLessEqual(result.completion_rate, 1.0)
            self.assertGreater(result.makespan, 0)
            self.assertTrue(Path(result.stage_world_path).exists())
            self.assertTrue(Path(result.stage_bitmap_path).exists())
            self.assertTrue(Path(result.stage_manifest_path).exists())


if __name__ == "__main__":
    unittest.main()
