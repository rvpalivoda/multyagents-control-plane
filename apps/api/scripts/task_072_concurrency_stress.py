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
    base_dir = _repo_root() / "docs" / "evidence" / "task-072"
    return (
        base_dir / f"task-072-concurrency-stress-{timestamp}.json",
        base_dir / f"task-072-concurrency-stress-{timestamp}.md",
    )


def parse_args() -> argparse.Namespace:
    default_json, default_md = _default_evidence_paths()
    parser = argparse.ArgumentParser(description="Run TASK-072 concurrency stress suite and write evidence files.")
    parser.add_argument("--output-json", type=Path, default=default_json, help="path to JSON evidence output")
    parser.add_argument("--output-md", type=Path, default=default_md, help="path to Markdown evidence output")
    parser.add_argument("--dispatch-iterations", type=int, default=4)
    parser.add_argument("--dispatch-parallelism", type=int, default=8)
    parser.add_argument("--dispatch-task-count", type=int, default=12)
    parser.add_argument("--rerun-iterations", type=int, default=4)
    parser.add_argument("--rerun-parallelism", type=int, default=8)
    parser.add_argument("--rerun-attempts", type=int, default=16)
    parser.add_argument("--approval-iterations", type=int, default=4)
    parser.add_argument("--approval-parallelism", type=int, default=8)
    parser.add_argument("--approval-attempts", type=int, default=50)
    return parser.parse_args()


def _render_markdown(report: dict[str, Any], json_path: Path) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("# TASK-072 Concurrency and Race Stress Evidence")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{report['generated_at_utc']}`")
    lines.append(f"- Python: `{report['python']}`")
    lines.append(f"- JSON evidence: `{json_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Overall status: `{summary['overall_status']}`")
    lines.append(f"- Scenarios: `{summary['scenario_count']}`")
    lines.append(f"- Invariants passed: `{summary['invariants_passed']}/{summary['invariants_total']}`")
    lines.append("")

    for scenario in report["scenarios"]:
        lines.append(f"## Scenario: {scenario['name']}")
        lines.append("")
        lines.append(f"- Objective: {scenario['objective']}")
        lines.append(f"- Status: `{scenario['status']}`")
        lines.append(f"- Iterations: `{scenario['iterations']}`")
        lines.append("")
        lines.append("### Invariants")
        lines.append("")
        for invariant in scenario["invariants"]:
            marker = "PASS" if invariant["passed"] else "FAIL"
            lines.append(f"- `{marker}` {invariant['id']}: {invariant['description']}")
            if not invariant["passed"]:
                lines.append(f"  failures: `{invariant['actual_failures']}`")
        lines.append("")

    lines.append("## Config")
    lines.append("")
    for key, value in report["config"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()

    if min(
        args.dispatch_iterations,
        args.dispatch_parallelism,
        args.dispatch_task_count,
        args.rerun_iterations,
        args.rerun_parallelism,
        args.rerun_attempts,
        args.approval_iterations,
        args.approval_parallelism,
        args.approval_attempts,
    ) < 1:
        print("[task-072] all numeric options must be >= 1", file=sys.stderr)
        return 2

    try:
        from multyagents_api.concurrency_stress import ConcurrencyStressConfig, run_concurrency_stress_suite
    except ModuleNotFoundError as exc:
        print(f"[task-072] missing dependency: {exc.name}", file=sys.stderr)
        print("[task-072] install API dependencies before running the stress suite:", file=sys.stderr)
        print("  cd apps/api && python3 -m venv .venv && .venv/bin/pip install -e .[dev]", file=sys.stderr)
        return 2

    config = ConcurrencyStressConfig(
        dispatch_iterations=args.dispatch_iterations,
        dispatch_parallelism=args.dispatch_parallelism,
        dispatch_task_count=args.dispatch_task_count,
        rerun_iterations=args.rerun_iterations,
        rerun_parallelism=args.rerun_parallelism,
        rerun_attempts=args.rerun_attempts,
        approval_iterations=args.approval_iterations,
        approval_parallelism=args.approval_parallelism,
        approval_attempts=args.approval_attempts,
    )
    report = run_concurrency_stress_suite(config)
    report["python"] = platform.python_version()

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(_render_markdown(report, args.output_json) + "\n", encoding="utf-8")

    print(f"[task-072] evidence json: {args.output_json}")
    print(f"[task-072] evidence md:   {args.output_md}")
    print(f"[task-072] summary:       {report['summary']}")

    return 0 if report["summary"]["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
