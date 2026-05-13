from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.env.scenario_loader import build_world, load_config
from src.env.stage_interface import StageInterface


class StageInterfaceTests(unittest.TestCase):
    def test_stage_assets_are_generated(self) -> None:
        config = load_config(Path("configs") / "baseline.yaml")
        world = build_world(config, seed=3)

        with TemporaryDirectory() as tmp_dir:
            bundle = StageInterface.materialize_assets(config, world, tmp_dir, "baseline_seed3")
            self.assertTrue(bundle.world_path.exists())
            self.assertTrue(bundle.bitmap_path.exists())
            self.assertTrue(bundle.manifest_path.exists())
            world_text = bundle.world_path.read_text(encoding="utf-8")
            self.assertIn('include "pioneer.inc"', world_text)
            self.assertIn('name "depot"', world_text)
            self.assertIn('name "robot_0"', world_text)
            self.assertIn("resource_marker(", world_text)

    @unittest.skipUnless(StageInterface.is_available(), "Stage binary not installed in this environment.")
    def test_generated_world_passes_stage_smoketest(self) -> None:
        config = load_config(Path("configs") / "baseline.yaml")
        world = build_world(config, seed=4)

        with TemporaryDirectory() as tmp_dir:
            bundle = StageInterface.materialize_assets(
                config,
                world,
                tmp_dir,
                "baseline_seed4",
                smoke_test=True,
            )
            self.assertTrue(bundle.smoke_test_ran)
            self.assertTrue(bundle.smoke_test_passed, msg=bundle.smoke_test_output)


if __name__ == "__main__":
    unittest.main()
