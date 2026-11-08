import tempfile
import unittest
import json
from asm.engine import ASMEngine
from unittest.mock import MagicMock
from pathlib import Path
from unittest.mock import patch

from app.controller import server
from app.controller.storage import ResultStore
from app.controller.system_log import EventStore


class ControllerTests(unittest.TestCase):
    def setUp(self):
        super().setUp()
        # Controller tests must not append events to the real system event log.
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        patcher = patch.object(
            server, "SYSTEM_EVENTS", EventStore(Path(directory.name) / "system_events.jsonl"),
        )
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_offline_asm_run_is_stored_with_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store):
                run = server.execute_experiment({
                    "source": "The bridge opens at 8:30. It closes at 17:00.",
                    "question": "When does the bridge close?",
                    "strategy": "asm",
                    "context_budget": 128,
                })
            self.assertIsNone(run["response"])
            self.assertEqual(run["metrics"]["addresses_retrieved"], 2)
            self.assertEqual(store.list()[0]["run_id"], run["run_id"])

    def test_baseline_budget_and_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store):
                run = server.execute_experiment({
                    "source": "one   two\nthree four five six",
                    "question": "status?",
                    "strategy": "baseline",
                    "context_budget": 3,
                })
        self.assertLessEqual(run["metrics"]["final_assembled_context_tokens"], 3)
        self.assertEqual(run["context"]["context"], "one   two\nthree")
        self.assertEqual(run["metrics"]["question_tokens"], 2)
        with self.assertRaises(ValueError):
            server.execute_experiment({"source": "", "question": "q"})

    def test_expected_evidence_scores_baseline_recall_and_precision(self):
        source = "The beacon is violet. Routine inventory is unchanged."
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(server, "RESULTS", ResultStore(Path(directory) / "runs.jsonl")):
                run = server.execute_experiment({
                    "source": source, "question": "What color is the beacon?",
                    "strategy": "baseline", "context_budget": 5,
                    "expected_evidence": ["The beacon is violet."],
                })
        self.assertEqual(run["evidence_evaluation"]["expected_evidence_count"], 1)
        self.assertEqual(run["evidence_evaluation"]["recovered_evidence_count"], 1)
        self.assertEqual(run["evidence_evaluation"]["precision"], 1.0)
        self.assertEqual(run["evidence_evaluation"]["recall"], 1.0)
        self.assertEqual(run["metrics"]["retrieval_evidence_f1"], 1.0)

    def test_expected_evidence_rejects_quotes_not_present_in_source(self):
        with self.assertRaisesRegex(ValueError, "exact substring"):
            server.execute_experiment({
                "source": "The beacon is violet.", "question": "What color?",
                "strategy": "baseline", "expected_evidence": ["The beacon is blue."],
            })

    def test_local_model_response_accounting_and_exact_match(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", return_value={"local-test": "sha256:test"}), patch.object(server, "call_ollama", return_value={
                "answer": "Blue.", "model": "local-test", "prompt_tokens": 37,
                "completion_tokens": 2, "model_time_ns": 1000,
            }) as call:
                run = server.execute_experiment({
                    "source": "The valve is blue.", "question": "What color is the valve?",
                    "strategy": "baseline", "context_budget": 32,
                    "run_model": True, "model": "local-test", "expected_answer": "blue",
                })
            self.assertEqual(call.call_args.args[0], "local-test")
            self.assertTrue(run["evaluation"]["exact_match"])
            self.assertEqual(run["metrics"]["actual_prompt_tokens"], 37)
            self.assertEqual(run["metrics"]["total_model_tokens"], 39)
            self.assertEqual(run["model_version"], "sha256:test")

    def test_criterion_evaluation_runs_separate_local_inference_and_computes_percentage(self):
        replies = [
            {"answer": "Classical-like EDS is associated with biallelic TNXB variants.", "model": "answer-model",
             "prompt_tokens": 20, "completion_tokens": 9, "model_time_ns": 1000},
            {"answer": json.dumps({"criteria": [
                {"criterion_id": 2, "passed": False, "rationale": "The answer does not discuss scarring."},
                {"criterion_id": 1, "passed": True, "rationale": "The answer names classical-like EDS."},
                {"criterion_id": 3, "passed": True, "rationale": "The answer identifies biallelic variants."},
            ]}), "model": "judge-model", "prompt_tokens": 80, "completion_tokens": 30, "model_time_ns": 2000},
        ]
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", return_value={
                "answer-model": "digest-answer", "judge-model": "digest-judge",
            }), patch.object(server, "call_ollama", side_effect=replies) as call:
                run = server.execute_experiment({
                    "source": "Biallelic TNXB variants can cause classical-like EDS. Typical atrophic scarring is absent.",
                    "question": "Which subtype is associated with TNXB variants?",
                    "strategy": "baseline", "context_budget": 64, "run_model": True,
                    "model": "answer-model", "evaluation_model": "judge-model",
                    "criteria": "The answer should identify classical-like EDS.\nThe answer should state typical atrophic scarring is absent.\n- The answer should identify biallelic TNXB variants.",
                })
                stored_evaluation = store.list()[0]["criterion_evaluation"]
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args_list[1].args[0], "judge-model")
        self.assertEqual(call.call_args_list[1].kwargs["output_format"], "json")
        result = run["criterion_evaluation"]
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["passed_count"], 2)
        self.assertEqual(result["criteria_count"], 3)
        self.assertEqual(result["pass_percentage"], 66.67)
        self.assertEqual(result["criteria"][0]["criterion_id"], 1)
        self.assertEqual(run["evaluation_model_version"], "digest-judge")
        self.assertEqual(run["metrics"]["total_model_tokens"], 139)
        self.assertEqual(stored_evaluation["pass_percentage"], 66.67)

    def test_criterion_evaluator_rejects_missing_or_invalid_judgments(self):
        with patch.object(server, "call_ollama", return_value={
            "answer": json.dumps({"criteria": [{"criterion_id": 1, "passed": "yes", "rationale": "Some reason."}]}),
            "model": "judge",
        }):
            with self.assertRaisesRegex(ValueError, "pass/fail value"):
                server.evaluate_criteria_with_ollama("source", "question", "answer", ["criterion"], "judge")
        with self.assertRaisesRegex(ValueError, "2000 characters"):
            server.parse_criteria(["x" * 2001])

    def test_ollama_client_parses_actual_token_metrics(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({
            "response": "A local answer", "model": "small-local", "prompt_eval_count": 18,
            "eval_count": 4, "total_duration": 5000000,
        }).encode()
        with patch.object(server, "urlopen", return_value=response) as open_url:
            result = server.call_ollama("small-local", "hello", output_format="json")
        self.assertEqual(result["prompt_tokens"], 18)
        self.assertEqual(result["completion_tokens"], 4)
        self.assertIn("127.0.0.1:11434/api/generate", open_url.call_args.args[0].full_url)
        request_body = json.loads(open_url.call_args.args[0].data)
        self.assertEqual(request_body["format"], "json")
        self.assertEqual(request_body["options"], {"temperature": 0, "seed": 0})

    def test_asm_model_run_compresses_then_answers_with_measured_overhead(self):
        source = "The valve is blue. The valve opens at 6:00."
        addresses = [fragment.address for fragment in ASMEngine().ingest(source)]
        compression_response = {
            "answer": json.dumps({"representations": [{"addresses": addresses, "text": "Blue valve opens at 6:00."}]}),
            "model": "local-test", "prompt_tokens": 90, "completion_tokens": 12, "model_time_ns": 1000,
        }
        answer_response = {
            "answer": "Blue.", "model": "local-test", "prompt_tokens": 35,
            "completion_tokens": 2, "model_time_ns": 2000,
        }
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", return_value={"local-test": "sha256:test"}), patch.object(server, "call_ollama", side_effect=[compression_response, answer_response]) as call:
                run = server.execute_experiment({
                    "source": source, "question": "What color is the valve?", "strategy": "asm",
                    "context_budget": 64, "run_model": True, "model": "local-test", "expand_sources": False,
                })
        self.assertEqual(call.call_count, 2)
        self.assertEqual(call.call_args_list[0].args[0], "local-test")
        self.assertEqual(call.call_args_list[0].kwargs["output_format"], "json")
        self.assertEqual(run["compression_mode"], "local-model-semantic")
        self.assertEqual(run["metrics"]["total_model_tokens"], 139)
        self.assertEqual(run["metrics"]["expansions"], 0)
        self.assertEqual(run["context"]["context"], "Blue valve opens at 6:00.")
        self.assertEqual(run["response"], "Blue.")

    def test_invalid_semantic_provenance_prevents_answer_request(self):
        source = "The valve is blue."
        response = {"answer": json.dumps({"representations": [{"addresses": ["src:wrong:000000"], "text": "Blue valve."}]})}
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", return_value={"local-test": "sha256:test"}), patch.object(server, "call_ollama", return_value=response) as call:
                run = server.execute_experiment({
                    "source": source, "question": "Color?", "strategy": "asm",
                    "context_budget": 64, "run_model": True, "model": "local-test",
                })
        self.assertEqual(call.call_count, 1)
        self.assertIn("unknown addresses", run["error"])
        self.assertIsNone(run["response"])

    def test_paired_comparison_preserves_equivalent_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store):
                result = server.execute_comparison({
                    "source": "Aster is a blue flower.", "question": "What color is Aster?",
                    "context_budget": 100, "model": None, "run_model": False,
                    "expected_answer": "blue", "repeat_count": 2,
                })
                stored_count = len(store.list())
        self.assertEqual(len(result["runs"]), 4)
        self.assertTrue(result["equivalence"]["controls_match"])
        self.assertTrue(result["equivalence"]["same_expansion_policy"])
        self.assertEqual(result["execution_order"], [["baseline", "asm"], ["asm", "baseline"]])
        self.assertEqual(len({run["comparison_id"] for run in result["runs"]}), 1)
        self.assertEqual(len({run["input_signature"] for run in result["runs"]}), 1)
        self.assertEqual(stored_count, 4)

    def test_paired_comparison_flags_model_version_change(self):
        source = "The sensor is green."
        address = ASMEngine().ingest(source)[0].address
        mocked_calls = [
            {"answer": "Green.", "model": "local", "prompt_tokens": 12, "completion_tokens": 1},
            {"answer": json.dumps({"representations": [{"addresses": [address], "text": "Green sensor."}]}), "model": "local", "prompt_tokens": 40, "completion_tokens": 5},
            {"answer": "Green.", "model": "local", "prompt_tokens": 10, "completion_tokens": 1},
        ]
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", side_effect=[{"local": "digest-a"}, {"local": "digest-b"}]), patch.object(server, "call_ollama", side_effect=mocked_calls):
                result = server.execute_comparison({
                    "source": source, "question": "What color?", "context_budget": 32,
                    "model": "local", "run_model": True, "repeat_count": 1,
                })
        self.assertFalse(result["equivalence"]["same_model_version"])
        self.assertFalse(result["equivalence"]["controls_match"])

    def test_paired_comparison_checks_criterion_evaluator_controls(self):
        source = "The sample is blue."
        address = ASMEngine().ingest(source)[0].address
        pass_result = {"answer": json.dumps({"criteria": [{"criterion_id": 1, "passed": True, "rationale": "The answer is supported."}]}),
                       "model": "judge", "prompt_tokens": 10, "completion_tokens": 2, "model_time_ns": 1000}
        responses = [
            {"answer": "Blue.", "model": "answer", "prompt_tokens": 10, "completion_tokens": 1},
            pass_result,
            {"answer": json.dumps({"representations": [{"addresses": [address], "text": "The sample is blue."}]}), "model": "answer", "prompt_tokens": 30, "completion_tokens": 4},
            {"answer": "Blue.", "model": "answer", "prompt_tokens": 10, "completion_tokens": 1},
            pass_result,
        ]
        with tempfile.TemporaryDirectory() as directory:
            store = ResultStore(Path(directory) / "runs.jsonl")
            with patch.object(server, "RESULTS", store), patch.object(server, "model_catalog", return_value={"answer": "answer-v1", "judge": "judge-v1"}), patch.object(server, "call_ollama", side_effect=responses):
                result = server.execute_comparison({
                    "source": source, "question": "What color is the sample?", "context_budget": 32,
                    "run_model": True, "model": "answer", "evaluation_model": "judge",
                    "criteria": ["The answer should state the sample color."], "repeat_count": 1,
                })
        self.assertTrue(result["equivalence"]["same_criteria"])
        self.assertTrue(result["equivalence"]["same_evaluation_model"])
        self.assertTrue(result["equivalence"]["same_evaluation_model_version"])
        self.assertTrue(result["equivalence"]["same_evaluation_settings"])
        self.assertTrue(result["equivalence"]["controls_match"])
        self.assertEqual([run["criterion_evaluation"]["pass_percentage"] for run in result["runs"]], [100, 100])

    def test_server_startup_binds_localhost(self):
        fake_server = MagicMock()
        with patch.object(server, "ThreadingHTTPServer", return_value=fake_server) as factory:
            server.serve()
        factory.assert_called_once_with(("127.0.0.1", 8000), server.Handler)
        fake_server.serve_forever.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
