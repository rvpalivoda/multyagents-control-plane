#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_evidence_paths() -> tuple[Path, Path]:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_dir = _repo_root() / "docs" / "evidence" / "task-076"
    return (
        base_dir / f"task-076-slo-performance-{timestamp}.json",
        base_dir / f"task-076-slo-performance-{timestamp}.md",
    )


def parse_args() -> argparse.Namespace:
    default_json, default_md = _default_evidence_paths()
    parser = argparse.ArgumentParser(description="Run TASK-076 SLO load/soak suite and write evidence.")
    parser.add_argument("--output-json", type=Path, default=default_json, help="path to JSON evidence output")
    parser.add_argument("--output-md", type=Path, default=default_md, help="path to Markdown evidence output")
    parser.add_argument("--load-runs", type=int, default=16, help="number of load scenario runs")
    parser.add_argument("--soak-runs", type=int, default=60, help="number of soak scenario runs")
    parser.add_argument("--steps-per-run", type=int, default=3, help="workflow steps per run")
    parser.add_argument("--soak-sleep-ms", type=int, default=20, help="delay between soak runs in ms")
    parser.add_argument("--latency-p95-ms", type=float, default=250.0, help="p95 latency threshold in ms")
    parser.add_argument("--latency-p99-ms", type=float, default=500.0, help="p99 latency threshold in ms")
    parser.add_argument("--success-ratio-min", type=float, default=0.99, help="minimum success ratio")
    parser.add_argument(
        "--throughput-runs-per-sec-min",
        type=float,
        default=2.0,
        help="minimum throughput in successful workflow runs per second",
    )
    return parser.parse_args()


def _render_markdown(report: dict[str, Any], json_path: Path) -> str:
    summary = report["summary"]
    lines: list[str] = []
    lines.append("# TASK-076 SLO Performance and Soak Evidence")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at_utc']}`")
    lines.append(f"- Python: `{report['python']}`")
    lines.append(f"- JSON evidence: `{json_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Overall status: `{summary['overall_status']}`")
    lines.append(f"- Scenarios: `{summary['scenario_count']}`")
    lines.append(f"- Threshold checks passed: `{summary['checks_passed']}/{summary['checks_total']}`")
    lines.append("")

    lines.append("## Thresholds")
    lines.append("")
    for key, value in report["thresholds"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")

    for scenario in report["scenarios"]:
        metrics = scenario["metrics"]
        lat = metrics["latency_ms"]

        lines.append(f"## Scenario: {scenario['name']}")
        lines.append("")
        lines.append(f"- Objective: {scenario['objective']}")
        lines.append(f"- Status: `{scenario['status']}`")
        lines.append(f"- Runs: `{metrics['successful_runs']}/{metrics['run_count']}` successful")
        lines.append(f"- Throughput (runs/sec): `{round(metrics['throughput_runs_per_sec'], 3)}`")
        lines.append(f"- Throughput (requests/sec): `{round(metrics['throughput_requests_per_sec'], 3)}`")
        lines.append(
            "- Latency (ms): "
            f"count=`{int(lat['count'])}`, p95=`{lat['p95']}`, p99=`{lat['p99']}`, avg=`{lat['avg']}`"
        )
        lines.append("")
        lines.append("### Threshold checks")
        lines.append("")
        for check in scenario["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            lines.append(
                f"- `{marker}` {check['id']}: {check['actual']} {check['operator']} {check['threshold']}"
            )
        lines.append("")

    lines.append("## Config")
    lines.append("")
    for key, value in report["config"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    try:
        from multyagents_api.slo_performance import (
            SloPerformanceConfig,
            SloThresholds,
            run_slo_performance_suite,
        )
    except ModuleNotFoundError as exc:
        print(f"[task-076] missing dependency: {exc.name}", file=sys.stderr)
        print("[task-076] install API dependencies before running the suite:", file=sys.stderr)
        print("  cd apps/api && python3 -m venv .venv && .venv/bin/pip install -e .[dev]", file=sys.stderr)
        return 2

    try:
        report = run_slo_performance_suite(
            config=SloPerformanceConfig(
                load_runs=args.load_runs,
                soak_runs=args.soak_runs,
                steps_per_run=args.steps_per_run,
                soak_sleep_ms=args.soak_sleep_ms,
            ),
            thresholds=SloThresholds(
                latency_p95_ms=args.latency_p95_ms,
                latency_p99_ms=args.latency_p99_ms,
                success_ratio_min=args.success_ratio_min,
                throughput_runs_per_sec_min=args.throughput_runs_per_sec_min,
            ),
        )
    except ValueError as exc:
        print(f"[task-076] invalid configuration: {exc}", file=sys.stderr)
        return 2

    report["python"] = platform.python_version()

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(_render_markdown(report, args.output_json) + "\n", encoding="utf-8")

    print(f"[task-076] evidence json: {args.output_json}")
    print(f"[task-076] evidence md:   {args.output_md}")
    print(f"[task-076] summary:       {report['summary']}")
    return 0 if report["summary"]["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
