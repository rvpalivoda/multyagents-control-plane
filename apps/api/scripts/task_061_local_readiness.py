#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@contextmanager
def _stub_runner_submit() -> Any:
    import multyagents_api.runner_client as runner_client

    submissions: list[dict[str, Any]] = []

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, str]:
            return {"status": "queued"}

    def fake_post(url: str, **kwargs: Any) -> _Response:
        if not url.endswith("/tasks/submit"):
            raise RuntimeError(f"unexpected runner call from local readiness script: {url}")
        payload = kwargs.get("json")
        submissions.append(payload if isinstance(payload, dict) else {})
        return _Response()

    previous_post = runner_client.httpx.post
    previous_runner_url = os.environ.get("HOST_RUNNER_URL")

    runner_client.httpx.post = fake_post
    os.environ["HOST_RUNNER_URL"] = "http://runner.test"
    try:
        yield submissions
    finally:
        runner_client.httpx.post = previous_post
        if previous_runner_url is None:
            os.environ.pop("HOST_RUNNER_URL", None)
        else:
            os.environ["HOST_RUNNER_URL"] = previous_runner_url


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_evidence_paths() -> tuple[Path, Path]:
    timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base_dir = _repo_root() / "docs" / "evidence" / "task-061"
    return (
        base_dir / f"task-061-local-readiness-{timestamp}.json",
        base_dir / f"task-061-local-readiness-{timestamp}.md",
    )


def _render_markdown(report: dict[str, Any], json_path: Path, submissions: list[dict[str, Any]]) -> str:
    generated_at = report["generated_at_utc"]
    summary = report["summary"]
    lines: list[str] = []
    lines.append("# TASK-061 Local Readiness Evidence")
    lines.append("")
    lines.append(f"- Generated at (UTC): `{generated_at}`")
    lines.append(f"- Python: `{report['python']}`")
    lines.append(f"- Runner submit calls (stubbed): `{len(submissions)}`")
    lines.append(f"- JSON evidence: `{json_path}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Overall status: `{summary['overall_status']}`")
    lines.append(f"- Total scenarios: `{summary['total']}`")
    lines.append(f"- Success: `{summary['success']}`")
    lines.append(f"- Expected pending: `{summary['expected_pending']}`")
    lines.append("")

    for scenario in report["scenarios"]:
        lines.append(f"## Scenario {scenario['scenario']}: {scenario['name']}")
        lines.append("")
        lines.append(f"- Status: `{scenario['status']}`")
        if "run_id" in scenario:
            lines.append(f"- Run ID: `{scenario['run_id']}`")
        if "run_status" in scenario:
            lines.append(f"- Run status: `{scenario['run_status']}`")
        if scenario["scenario"] == "A":
            lines.append(f"- Task IDs: `{scenario['task_ids']}`")

        if scenario["scenario"] == "B":
            lines.append(f"- Failed run ID: `{scenario['failed_run_id']}`")
            lines.append(f"- Failed task ID: `{scenario['failed_task_id']}`")
            lines.append(f"- Failed run status: `{scenario['failed_run_status']}`")
            lines.append(f"- Partial rerun HTTP status: `{scenario['partial_rerun_http_status']}`")
            triage = scenario.get("triage", {})
            lines.append(f"- Triage category: `{triage.get('failure_category')}`")
            lines.append(f"- Triage hints: `{triage.get('failure_triage_hints', [])}`")
            lines.append(f"- Suggested next actions: `{triage.get('suggested_next_actions', [])}`")
            if scenario["status"] == "expected_pending":
                lines.append(f"- Pending reason: `{scenario['pending_reason']}`")
                if "fallback_recovery_run_id" in scenario:
                    lines.append(f"- Fallback recovery run ID: `{scenario['fallback_recovery_run_id']}`")
                    lines.append(f"- Fallback recovery run status: `{scenario['fallback_recovery_run_status']}`")
                if "rerun_run_id" in scenario:
                    lines.append(f"- Partial rerun run ID: `{scenario['rerun_run_id']}`")
                    lines.append(f"- Partial rerun run status: `{scenario.get('rerun_status')}`")

        if scenario["scenario"] == "C":
            lines.append(f"- Plan task ID: `{scenario['plan_task_id']}`")
            lines.append(f"- Report task ID: `{scenario['report_task_id']}`")
            lines.append(f"- Approval ID: `{scenario['approval_id']}`")
            lines.append(f"- Handoff artifact ID: `{scenario['handoff_artifact_id']}`")
            lines.append(f"- Retry summary: `{scenario['run_retry_summary']}`")
            lines.append(f"- Failure categories: `{scenario['run_failure_categories']}`")
            lines.append(f"- Event sample: `{scenario['events_sample']}`")

        lines.append("")

    lines.append("## Actionable Follow-up")
    lines.append("")
    lines.append("- If Scenario B is `expected_pending`, inspect partial rerun policy for no-ready-tasks handling and decide whether to auto-dispatch or operator-review.")
    lines.append("- Keep Scenario C in CI because it covers the critical approval+handoff+retry interaction surface.")
    lines.append("")

    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    default_json, default_md = _default_evidence_paths()

    parser = argparse.ArgumentParser(description="Run TASK-061 local readiness scenarios and write evidence docs.")
    parser.add_argument("--initiated-by", default="task-061-readiness-script", help="workflow initiated_by value")
    parser.add_argument("--output-json", type=Path, default=default_json, help="path to JSON evidence output")
    parser.add_argument("--output-md", type=Path, default=default_md, help="path to Markdown evidence output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from fastapi.testclient import TestClient

        from multyagents_api.local_readiness import run_local_readiness_scenarios
        from multyagents_api.main import app
    except ModuleNotFoundError as exc:
        print(f"[task-061] missing dependency: {exc.name}", file=sys.stderr)
        print("[task-061] install API dependencies before running readiness scenarios:", file=sys.stderr)
        print(
            "  cd apps/api && python3 -m venv .venv && .venv/bin/pip install -e .[dev]",
            file=sys.stderr,
        )
        return 2

    with _stub_runner_submit() as submissions:
        with TestClient(app) as client:
            report = run_local_readiness_scenarios(client, initiated_by=args.initiated_by)

    report["generated_at_utc"] = datetime.now(tz=timezone.utc).isoformat()
    report["python"] = platform.python_version()
    report["runner_submit_calls"] = len(submissions)

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)

    args.output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.output_md.write_text(_render_markdown(report, args.output_json, submissions) + "\n", encoding="utf-8")

    print(f"[task-061] evidence json: {args.output_json}")
    print(f"[task-061] evidence md:   {args.output_md}")
    print(f"[task-061] summary:      {report['summary']}")

    if report["summary"]["overall_status"] != "success":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
