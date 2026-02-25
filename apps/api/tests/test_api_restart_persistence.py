from multyagents_api.restart_persistence import (
    RestartPersistenceConfig,
    run_restart_persistence_invariant_suite,
)


def test_restart_persistence_suite_report_invariants_pass() -> None:
    report = run_restart_persistence_invariant_suite(
        RestartPersistenceConfig(
            callback_replays=2,
        )
    )

    assert report["task"] == "TASK-073"
    assert report["summary"]["overall_status"] == "pass"
    assert report["summary"]["invariants_total"] == report["summary"]["invariants_passed"]

    scenario_names = {scenario["name"] for scenario in report["scenarios"]}
    assert scenario_names == {"restart-callback-replay"}
    assert all(scenario["status"] == "pass" for scenario in report["scenarios"])


def test_restart_persistence_suite_tracks_replay_recoverability() -> None:
    callback_replays = 3
    report = run_restart_persistence_invariant_suite(
        RestartPersistenceConfig(
            callback_replays=callback_replays,
        )
    )
    scenario = report["scenarios"][0]
    invariants = {item["id"]: item for item in scenario["invariants"]}

    assert scenario["callback_replays"] == callback_replays
    assert invariants["state-recoverability"]["passed"] is True
    assert invariants["state-recoverability"]["actual"]["callback_replays"] == callback_replays
    assert invariants["no-duplicate-dispatch-events"]["passed"] is True
    assert invariants["no-duplicate-dispatch-events"]["actual"]["duplicate_dispatch_task_ids"] == []
