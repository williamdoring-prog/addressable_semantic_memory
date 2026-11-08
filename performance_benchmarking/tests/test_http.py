import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.controller import server
from app.controller.storage import ResultStore
from app.controller.system_log import EventStore


class HTTPHandlerTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Handler tests must not append events to the real system event log.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch.object(
            server, "SYSTEM_EVENTS", EventStore(Path(directory.name) / "system_events.jsonl"),
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_static_home_route_serves_interface(self):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/"
        with patch.object(handler, "_send") as send:
            handler.do_GET()
        status, body, content_type = send.call_args.args
        self.assertEqual(status, 200)
        self.assertIn(b"ASM Local Benchmark", body)
        self.assertIn("text/html", content_type)

    def test_post_route_persists_a_run(self):
        body = json.dumps({
            "source": "The sample valve is blue.",
            "question": "What color is the valve?",
            "strategy": "asm",
            "context_budget": 64,
        }).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/experiments"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "results.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(handler, "_json") as send:
                handler.do_POST()
            status, run = send.call_args.args
            self.assertEqual(status, 201)
            self.assertEqual(run["context"]["context"], "The sample valve is blue.")
            self.assertEqual(len(store.list()), 1)

    def test_post_rejects_non_object_payload(self):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/experiments"
        handler.headers = {"Content-Length": "2"}
        handler.rfile = io.BytesIO(b"[]")
        with patch.object(handler, "_json") as send:
            handler.do_POST()
        self.assertEqual(send.call_args.args[0], 400)

    def test_compare_route_returns_and_stores_a_pair(self):
        body = json.dumps({
            "source": "There are 12 lamps.", "question": "How many lamps?",
            "context_budget": 40, "repeat_count": 1,
        }).encode()
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/compare"
        handler.headers = {"Content-Length": str(len(body))}
        handler.rfile = io.BytesIO(body)
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "results.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(handler, "_json") as send:
                handler.do_POST()
            status, result = send.call_args.args
            self.assertEqual(status, 201)
            self.assertTrue(result["equivalence"]["controls_match"])
            self.assertEqual({run["strategy"] for run in result["runs"]}, {"baseline", "asm"})
            self.assertEqual(len(store.list()), 2)

    def test_language_result_route_reads_separate_append_only_store(self):
        record = {"run_id":"lang-1", "language_metrics":{"language":"javascript"}}
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "language.jsonl")
            store.append(record)
            handler = server.Handler.__new__(server.Handler)
            handler.path = "/api/language-results"
            with patch.object(server, "LANGUAGE_RESULTS", store), patch.object(handler, "_json") as send:
                handler.do_GET()
        self.assertEqual(send.call_args.args, (200, [record]))

    def test_context_pressure_result_route_reads_separate_store(self):
        record = {"run_id":"pressure-1", "category":"synthetic-context-pressure-multihop"}
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "pressure.jsonl")
            store.append(record)
            handler = server.Handler.__new__(server.Handler)
            handler.path = "/api/context-pressure-results"
            with patch.object(server, "CONTEXT_PRESSURE_RESULTS", store), patch.object(handler, "_json") as send:
                handler.do_GET()
        self.assertEqual(send.call_args.args, (200, [record]))

    def test_standard_benchmark_route_starts_the_selected_mode(self):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/standard-benchmark"
        handler.headers = {"Content-Length": "16"}
        handler.rfile = io.BytesIO(b'{"mode":"smoke"}')
        with patch.object(server, "start_standard_benchmark", return_value={"job_id":"job-1", "status":"running"}) as starter:
            with patch.object(handler, "_json") as send:
                handler.do_POST()
        self.assertEqual(send.call_args.args, (202, {"job_id":"job-1", "status":"running"}))
        self.assertEqual(starter.call_args.args, ("smoke",))

    def test_standard_benchmark_route_defaults_to_the_full_mode(self):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/api/standard-benchmark"
        handler.headers = {"Content-Length": "2"}
        handler.rfile = io.BytesIO(b"{}")
        with patch.object(server, "start_standard_benchmark", return_value={"job_id":"job-1", "status":"running"}) as starter:
            with patch.object(handler, "_json") as send:
                handler.do_POST()
        self.assertEqual(send.call_args.args, (202, {"job_id":"job-1", "status":"running"}))
        self.assertEqual(starter.call_args.args, ("full",))


if __name__ == "__main__":
    unittest.main()
