from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("chaos_e2e_failure_drills.py")
SPEC = importlib.util.spec_from_file_location("chaos_e2e_failure_drills", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"unable to load module spec from {MODULE_PATH}")
chaos = importlib.util.module_from_spec(SPEC)
sys.modules["chaos_e2e_failure_drills"] = chaos
SPEC.loader.exec_module(chaos)


class RunnerPortFromUrlTests(unittest.TestCase):
    def test_returns_none_for_empty_url(self) -> None:
        self.assertIsNone(chaos.runner_port_from_url(""))

    def test_returns_explicit_port_from_url(self) -> None:
        self.assertEqual(chaos.runner_port_from_url("http://127.0.0.1:48070/health"), 48070)

    def test_returns_none_when_port_not_present(self) -> None:
        self.assertIsNone(chaos.runner_port_from_url("http://localhost/health"))


class BuildSummaryTests(unittest.TestCase):
    def test_build_summary_marks_success_when_all_passed(self) -> None:
        results = [
            chaos.ScenarioResult("s1", "one", "success", {"id": 1}),
            chaos.ScenarioResult("s2", "two", "success", {"id": 2}),
        ]

        summary = chaos.build_summary(results, api_base="http://localhost:48000")

        self.assertEqual(summary["summary"]["overall_status"], "success")
        self.assertEqual(summary["summary"]["total"], 2)
        self.assertEqual(summary["summary"]["success"], 2)
        self.assertEqual(summary["summary"]["failed"], 0)

    def test_build_summary_counts_failed_scenarios(self) -> None:
        results = [
            chaos.ScenarioResult("s1", "one", "success", {"id": 1}),
            chaos.ScenarioResult("s2", "two", "failed", {"id": 2}, error="boom"),
        ]

        summary = chaos.build_summary(results, api_base="http://localhost:48000")

        self.assertEqual(summary["summary"]["overall_status"], "failed")
        self.assertEqual(summary["summary"]["total"], 2)
        self.assertEqual(summary["summary"]["success"], 1)
        self.assertEqual(summary["summary"]["failed"], 1)
        self.assertEqual(summary["scenarios"][1]["error"], "boom")


if __name__ == "__main__":
    unittest.main()
