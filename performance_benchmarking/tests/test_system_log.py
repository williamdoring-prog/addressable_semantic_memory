import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from app.controller import server
from app.controller.system_log import EventStore
from app.controller.storage import ResultStore


def temporary_event_store(case, **kwargs) -> EventStore:
    directory = tempfile.TemporaryDirectory()
    case.addCleanup(directory.cleanup)
    return EventStore(Path(directory.name) / "system_events.jsonl", **kwargs)


class EventRecordTests(unittest.TestCase):
    def test_record_contains_required_fields_and_alert_flag_by_severity(self):
        store = temporary_event_store(self)
        info = store.record("info", "http", "invalid_request", "Rejected payload.")
        error = store.record("error", "http", "unhandled_request_error", "Request failed.")
        critical = store.record("critical", "storage", "run_storage_failed", "Persist failed.")
        for event in (info, error, critical):
            for field in ("event_id", "timestamp", "severity", "component", "event_type", "message"):
                self.assertTrue(event[field], field)
            self.assertIsInstance(event["event_id"], str)
        self.assertEqual(info["alert"], False)
        self.assertEqual(error["alert"], True)
        self.assertEqual(critical["alert"], True)
        self.assertEqual(info["severity"], "info")

    def test_details_are_recorded_and_unknown_values_degrade_to_strings(self):
        store = temporary_event_store(self)
        event = store.record("info", "http", "check", "message", {"ok": 1, "bad": {1, 2}})
        self.assertEqual(event["details"]["ok"], 1)
        self.assertIsInstance(event["details"]["bad"], str)
        self.assertEqual(event["traceback"], None)

    def test_error_records_capture_traceback_of_raised_exception(self):
        store = temporary_event_store(self)
        try:
            raise RuntimeError("boom")
        except RuntimeError as exc:
            event = store.record("error", "asm-engine", "semantic_validation_failed", "validation failed", exc=exc)
        self.assertIn("RuntimeError: boom", event["traceback"])
        self.assertLessEqual(len(event["traceback"]), 4000)

    def test_every_event_is_mirrored_to_stderr(self):
        store = temporary_event_store(self)
        with redirect_stderr(io.StringIO()) as mirror:
            event = store.record("warning", "storage", "malformed_result_line", "Skipped a line.")
        output = mirror.getvalue()
        self.assertIn("WARNING", output)
        self.assertIn("storage/malformed_result_line", output)
        self.assertIn("Skipped a line.", output)
        self.assertIn(event["timestamp"], output)

    def test_write_failure_falls_back_to_stderr_without_raising(self):
        with tempfile.TemporaryDirectory() as directory:
            # A directory cannot be opened for appending, so the store write fails.
            store = EventStore(Path(directory))
            with redirect_stderr(io.StringIO()) as mirror:
                event = store.record("info", "http", "check", "log file unavailable")
        self.assertEqual(event["event_type"], "check")
        self.assertIn("SYSTEM LOG WRITE FAILED", mirror.getvalue())
        self.assertIn("http/check", mirror.getvalue())


class EscalationTests(unittest.TestCase):
    def _error(self, store, component="criterion-evaluator", event_type="criterion_evaluation_failed"):
        return store.record("error", component, event_type, "failure recorded", {"component": component})

    def test_repeated_failures_raise_one_escalation_per_window(self):
        store = temporary_event_store(self, repeat_threshold=3, repeat_window_minutes=15)
        for _ in range(3):
            self._error(store)
        records = store.list_events(limit=10)
        escalations = [record for record in records if record.get("alert_type")]
        self.assertEqual(len(escalations), 1)
        escalation = escalations[0]
        self.assertEqual(escalation["severity"], "critical")
        self.assertEqual(escalation["alert_type"], "repeat_failures")
        self.assertEqual(escalation["component"], "criterion-evaluator")
        self.assertEqual(escalation["details"]["repeat_count"], 3)
        self.assertEqual(escalation["details"]["watched_event_type"], "criterion_evaluation_failed")
        self.assertIn("3 repeated criterion_evaluation_failed failures", escalation["message"])
        # A further failure inside the window raises no second escalation.
        self._error(store)
        escalations = [record for record in store.list_events(limit=20) if record.get("alert_type")]
        self.assertEqual(len(escalations), 1)

    def test_escalation_window_reset_allows_a_fresh_alert(self):
        store = temporary_event_store(self, repeat_threshold=2, repeat_window_minutes=15)
        for _ in range(2):
            self._error(store)
        state = store._streaks[("criterion-evaluator", "criterion_evaluation_failed")]
        state["window_start"] = state["window_start"] - timedelta(minutes=30)
        self._error(store)
        escalating_errors = [record for record in store.list_events(limit=20) if record.get("alert")]
        self.assertEqual(len(escalating_errors), 4)
        self._error(store)
        escalations = [record for record in store.list_events(limit=20) if record.get("alert_type")]
        self.assertEqual(len(escalations), 2)
        self.assertEqual(escalations[0]["details"]["repeat_count"], 2)

    def test_streaks_are_tracked_per_component_and_event_type(self):
        store = temporary_event_store(self, repeat_threshold=3, repeat_window_minutes=15)
        self._error(store, component="criterion-evaluator", event_type="type_a")
        self._error(store, component="criterion-evaluator", event_type="type_b")
        self._error(store, component="model-call", event_type="type_a")
        records = store.list_events(limit=10)
        self.assertEqual([record for record in records if record.get("alert_type")], [])


class EventReadingTests(unittest.TestCase):
    def test_list_events_returns_newest_first_with_filter_and_limit(self):
        store = temporary_event_store(self)
        store.record("info", "http", "first", "first event")
        store.record("error", "http", "second", "second event")
        store.record("warning", "storage", "third", "third event")
        self.assertEqual([event["event_type"] for event in store.list_events(limit=10)], ["third", "second", "first"])
        self.assertEqual([event["event_type"] for event in store.list_events(limit=2)], ["third", "second"])
        errors = store.list_events(limit=10, severity="error")
        self.assertEqual([event["event_type"] for event in errors], ["second"])

    def test_counts_and_health_surfaces(self):
        store = temporary_event_store(self)
        store.record("info", "http", "check", "all fine")
        try:
            raise OSError("disk unreachable")
        except OSError as exc:
            store.record("error", "storage", "run_storage_failed", "Persist failed.", exc=exc)
        self.assertEqual(store.counts(), {"info": 1, "error": 1})
        health = store.health(alert_window_minutes=60, event_limit=10)
        self.assertEqual(health["alert_window_minutes"], 60)
        self.assertEqual(health["counts"], {"info": 1, "error": 1})
        self.assertEqual(health["malformed_lines"], [])
        self.assertEqual([event["event_type"] for event in health["active_alerts"]], ["run_storage_failed"])
        self.assertEqual([event["event_type"] for event in health["events"]], ["run_storage_failed", "check"])
        for event in health["events"] + health["active_alerts"]:
            self.assertNotIn("traceback", event)

    def test_active_alerts_expire_outside_the_health_window(self):
        store = temporary_event_store(self)
        try:
            raise OSError("disk unreachable")
        except OSError:
            store.record("error", "storage", "run_storage_failed", "Persist failed.")
        fresh = store.health(alert_window_minutes=60)
        self.assertEqual(len(fresh["active_alerts"]), 1)
        expired = store.health(alert_window_minutes=0)
        self.assertEqual(expired["active_alerts"], [])
        self.assertEqual(expired["counts"], {"error": 1})

    def test_malformed_lines_are_counted_and_skipped_not_deleted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "system_events.jsonl"
            store = EventStore(path)
            store.record("info", "http", "valid", "first")
            path.write_text(path.read_text(encoding="utf-8") + "{not valid json}\n", encoding="utf-8")
            store.record("info", "http", "valid2", "second")
            self.assertEqual([event["event_type"] for event in store.list_events()], ["valid2", "valid"])
            self.assertEqual(store.malformed_line_numbers, [2])
            health = store.health(alert_window_minutes=60)
            self.assertEqual(health["malformed_lines"], [2])


class ResultStoreMalformedTests(unittest.TestCase):
    def test_malformed_lines_call_callback_with_line_numbers(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.jsonl"
            path.write_text('{"run_id": "ok"}\n{broken\n{"run_id": "ok2"}\n', encoding="utf-8")
            store = ResultStore(path)
            seen = []
            records = store.list(on_malformed=lambda line_number, count: seen.append((line_number, count)))
            self.assertEqual([record["run_id"] for record in records], ["ok", "ok2"])
            self.assertEqual(seen, [(2, 1)])
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 3)  # original data intact

    def test_listing_without_callback_still_skips_malformed_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.jsonl"
            path.write_text('{"a": 1}\n{broken\n', encoding="utf-8")
            records = ResultStore(path).list()
        self.assertEqual(records, [{"a": 1}])


class ServerEventTests(unittest.TestCase):
    def _handler(self, path):
        handler = server.Handler.__new__(server.Handler)
        handler.path = path
        return handler

    def test_unexpected_get_failure_returns_500_and_records_an_alert(self):
        store = temporary_event_store(self)
        handler = self._handler("/api/results")
        with patch.object(server, "SYSTEM_EVENTS", store), \
                patch.object(handler, "_do_get", side_effect=RuntimeError("catalog exploded")), \
                patch.object(handler, "_json") as send:
            handler.do_GET()
        status, payload = send.call_args.args
        self.assertEqual(status, 500)
        self.assertIn("event_id", payload)
        event = store.list_events()[0]
        self.assertEqual(event["event_type"], "unhandled_request_error")
        self.assertEqual(event["component"], "http")
        self.assertEqual(event["severity"], "error")
        self.assertTrue(event["alert"])
        self.assertIn("RuntimeError: catalog exploded", event["traceback"])

    def test_invalid_post_payload_returns_400_with_info_event(self):
        store = temporary_event_store(self)
        handler = self._handler("/api/experiments")
        handler.headers = {"Content-Length": "2"}
        handler.rfile = io.BytesIO(b"[]")
        with patch.object(server, "SYSTEM_EVENTS", store), patch.object(handler, "_json") as send:
            handler.do_POST()
        status, payload = send.call_args.args
        self.assertEqual(status, 400)
        event = store.list_events()[0]
        self.assertEqual(event["event_type"], "invalid_request")
        self.assertEqual(event["severity"], "info")
        self.assertEqual(event["alert"], False)
        self.assertEqual(event["details"]["path"], "/api/experiments")

    def test_system_events_route_serves_the_health_envelope(self):
        store = temporary_event_store(self)
        store.record("info", "http", "check", "all fine")
        handler = self._handler("/api/system-events")
        with patch.object(server, "SYSTEM_EVENTS", store), patch.object(handler, "_json") as send:
            handler.do_GET()
        status, payload = send.call_args.args
        self.assertEqual(status, 200)
        for key in ("generated_at", "alert_window_minutes", "counts", "malformed_lines", "active_alerts", "events"):
            self.assertIn(key, payload)

    def test_results_route_skips_malformed_lines_and_logs_a_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiments.jsonl"
            path.write_text('{"run_id": "ok"}\n{broken\n', encoding="utf-8")
            system_store = temporary_event_store(self)
            handler = self._handler("/api/results")
            with patch.object(server, "RESULTS", ResultStore(path)), \
                    patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(handler, "_json") as send:
                handler.do_GET()
        status, payload = send.call_args.args
        self.assertEqual(status, 200)
        self.assertEqual(payload, [{"run_id": "ok"}])
        event = system_store.list_events()[0]
        self.assertEqual(event["event_type"], "malformed_result_line")
        self.assertEqual(event["details"]["line_number"], 2)

    def test_standard_job_comparison_failure_is_logged_and_job_completes_with_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            system_store = EventStore(Path(directory) / "system_events.jsonl")
            job_state = {"job_id": "job-1", "status": "running", "failures": []}
            job_events = []
            case = {"case_id": "case-1", "category": "Test"}
            with patch.object(server, "STANDARD_JOB", job_state), \
                    patch.object(server, "STANDARD_JOB_EVENTS", job_events), \
                    patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(server, "execute_comparison", side_effect=RuntimeError("model offline")):
                server._run_standard_job("job-1", ["model-a"], "judge", [case], [2048], 1, "smoke")
            self.assertEqual(job_state["status"], "completed_with_failures")
            self.assertEqual(len(job_state["failures"]), 1)
            self.assertEqual({event["event"] for event in job_events}, {"comparison_failed", "completed"})
            event_types = {event["event_type"] for event in system_store.list_events(limit=10)}
            self.assertEqual(event_types, {"standard_comparison_failed", "standard_job_completed"})

    def test_standard_job_crash_records_a_critical_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            system_store = EventStore(Path(directory) / "system_events.jsonl")
            job_state = {"job_id": "job-1", "status": "running", "failures": []}
            case = {"case_id": "case-1", "category": "Test"}

            class FailingJobEventStore:
                def append(self, record):
                    raise OSError("disk full")

            with patch.object(server, "STANDARD_JOB", job_state), \
                    patch.object(server, "STANDARD_JOB_EVENTS", FailingJobEventStore()), \
                    patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(server, "execute_comparison", return_value={"runs": []}):
                with self.assertRaises(OSError):
                    server._run_standard_job("job-1", ["model-a"], "judge", [case], [2048], 1, "smoke")
            self.assertEqual(job_state["status"], "failed")
            event = system_store.list_events()[0]
            self.assertEqual(event["event_type"], "standard_job_failed")
            self.assertEqual(event["severity"], "critical")
            self.assertTrue(event["alert"])

    def test_job_start_records_an_info_event(self):
        with tempfile.TemporaryDirectory() as directory:
            system_store = EventStore(Path(directory) / "system_events.jsonl")

            class _FakeThread:
                def __init__(self, **kwargs):
                    self.kwargs = kwargs

                def start(self):
                    pass

            with patch.object(server, "STANDARD_JOB", None), \
                    patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(server, "model_catalog", return_value={
                        "answer-model": "digest-answer", server.STANDARD_EVALUATOR_MODEL: "digest-evaluator",
                    }), \
                    patch.object(server, "Thread", _FakeThread):
                server.start_standard_benchmark("smoke")
            started = [event for event in system_store.list_events(limit=10) if event["event_type"] == "standard_job_started"]
            self.assertEqual(len(started), 1)
            self.assertEqual(started[0]["severity"], "info")
            self.assertEqual(started[0]["details"]["mode"], "smoke")

    def test_serve_bind_failure_records_critical_alert_and_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            system_store = EventStore(Path(directory) / "system_events.jsonl")

            class FailingFactory:
                def __init__(self, *args, **kwargs):
                    raise OSError("port already in use")

            with patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(server, "ThreadingHTTPServer", FailingFactory):
                with self.assertRaises(SystemExit):
                    server.serve()
            event = system_store.list_events()[0]
            self.assertEqual(event["event_type"], "server_bind_failed")
            self.assertEqual(event["severity"], "critical")
            self.assertTrue(event["alert"])
            self.assertEqual(event["details"]["port"], 8000)

    def test_criterion_evaluator_failure_records_an_error_alert(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            system_store = EventStore(Path(directory) / "system_events.jsonl")
            with patch.object(server, "RESULTS", store), \
                    patch.object(server, "SYSTEM_EVENTS", system_store), \
                    patch.object(server, "model_catalog", return_value={
                        "answer-model": "digest-answer", "judge-model": "digest-judge",
                    }), \
                    patch.object(server, "call_ollama", side_effect=[
                        {"answer": "Blue.", "model": "answer-model", "prompt_tokens": 1, "completion_tokens": 1, "model_time_ns": 1},
                        OSError("evaluation service offline"),
                    ]):
                run = server.execute_experiment({
                    "source": "The valve is blue.", "question": "What color is the valve?",
                    "strategy": "baseline", "context_budget": 32, "run_model": True,
                    "model": "answer-model", "evaluation_model": "judge-model",
                    "criteria": ["The answer should state the sample color."],
                })
            event = system_store.list_events()[0]
            self.assertEqual(event["component"], "criterion-evaluator")
            self.assertEqual(event["event_type"], "criterion_evaluation_failed")
            self.assertEqual(event["severity"], "error")
            self.assertTrue(event["alert"])
            self.assertEqual(run["criterion_evaluation"]["status"], "error")
            self.assertEqual(len(store.list()), 1)


class SystemInterfaceStaticTests(unittest.TestCase):
    def test_results_page_contains_the_system_health_panel(self):
        html = (Path(__file__).resolve().parents[1] / "app" / "interface" / "index.html").read_text(encoding="utf-8")
        for element_id in (
            "system-health-panel", "system-health-summary", "refresh-system",
            "system-active-alert-count", "system-error-count", "system-malformed-count",
            "system-alert-list", "system-event-list",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn("data/logs/system_events.jsonl", html)

    def test_interface_loads_and_wires_system_events(self):
        script = (Path(__file__).resolve().parents[1] / "app" / "interface" / "app.js").read_text(encoding="utf-8")
        self.assertIn('$("#refresh-system").addEventListener("click", loadSystemEvents)', script)
        self.assertIn("loadResults(); loadSystemEvents();", script)
        self.assertIn("init(); loadResults(); loadSystemEvents();", script)
        self.assertIn("/api/system-events", script)
        self.assertIn("severity-${esc(severity)}", script)

    def test_interface_does_not_mention_the_removed_language(self):
        script = (Path(__file__).resolve().parents[1] / "app" / "interface" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("JavaScript, C, Go, and Rust", script)
        self.assertNotIn("four-language operation benchmarks", script)
        self.assertIn("three-language operation benchmarks", script)

    def test_styles_provide_event_and_severity_rules(self):
        styles = (Path(__file__).resolve().parents[1] / "app" / "interface" / "style.css").read_text(encoding="utf-8")
        for selector in (".event-list", ".event-row", ".tag.severity-error", ".tag.severity-critical", ".event-empty"):
            self.assertIn(selector, styles)


if __name__ == "__main__":
    unittest.main()
