from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from multyagents_api.schemas import (
    RoleCreate,
    RunnerLifecycleStatus,
    RunnerSubmission,
    TaskCreate,
    TaskStatus,
    WorkflowRunCreate,
    WorkflowRunStatus,
)
from multyagents_api.store import InMemoryStore


@dataclass(frozen=True)
class RestartPersistenceConfig:
    callback_replays: int = 2


def run_restart_persistence_invariant_suite(config: RestartPersistenceConfig | None = None) -> dict[str, Any]:
    cfg = config or RestartPersistenceConfig()
    if cfg.callback_replays < 1:
        raise ValueError("callback_replays must be >= 1")

    with TemporaryDirectory(prefix="task-073-restart-persistence-") as tmp_dir:
        state_file = Path(tmp_dir) / "api-state.json"
        scenario = _run_restart_callback_replay_scenario(state_file=state_file, config=cfg)

    invariants_total = len(scenario["invariants"])
    invariants_passed = sum(1 for invariant in scenario["invariants"] if invariant["passed"])
    overall_status = "pass" if invariants_total == invariants_passed else "fail"
    return {
        "task": "TASK-073",
        "generated_at_utc": datetime.now(tz=timezone.utc).isoformat(),
        "config": {
            "callback_replays": cfg.callback_replays,
        },
        "summary": {
            "scenario_count": 1,
            "invariants_total": invariants_total,
            "invariants_passed": invariants_passed,
            "overall_status": overall_status,
        },
        "scenarios": [scenario],
    }


def _run_restart_callback_replay_scenario(
    *,
    state_file: Path,
    config: RestartPersistenceConfig,
) -> dict[str, Any]:
    store = InMemoryStore(state_file=str(state_file))
    role = store.create_role(RoleCreate(name="task-073-restart-role", context7_enabled=True))
    task = store.create_task(
        TaskCreate(
            role_id=role.id,
            title="task-073 restart callback replay",
            execution_mode="no-workspace",
        )
    )
    run = store.create_workflow_run(
        WorkflowRunCreate(
            task_ids=[task.id],
            initiated_by="task-073-restart-persistence",
        )
    )

    store.dispatch_task(task.id)
    store.apply_runner_submission(
        task.id,
        RunnerSubmission(
            submitted=True,
            runner_url="http://runner.test",
            runner_task_status=TaskStatus.QUEUED.value,
            message="queued for restart persistence invariant scenario",
        ),
    )

    checkpoints: list[dict[str, Any]] = []
    checkpoints.append(_snapshot(store, label="queued-before-restart", run_id=run.id, task_id=task.id))

    store = InMemoryStore(state_file=str(state_file))
    checkpoints.append(_snapshot(store, label="queued-after-restart", run_id=run.id, task_id=task.id))

    store.update_task_runner_status(
        task.id,
        status=RunnerLifecycleStatus.RUNNING,
        message="runner callback: running",
    )
    checkpoints.append(_snapshot(store, label="running-before-restart", run_id=run.id, task_id=task.id))

    store = InMemoryStore(state_file=str(state_file))
    checkpoints.append(_snapshot(store, label="running-after-restart", run_id=run.id, task_id=task.id))

    store.update_task_runner_status(
        task.id,
        status=RunnerLifecycleStatus.SUCCESS,
        message="runner callback: success (first delivery)",
        exit_code=0,
    )
    checkpoints.append(_snapshot(store, label="success-first-callback", run_id=run.id, task_id=task.id))

    for replay_index in range(config.callback_replays):
        store = InMemoryStore(state_file=str(state_file))
        checkpoints.append(
            _snapshot(
                store,
                label=f"success-replay-{replay_index + 1}-before-callback",
                run_id=run.id,
                task_id=task.id,
            )
        )
        store.update_task_runner_status(
            task.id,
            status=RunnerLifecycleStatus.SUCCESS,
            message=f"runner callback: success (replay {replay_index + 1})",
            exit_code=0,
        )
        checkpoints.append(
            _snapshot(
                store,
                label=f"success-replay-{replay_index + 1}-after-callback",
                run_id=run.id,
                task_id=task.id,
            )
        )

    final_store = InMemoryStore(state_file=str(state_file))
    checkpoints.append(_snapshot(final_store, label="final-after-restart", run_id=run.id, task_id=task.id))
    invariants = _evaluate_invariants(
        store=final_store,
        run_id=run.id,
        task_id=task.id,
        checkpoints=checkpoints,
        callback_replays=config.callback_replays,
    )

    return {
        "name": "restart-callback-replay",
        "objective": "Replay runner callbacks after API restart without corrupting task/run state or dispatch history.",
        "status": "pass" if all(item["passed"] for item in invariants) else "fail",
        "callback_replays": config.callback_replays,
        "invariants": invariants,
        "checkpoints": checkpoints,
    }


def _evaluate_invariants(
    *,
    store: InMemoryStore,
    run_id: int,
    task_id: int,
    checkpoints: list[dict[str, Any]],
    callback_replays: int,
) -> list[dict[str, Any]]:
    task_status_allowed = {status.value for status in TaskStatus}
    run_status_allowed = {status.value for status in WorkflowRunStatus}
    callback_status_allowed = {status.value for status in RunnerLifecycleStatus}

    task_statuses = sorted({str(task.status.value) for task in store.list_tasks()})
    run_statuses = sorted({str(run.status.value) for run in store.list_workflow_runs()})

    runner_status_events = store.list_events(run_id=run_id, task_id=task_id, event_type="task.runner_status_updated", limit=500)
    callback_statuses = [str(event.payload.get("status")) for event in runner_status_events if "status" in event.payload]

    illegal_task_statuses = sorted(status for status in task_statuses if status not in task_status_allowed)
    illegal_run_statuses = sorted(status for status in run_statuses if status not in run_status_allowed)
    illegal_callback_statuses = sorted(
        status for status in set(callback_statuses) if status not in callback_status_allowed
    )
    no_illegal_statuses = (
        not illegal_task_statuses and not illegal_run_statuses and not illegal_callback_statuses
    )

    dispatch_events = store.list_events(run_id=run_id, event_type="task.dispatched", limit=500)
    dispatch_counts = Counter(
        event.task_id for event in dispatch_events if event.task_id is not None
    )
    duplicate_dispatch_task_ids = sorted(
        task_identifier for task_identifier, count in dispatch_counts.items() if count > 1
    )
    no_duplicate_dispatch = not duplicate_dispatch_task_ids

    checkpoint_by_label = {item["label"]: item for item in checkpoints}
    event_counts = [item["event_count"] for item in checkpoints]
    event_count_monotonic = all(
        current >= previous
        for previous, current in zip(event_counts, event_counts[1:])
    )

    queued_before = checkpoint_by_label.get("queued-before-restart")
    queued_after = checkpoint_by_label.get("queued-after-restart")
    running_before = checkpoint_by_label.get("running-before-restart")
    running_after = checkpoint_by_label.get("running-after-restart")
    final_checkpoint = checkpoint_by_label.get("final-after-restart")

    recoverability_checks = {
        "queued_state_stable_after_restart": (
            queued_before is not None
            and queued_after is not None
            and queued_before["task_status"] == TaskStatus.QUEUED.value
            and queued_after["task_status"] == TaskStatus.QUEUED.value
        ),
        "running_state_stable_after_restart": (
            running_before is not None
            and running_after is not None
            and running_before["task_status"] == TaskStatus.RUNNING.value
            and running_after["task_status"] == TaskStatus.RUNNING.value
        ),
        "final_task_status_success": (
            final_checkpoint is not None and final_checkpoint["task_status"] == TaskStatus.SUCCESS.value
        ),
        "final_run_status_success": (
            final_checkpoint is not None and final_checkpoint["run_status"] == WorkflowRunStatus.SUCCESS.value
        ),
        "event_count_monotonic_across_restarts": event_count_monotonic,
    }
    state_recoverability = all(recoverability_checks.values())

    return [
        _invariant(
            invariant_id="no-illegal-statuses",
            description="Task/run/callback statuses always stay within enum constraints after restart and replay.",
            expected={
                "task_statuses_subset_of": sorted(task_status_allowed),
                "run_statuses_subset_of": sorted(run_status_allowed),
                "callback_statuses_subset_of": sorted(callback_status_allowed),
            },
            actual={
                "task_statuses": task_statuses,
                "run_statuses": run_statuses,
                "callback_statuses": sorted(set(callback_statuses)),
                "illegal_task_statuses": illegal_task_statuses,
                "illegal_run_statuses": illegal_run_statuses,
                "illegal_callback_statuses": illegal_callback_statuses,
            },
            passed=no_illegal_statuses,
        ),
        _invariant(
            invariant_id="no-duplicate-dispatch-events",
            description="Callback replay must not generate duplicate task dispatch events.",
            expected={
                "max_dispatch_events_per_task": 1,
            },
            actual={
                "dispatch_event_count": len(dispatch_events),
                "dispatch_counts_by_task_id": {
                    str(task_identifier): count for task_identifier, count in sorted(dispatch_counts.items())
                },
                "duplicate_dispatch_task_ids": duplicate_dispatch_task_ids,
            },
            passed=no_duplicate_dispatch,
        ),
        _invariant(
            invariant_id="state-recoverability",
            description="After restart checkpoints, the run remains recoverable and converges to success after callback replay.",
            expected={
                "queued_state_stable_after_restart": True,
                "running_state_stable_after_restart": True,
                "final_task_status_success": True,
                "final_run_status_success": True,
                "event_count_monotonic_across_restarts": True,
            },
            actual={
                "callback_replays": callback_replays,
                "checks": recoverability_checks,
                "checkpoint_count": len(checkpoints),
            },
            passed=state_recoverability,
        ),
    ]


def _snapshot(store: InMemoryStore, *, label: str, run_id: int, task_id: int) -> dict[str, Any]:
    task = store.get_task(task_id)
    run = store.get_workflow_run(run_id)
    return {
        "label": label,
        "task_status": task.status.value,
        "run_status": run.status.value,
        "event_count": len(store.list_events(run_id=run_id, limit=1000)),
    }


def _invariant(
    *,
    invariant_id: str,
    description: str,
    expected: dict[str, Any],
    actual: dict[str, Any],
    passed: bool,
) -> dict[str, Any]:
    return {
        "id": invariant_id,
        "description": description,
        "expected": expected,
        "actual": actual,
        "passed": passed,
    }
