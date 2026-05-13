#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "${PROJECT_ROOT}"

source "${PROJECT_ROOT}/scripts/stage_env.sh" >/dev/null

python3 - <<'PY'
from __future__ import annotations

import os
import subprocess
from pathlib import Path

project_root = Path(os.environ["PROJECT_ROOT"])
stage_binary = Path(os.environ["STAGE_ROOT"]) / "bin" / "stage"
world_path = project_root / "worlds" / "warehouse_base.world"

try:
    subprocess.run(
        [str(stage_binary), "-g", str(world_path)],
        check=False,
        timeout=3,
    )
except subprocess.TimeoutExpired:
    pass
PY
