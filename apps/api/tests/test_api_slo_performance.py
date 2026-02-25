from multyagents_api.slo_performance import (
    SloPerformanceConfig,
    SloThresholds,
    run_slo_performance_suite,
)


def test_slo_performance_suite_report_passes_with_reasonable_thresholds() -> None:
    report = run_slo_performance_suite(
        config=SloPerformanceConfig(
            load_runs=4,
            soak_runs=6,
            steps_per_run=2,
            soak_sleep_ms=1,
        ),
        thresholds=SloThresholds(
            latency_p95_ms=2000.0,
            latency_p99_ms=3000.0,
            success_ratio_min=1.0,
            throughput_runs_per_sec_min=0.5,
        ),
    )

    assert report["task"] == "TASK-076"
    assert report["summary"]["overall_status"] == "pass"
    assert report["summary"]["checks_total"] == report["summary"]["checks_passed"]

    scenario_names = {scenario["name"] for scenario in report["scenarios"]}
    assert scenario_names == {"load-burst", "sustained-soak"}
    assert all(scenario["status"] == "pass" for scenario in report["scenarios"])


def test_slo_performance_suite_fails_when_thresholds_are_unrealistic() -> None:
    report = run_slo_performance_suite(
        config=SloPerformanceConfig(
            load_runs=2,
            soak_runs=2,
            steps_per_run=2,
            soak_sleep_ms=0,
        ),
        thresholds=SloThresholds(
            latency_p95_ms=0.001,
            latency_p99_ms=0.001,
            success_ratio_min=1.0,
            throughput_runs_per_sec_min=1_000_000.0,
        ),
    )

    assert report["task"] == "TASK-076"
    assert report["summary"]["overall_status"] == "fail"
    assert report["summary"]["checks_passed"] < report["summary"]["checks_total"]

    failed_checks = {
        check["id"]
        for scenario in report["scenarios"]
        for check in scenario["checks"]
        if not check["passed"]
    }
    assert "latency-p95" in failed_checks
    assert "latency-p99" in failed_checks
    assert "throughput-runs-per-sec" in failed_checks
