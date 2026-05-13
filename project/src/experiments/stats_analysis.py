from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from scipy.stats import kruskal, mannwhitneyu


def holm_correction(p_values: list[float]) -> list[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    corrected = [0.0] * len(p_values)
    total = len(p_values)
    running_max = 0.0
    for rank, (original_index, p_value) in enumerate(indexed, start=1):
        adjusted = min(1.0, (total - rank + 1) * p_value)
        running_max = max(running_max, adjusted)
        corrected[original_index] = running_max
    return corrected


def cliffs_delta(values_a: list[float], values_b: list[float]) -> float:
    comparisons = 0
    dominance = 0
    for a in values_a:
        for b in values_b:
            comparisons += 1
            if a > b:
                dominance += 1
            elif a < b:
                dominance -= 1
    if comparisons == 0:
        return 0.0
    return dominance / comparisons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute descriptive and inferential statistics.")
    parser.add_argument(
        "--input",
        default="results_openai_gpt54/processed/batch_results.csv",
        help="CSV produced by run_batch.py",
    )
    parser.add_argument("--output-dir", default="results_openai_gpt54/processed", help="Directory for analysis outputs.")
    return parser.parse_args()


def frame_to_plain_table(frame: pd.DataFrame) -> str:
    headers = [str(column) for column in frame.columns]
    rows = [[str(value) for value in row] for row in frame.astype(object).fillna("").values.tolist()]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def format_row(values: list[str]) -> str:
        return "| " + " | ".join(value.ljust(widths[index]) for index, value in enumerate(values)) + " |"

    separator = "|-" + "-|-".join("-" * width for width in widths) + "-|"
    lines = [format_row(headers), separator]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.input)

    grouped = frame.groupby(["scenario", "strategy"])
    summary = grouped.agg(
        completion_rate_mean=("completion_rate", "mean"),
        completion_rate_std=("completion_rate", "std"),
        makespan_mean=("makespan", "mean"),
        makespan_std=("makespan", "std"),
        total_value_mean=("total_collected_value", "mean"),
        total_value_std=("total_collected_value", "std"),
        communication_messages_mean=("communication_messages", "mean"),
        average_team_formation_time_mean=("average_team_formation_time", "mean"),
        run_count=("seed", "count"),
    ).reset_index()

    ci_multiplier = 1.96
    summary["makespan_ci95"] = ci_multiplier * summary["makespan_std"].fillna(0.0) / summary["run_count"].clip(lower=1).pow(0.5)
    summary["completion_rate_ci95"] = (
        ci_multiplier * summary["completion_rate_std"].fillna(0.0) / summary["run_count"].clip(lower=1).pow(0.5)
    )
    summary_path = output_dir / "summary_statistics.csv"
    summary.to_csv(summary_path, index=False)

    significance_rows: list[dict[str, object]] = []
    for scenario, scenario_frame in frame.groupby("scenario"):
        strategies = sorted(scenario_frame["strategy"].unique())
        if len(strategies) < 2:
            continue
        samples = [scenario_frame.loc[scenario_frame["strategy"] == strategy, "makespan"].tolist() for strategy in strategies]
        valid_samples = [sample for sample in samples if sample]
        if len(valid_samples) >= 2:
            stat, p_value = kruskal(*valid_samples)
            significance_rows.append(
                {
                    "scenario": scenario,
                    "comparison": "kruskal_makespan",
                    "statistic": stat,
                    "p_value": p_value,
                    "adjusted_p_value": p_value,
                    "effect_size": "",
                }
            )

        pairwise_rows: list[dict[str, object]] = []
        pairwise_p_values: list[float] = []
        for index, strategy_a in enumerate(strategies):
            for strategy_b in strategies[index + 1 :]:
                sample_a = scenario_frame.loc[scenario_frame["strategy"] == strategy_a, "makespan"].tolist()
                sample_b = scenario_frame.loc[scenario_frame["strategy"] == strategy_b, "makespan"].tolist()
                if not sample_a or not sample_b:
                    continue
                stat, p_value = mannwhitneyu(sample_a, sample_b, alternative="two-sided")
                pairwise_rows.append(
                    {
                        "scenario": scenario,
                        "comparison": f"{strategy_a}_vs_{strategy_b}",
                        "statistic": stat,
                        "p_value": p_value,
                        "effect_size": cliffs_delta(sample_a, sample_b),
                    }
                )
                pairwise_p_values.append(p_value)

        adjusted = holm_correction(pairwise_p_values) if pairwise_p_values else []
        for row, adjusted_p in zip(pairwise_rows, adjusted, strict=True):
            row["adjusted_p_value"] = adjusted_p
            significance_rows.append(row)

    significance = pd.DataFrame(significance_rows)
    significance_path = output_dir / "significance_tests.csv"
    significance.to_csv(significance_path, index=False)

    markdown_lines = [
        "# Statistical Summary",
        "",
        f"- Input rows: {len(frame)}",
        f"- Scenarios: {frame['scenario'].nunique()}",
        f"- Strategies: {frame['strategy'].nunique()}",
        "",
        "## Summary Table",
        "",
        frame_to_plain_table(summary),
    ]
    if not significance.empty:
        markdown_lines.extend(["", "## Significance Tests", "", frame_to_plain_table(significance)])
    (output_dir / "analysis_report.md").write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    print(f"Wrote {summary_path}")
    print(f"Wrote {significance_path}")
    print(f"Wrote {output_dir / 'analysis_report.md'}")


if __name__ == "__main__":
    main()
