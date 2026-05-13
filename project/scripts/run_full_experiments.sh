#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "${PROJECT_ROOT}"

source "${PROJECT_ROOT}/scripts/bootstrap_env.sh"

python3 -m unittest discover -s tests

python3 -m src.experiments.export_stage_world --config configs/baseline.yaml --output-dir worlds --stem warehouse_base
python3 -m src.experiments.export_stage_world --config configs/high_coord.yaml --output-dir worlds --stem warehouse_high_coord

python3 -m src.experiments.run_batch \
  --config configs/baseline.yaml \
  --config configs/more_agents.yaml \
  --config configs/high_coord.yaml \
  --config configs/stress_sensing.yaml \
  --config configs/stress_failure.yaml \
  --strategy centralized \
  --strategy contract_net \
  --strategy llm \
  --seeds 20 \
  --output-dir results_openai_gpt54

python3 -m src.experiments.stats_analysis \
  --input results_openai_gpt54/processed/batch_results.csv \
  --output-dir results_openai_gpt54/processed

python3 -m src.experiments.plotting \
  --input results_openai_gpt54/processed/batch_results.csv \
  --output-dir results_openai_gpt54/figures
