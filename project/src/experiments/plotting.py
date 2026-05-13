from __future__ import annotations

import argparse
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/mplconfig_dlcw")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/xdg_cache_dlcw")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate coursework figures from batch results.")
    parser.add_argument(
        "--input",
        default="results_openai_gpt54/processed/batch_results.csv",
        help="CSV produced by run_batch.py",
    )
    parser.add_argument("--output-dir", default="results_openai_gpt54/figures", help="Directory for plot files.")
    return parser.parse_args()


def save_grouped_bar(
    frame: pd.DataFrame,
    metric: str,
    ylabel: str,
    output_path: Path,
) -> None:
    grouped = frame.groupby(["scenario", "strategy"])[metric].mean().unstack()
    ax = grouped.plot(kind="bar", figsize=(10, 5))
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Scenario")
    ax.legend(title="Strategy")
    ax.figure.tight_layout()
    ax.figure.savefig(output_path)
    plt.close(ax.figure)


def save_boxplot(frame: pd.DataFrame, metric: str, ylabel: str, output_path: Path) -> None:
    scenarios = sorted(frame["scenario"].unique())
    fig, axes = plt.subplots(1, len(scenarios), figsize=(4 * len(scenarios), 5), squeeze=False)
    for axis, scenario in zip(axes[0], scenarios, strict=True):
        subset = frame.loc[frame["scenario"] == scenario]
        data = [
            subset.loc[subset["strategy"] == strategy, metric].tolist()
            for strategy in ["centralized", "contract_net", "llm"]
        ]
        axis.boxplot(data, tick_labels=["centralized", "contract_net", "llm"])
        axis.set_title(scenario)
        axis.set_ylabel(ylabel)
        axis.tick_params(axis="x", rotation=30)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.input)

    save_boxplot(frame, "makespan", "Makespan", output_dir / "makespan_boxplots.png")
    save_grouped_bar(frame, "completion_rate", "Completion Rate", output_dir / "completion_rate_bar.png")
    save_grouped_bar(
        frame,
        "communication_messages",
        "Communication Overhead",
        output_dir / "communication_overhead_bar.png",
    )
    if "llm_token_usage" in frame.columns:
        save_grouped_bar(frame, "llm_token_usage", "Estimated Token Usage", output_dir / "llm_token_bar.png")
    print(f"Wrote figures to {output_dir}")


if __name__ == "__main__":
    main()
