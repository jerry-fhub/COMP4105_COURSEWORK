# Multi-Agent Coordination in Resource Collection

This submission branch keeps only the code, reproducibility assets, and final experimental results for the COMP3004/COMP4105 coursework project.

All project files live under `project/`.

## Repository Layout

- `project/src/`: implementation code
- `project/configs/`: scenario definitions used in the experiments
- `project/worlds/`: bundled Stage maps, demo worlds, floorplans, and manifests
- `project/scripts/`: environment/bootstrap and experiment helper scripts
- `project/results_openai_gpt54/`: final GPT-based experiment outputs used in the report and presentation
- `project/tests/`: regression tests
- `project/requirements.txt`: Python dependencies

## Installation

Use Python 3.11+:

```bash
cd project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## LLM Configuration

The repository does not store any API key or endpoint in code.

```bash
export OPENAI_API_KEY="your_key_here"
export OPENAI_BASE_URL="your_openai_compatible_base_url"
```

`OPENAI_BASE_URL` is optional unless you are using an OpenAI-compatible gateway.

## Running

Run tests:

```bash
cd project
python3 -m unittest discover -s tests
```

Run one simulation:

```bash
cd project
python3 -m src.experiments.run_single --config configs/baseline.yaml --strategy centralized --seed 0 --output-dir results_openai_gpt54
```

Run the full batch:

```bash
cd project
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
```

Recompute analysis outputs:

```bash
cd project
python3 -m src.experiments.stats_analysis \
  --input results_openai_gpt54/processed/batch_results.csv \
  --output-dir results_openai_gpt54/processed

python3 -m src.experiments.plotting \
  --input results_openai_gpt54/processed/batch_results.csv \
  --output-dir results_openai_gpt54/figures
```

## Notes

- The final reported experimental artifacts are already included in `project/results_openai_gpt54/`.
- The repository keeps the map/configuration assets required to reproduce the Stage world exports.
- On macOS, the Python simulator runs without a local Stage installation; Stage visualization and smoke tests remain optional.
