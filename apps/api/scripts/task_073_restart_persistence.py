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
    base_dir = _repo_root() / "docs" / "evidence" / "task-073"
    return (
        base_dir / f"task-073-restart-persistence-{timestamp}.json",
        base_dir / f"task-073-restart-persistence-{timestamp}.md",
    )


def parse_args() -> argparse.Namespace:
    default_json, default_md = _default_evidence_paths()
    parser = argparse.ArgumentParser(description="Run TASK-073 restart persistence invariant suite and write evidence.")
    parser.add_argument("--output-json", type=Path, default=default_json, help="path to JSON evidence output")
    parser.add_argument("--output-md", type=Path, default=default_md, help="path to Markdown evidence output")
    parser.add_argument("--callback-replays", type=int, default=2, help="number of success callback replays")
    return parser.parse_args()


def _render_markdown(report: dict[str, Any], json_path: Path) -> str:
    lines: list[str] = []
    summary = report["summary"]
    lines.append("# TASK-073 Restart Persistence Invariant Evidence")
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
        lines.append(f"- Callback replays: `{scenario['callback_replays']}`")
        lines.append("")
        lines.append("### Invariants")
        lines.append("")
        for invariant in scenario["invariants"]:
            marker = "PASS" if invariant["passed"] else "FAIL"
            lines.append(f"- `{marker}` {invariant['id']}: {invariant['description']}")
        lines.append("")
        lines.append("### Checkpoints")
        lines.append("")
        for checkpoint in scenario["checkpoints"]:
            lines.append(
                "- "
                f"`{checkpoint['label']}` "
                f"(task=`{checkpoint['task_status']}`, run=`{checkpoint['run_status']}`, "
                f"events=`{checkpoint['event_count']}`)"
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
    if args.callback_replays < 1:
        print("[task-073] callback-replays must be >= 1", file=sys.stderr)
        return 2

    try:
        from multyagents_api.restart_persistence import (
            RestartPersistenceConfig,
            run_restart_persistence_invariant_suite,
        )
    except ModuleNotFoundError as exc:
        print(f"[task-073] missing dependency: {exc.name}", file=sys.stderr)
        print("[task-073] install API dependencies before running the suite:", file=sys.stderr)
        print("  cd apps/api && python3 -m venv .venv && .venv/bin/pip install -e .[dev]", file=sys.stderr)
        return 2

    report = run_restart_persistence_invariant_suite(
        RestartPersistenceConfig(callback_replays=args.callback_replays)
    )
    report["python"] = platform.python_version()

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(_render_markdown(report, args.output_json) + "\n", encoding="utf-8")

    print(f"[task-073] evidence json: {args.output_json}")
    print(f"[task-073] evidence md:   {args.output_md}")
    print(f"[task-073] summary:       {report['summary']}")
    return 0 if report["summary"]["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
