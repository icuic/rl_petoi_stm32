#!/usr/bin/env python3
"""Rank policy checkpoints from evaluation JSON reports."""

from __future__ import annotations

import argparse
import glob
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RankedReport:
    rank: int
    report: str
    model: str
    checkpoint: str
    episodes: int
    fall_rate: float
    distance_x_mean: float
    distance_x_std: float
    reward_mean: float
    reward_std: float
    steps_mean: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "reports",
        nargs="+",
        help="Evaluation report paths or glob patterns.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Optional JSON path for the ranked result.",
    )
    parser.add_argument(
        "--min-episodes",
        type=int,
        default=1,
        help="Ignore reports with fewer than this many episodes.",
    )
    parser.add_argument(
        "--allow-falls",
        action="store_true",
        help="Include reports with fall_rate > 0. By default they are excluded.",
    )
    return parser.parse_args()


def expand_report_paths(patterns: list[str]) -> list[Path]:
    paths: list[Path] = []
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            paths.extend(Path(match) for match in matches)
        else:
            paths.append(Path(pattern))
    return sorted(set(paths))


def load_report(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        report = json.load(f)
    if not isinstance(report, dict):
        raise ValueError(f"Report must be a JSON object: {path}")
    if "summary" not in report or not isinstance(report["summary"], dict):
        raise ValueError(f"Report is missing summary object: {path}")
    return report


def checkpoint_label(report: dict[str, Any], report_path: Path) -> str:
    model = str(report.get("model") or "")
    source = Path(model).name if model else report_path.stem
    match = re.search(r"_(\d+)_steps\.zip$", source)
    if match:
        return match.group(1)
    if source == "final_model.zip" or report_path.stem.endswith("_eval"):
        return "final"
    return source.removesuffix(".zip")


def make_row(report_path: Path, report: dict[str, Any]) -> RankedReport:
    summary = report["summary"]
    episodes = report.get("episodes", [])
    return RankedReport(
        rank=0,
        report=str(report_path),
        model=str(report.get("model") or ""),
        checkpoint=checkpoint_label(report, report_path),
        episodes=len(episodes) if isinstance(episodes, list) else 0,
        fall_rate=float(summary.get("fall_rate", 1.0)),
        distance_x_mean=float(summary.get("distance_x_mean", float("-inf"))),
        distance_x_std=float(summary.get("distance_x_std", float("inf"))),
        reward_mean=float(summary.get("reward_mean", float("-inf"))),
        reward_std=float(summary.get("reward_std", float("inf"))),
        steps_mean=float(summary.get("steps_mean", 0.0)),
    )


def sort_key(row: RankedReport) -> tuple[float, float, float, float, float]:
    return (
        row.fall_rate,
        -row.distance_x_mean,
        row.distance_x_std,
        -row.reward_mean,
        -row.steps_mean,
    )


def format_markdown(rows: list[RankedReport]) -> str:
    lines = [
        "| Rank | Checkpoint | Episodes | Fall rate | Mean distance x | Distance std | Reward mean | Report |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row.rank} | "
            f"`{row.checkpoint}` | "
            f"{row.episodes} | "
            f"{row.fall_rate:.3f} | "
            f"{row.distance_x_mean:.4f} | "
            f"{row.distance_x_std:.4f} | "
            f"{row.reward_mean:.4f} | "
            f"`{row.report}` |"
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    rows: list[RankedReport] = []
    for path in expand_report_paths(args.reports):
        report = load_report(path)
        row = make_row(path, report)
        if row.episodes < args.min_episodes:
            continue
        if not args.allow_falls and row.fall_rate > 0.0:
            continue
        rows.append(row)

    ranked = [
        RankedReport(rank=index, **{key: value for key, value in asdict(row).items() if key != "rank"})
        for index, row in enumerate(sorted(rows, key=sort_key), start=1)
    ]

    if not ranked:
        raise SystemExit("No reports matched the selection criteria.")

    best = ranked[0]
    output = {
        "best": asdict(best),
        "ranked": [asdict(row) for row in ranked],
        "sort_order": ["fall_rate asc", "distance_x_mean desc", "distance_x_std asc", "reward_mean desc"],
    }

    print("Best checkpoint:")
    print(json.dumps(output["best"], indent=2))
    print()
    print(format_markdown(ranked))

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        with args.output_json.open("w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
            f.write("\n")
        print()
        print(f"Saved ranked checkpoint report to {args.output_json}")


if __name__ == "__main__":
    main()
