import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.controller import server
from app.controller.system_log import EventStore
from benchmarks.standard_suite import (
    STANDARD_CATEGORIES, build_smoke_suite, build_standard_suite, SMOKE_CASE_IDS,
)

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT / "app" / "interface"


class FakeThread:
    instances = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True


class StandardSuiteTests(unittest.TestCase):
    def test_suite_has_ten_unique_categories_and_valid_gold_evidence(self):
        suite = build_standard_suite()
        self.assertEqual([case["category"] for case in suite], STANDARD_CATEGORIES)
        self.assertEqual(len({case["case_id"] for case in suite}), 10)
        for case in suite:
            for quote in case["expected_evidence"]:
                self.assertIn(quote, case["source"], case["case_id"])

    def test_smoke_suite_is_the_fixed_minimal_subsets_of_the_standard_suite(self):
        standard = {case["case_id"]: case for case in build_standard_suite()}
        smoke = build_smoke_suite()
        self.assertEqual([case["case_id"] for case in smoke], list(SMOKE_CASE_IDS))
        self.assertEqual(set(SMOKE_CASE_IDS), {case["case_id"] for case in smoke})
        self.assertLess(set(SMOKE_CASE_IDS), set(standard))
        for case in smoke:
            self.assertEqual(case, standard[case["case_id"]])
            for quote in case["expected_evidence"]:
                self.assertIn(quote, case["source"], case["case_id"])
            self.assertTrue(case["criteria"], case["case_id"])


class StandardBenchmarkTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Job tests must not append events to the real system event log.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch.object(
            server, "SYSTEM_EVENTS", EventStore(Path(directory.name) / "system_events.jsonl"),
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_full_mode_uses_all_local_models_and_fixed_independent_evaluator(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={
                    "answer-model": "digest-answer", server.STANDARD_EVALUATOR_MODEL: "digest-evaluator",
                }), \
                patch.object(server, "STANDARD_JOB_EVENTS") as events, \
                patch.object(server, "Thread", FakeThread):
            job = server.start_standard_benchmark("full")
        self.assertEqual(job["mode"], "full")
        self.assertEqual(job["models"], ["answer-model", server.STANDARD_EVALUATOR_MODEL])
        self.assertEqual(job["evaluator_model"], server.STANDARD_EVALUATOR_MODEL)
        self.assertEqual(job["categories"], STANDARD_CATEGORIES)
        self.assertEqual(job["budgets"], server.STANDARD_BUDGETS)
        self.assertEqual(job["repeat_count"], 3)
        self.assertEqual(job["total_comparisons"], 2 * 10 * 5)
        self.assertEqual(job["total_strategy_runs"], 2 * 10 * 5 * 3 * 2)
        self.assertEqual(job["estimated_model_calls"], 1200)
        self.assertTrue(FakeThread.instances[0].started)
        self.assertEqual(FakeThread.instances[0].kwargs["args"], (
            job["job_id"], ["answer-model", server.STANDARD_EVALUATOR_MODEL],
            server.STANDARD_EVALUATOR_MODEL, build_standard_suite(), server.STANDARD_BUDGETS, 3, "full",
        ))
        events.append.assert_called_once()

    def test_default_mode_preserves_the_full_profile(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={
                    "answer-model": "digest-answer", server.STANDARD_EVALUATOR_MODEL: "digest-evaluator",
                }), \
                patch.object(server, "STANDARD_JOB_EVENTS"), \
                patch.object(server, "Thread", FakeThread):
            job = server.start_standard_benchmark()
        self.assertEqual(job["mode"], "full")
        self.assertEqual(job["repeat_count"], 3)
        self.assertEqual(job["models"], ["answer-model", server.STANDARD_EVALUATOR_MODEL])

    def test_smoke_mode_runs_minimal_pipeline_configuration(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={
                    "answer-model": "digest-answer", server.STANDARD_EVALUATOR_MODEL: "digest-evaluator",
                }), \
                patch.object(server, "STANDARD_JOB_EVENTS") as events, \
                patch.object(server, "Thread", FakeThread):
            job = server.start_standard_benchmark("smoke")
        self.assertEqual(job["mode"], "smoke")
        self.assertEqual(job["models"], ["answer-model"])
        self.assertNotIn(server.STANDARD_EVALUATOR_MODEL, job["models"])
        self.assertEqual(job["evaluator_model"], server.STANDARD_EVALUATOR_MODEL)
        self.assertEqual(job["categories"], ["Factual retrieval", "Missing information"])
        self.assertEqual(job["budgets"], [server.SMOKE_BUDGET])
        self.assertEqual(job["repeat_count"], 1)
        self.assertEqual(job["total_comparisons"], 2)
        self.assertEqual(job["total_strategy_runs"], 4)
        self.assertEqual(job["estimated_model_calls"], 10)
        self.assertTrue(FakeThread.instances[0].started)
        self.assertEqual(FakeThread.instances[0].kwargs["args"], (
            job["job_id"], ["answer-model"], server.STANDARD_EVALUATOR_MODEL,
            build_smoke_suite(), [server.SMOKE_BUDGET], 1, "smoke",
        ))
        events.append.assert_called_once()

    def test_smoke_mode_falls_back_to_the_evaluator_as_beyond_answer_model(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={server.STANDARD_EVALUATOR_MODEL: "digest"}), \
                patch.object(server, "STANDARD_JOB_EVENTS"), \
                patch.object(server, "Thread", FakeThread):
            job = server.start_standard_benchmark("smoke")
        self.assertEqual(job["models"], [server.STANDARD_EVALUATOR_MODEL])
        self.assertEqual(job["estimated_model_calls"], 6)

    def test_single_pass_mode_runs_every_configuration_once(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={
                    "answer-model": "digest-answer", server.STANDARD_EVALUATOR_MODEL: "digest-evaluator",
                }), \
                patch.object(server, "STANDARD_JOB_EVENTS"), \
                patch.object(server, "Thread", FakeThread):
            job = server.start_standard_benchmark("single_pass")
        self.assertEqual(job["mode"], "single_pass")
        self.assertEqual(job["models"], ["answer-model", server.STANDARD_EVALUATOR_MODEL])
        self.assertEqual(job["categories"], STANDARD_CATEGORIES)
        self.assertEqual(job["budgets"], server.STANDARD_BUDGETS)
        self.assertEqual(job["repeat_count"], 1)
        self.assertEqual(job["total_comparisons"], 2 * 10 * 5)
        self.assertEqual(job["total_strategy_runs"], 2 * 10 * 5 * 1 * 2)
        self.assertEqual(job["estimated_model_calls"], 400)

    def test_unknown_mode_is_rejected_without_starting_a_job(self):
        FakeThread.instances.clear()
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={server.STANDARD_EVALUATOR_MODEL: "digest"}), \
                patch.object(server, "STANDARD_JOB_EVENTS") as events, \
                patch.object(server, "Thread", FakeThread):
            with self.assertRaisesRegex(ValueError, "smoke, single_pass, or full"):
                server.start_standard_benchmark("mystery")
        self.assertEqual(FakeThread.instances, [])
        events.append.assert_not_called()

    def test_standard_job_does_not_substitute_for_missing_fixed_evaluator(self):
        with patch.object(server, "STANDARD_JOB", None), \
                patch.object(server, "model_catalog", return_value={"some-other-model": "digest"}), \
                patch.object(server, "STANDARD_JOB_EVENTS") as events:
            for mode in server.STANDARD_MODES:
                with self.assertRaisesRegex(ValueError, "fixed independent evaluator"):
                    server.start_standard_benchmark(mode)
        events.append.assert_not_called()

    def test_smoke_job_thread_runs_smoke_payloads_with_single_repeats(self):
        comparison_payloads = []

        def fake_comparison(payload):
            comparison_payloads.append(dict(payload))
            return {"runs": [
                {"response": "answer", "error": None, "criterion_evaluation": {"status": "complete"}},
                {"response": None, "error": "offline", "criterion_evaluation": {"status": "not_run"}},
            ]}

        job_state = {"job_id": "job-smoke", "status": "running", "failures": []}
        finished_events = []
        with patch.object(server, "STANDARD_JOB", job_state), \
                patch.object(server, "STANDARD_JOB_EVENTS", finished_events), \
                patch.object(server, "execute_comparison", side_effect=fake_comparison):
            server._run_standard_job(
                "job-smoke", ["answer-model"], server.STANDARD_EVALUATOR_MODEL,
                build_smoke_suite(), [server.SMOKE_BUDGET], 1, "smoke",
            )
        self.assertEqual(len(comparison_payloads), 2)
        self.assertEqual({payload["benchmark_case_id"] for payload in comparison_payloads}, set(SMOKE_CASE_IDS))
        for payload in comparison_payloads:
            self.assertEqual(payload["repeat_count"], 1)
            self.assertEqual(payload["benchmark_mode"], "smoke")
            self.assertEqual(payload["context_budget"], server.SMOKE_BUDGET)
            self.assertEqual(payload["benchmark_suite_version"], "standard-suite-v1")
            self.assertTrue(payload["run_model"])
            self.assertEqual(payload["model"], "answer-model")
            self.assertEqual(payload["evaluation_model"], server.STANDARD_EVALUATOR_MODEL)
            self.assertTrue(payload["independent_evaluator_required"])
            self.assertTrue(payload["expand_sources"])
        events = {event["event"] for event in finished_events}
        self.assertEqual(events, {"completed"})
        self.assertEqual(job_state["completed_comparisons"], 2)


class StandardBenchmarkInterfaceTests(unittest.TestCase):
    def test_mode_selector_offers_the_three_documented_modes(self):
        html = (UI_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="standard-mode"', html)
        self.assertIn('<option value="smoke">Smoke Test', html)
        self.assertIn('<option value="single_pass">Single-Pass Test', html)
        self.assertIn('<option value="full">Full Standard Benchmark', html)
        for element_id in ("standard-mode-description", "standard-estimate", "standard-repetitions"):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn('id="run-standard-benchmark"', html)

    def test_interface_describes_and_sends_the_selected_mode(self):
        script = (UI_ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('$("#standard-mode").addEventListener("change"', script)
        self.assertIn('const mode = $("#standard-mode").value;', script)
        self.assertIn("body:JSON.stringify({mode})", script)
        for phrase in ("Pipeline verification:", "Moderate evaluation:", "Complete benchmark:", "not statistically robust."):
            self.assertIn(phrase, script)
        self.assertIn("standardSmokeAnswerModel", script)
        self.assertIn('STANDARD_MODE_NAMES[job.mode]', script)


if __name__ == "__main__":
    unittest.main()
