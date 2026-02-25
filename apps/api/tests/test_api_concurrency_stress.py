from multyagents_api.concurrency_stress import ConcurrencyStressConfig, run_concurrency_stress_suite


def test_concurrency_stress_suite_report_invariants_pass() -> None:
    report = run_concurrency_stress_suite(
        ConcurrencyStressConfig(
            dispatch_iterations=2,
            dispatch_parallelism=4,
            dispatch_task_count=8,
            rerun_iterations=2,
            rerun_parallelism=4,
            rerun_attempts=10,
            approval_iterations=2,
            approval_parallelism=4,
            approval_attempts=24,
        )
    )

    assert report["task"] == "TASK-072"
    assert report["summary"]["overall_status"] == "pass"
    assert report["summary"]["invariants_total"] == report["summary"]["invariants_passed"]

    scenario_names = {scenario["name"] for scenario in report["scenarios"]}
    assert scenario_names == {
        "parallel-dispatch-race",
        "partial-rerun-race",
        "approval-dispatch-race",
    }
    assert all(scenario["status"] == "pass" for scenario in report["scenarios"])
