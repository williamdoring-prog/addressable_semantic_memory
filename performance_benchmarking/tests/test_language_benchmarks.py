import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "benchmarks" / "fixtures" / "inputs"
EXPECTED_DIR = ROOT / "benchmarks" / "fixtures" / "expected_outputs"
C_SOURCE = ROOT / "benchmarks" / "c" / "main.c"
BENCHMARK_RUNNER = ROOT / "benchmarks" / "run_benchmarks.py"
RUSTC = shutil.which("rustc") or str(Path.home() / ".cargo" / "bin" / ("rustc.exe" if os.name == "nt" else "rustc"))
OPERATION_NAMES = {"input_parse_ns", "retrieval_ns", "address_lookup_ns", "expansion_assembly_ns", "serialization_ns"}
RUST_ENVIRONMENT = os.environ.copy()
RUST_TARGET = "x86_64-pc-windows-gnu" if os.name == "nt" and not shutil.which("link.exe") else None
RUSTUP_HOME = Path(os.environ.get("RUSTUP_HOME", Path.home() / ".rustup"))
if Path(RUSTC).is_file() and not RUST_ENVIRONMENT.get("RUSTUP_TOOLCHAIN"):
    installed_toolchains = sorted(path.name for path in (RUSTUP_HOME / "toolchains").glob("*") if path.is_dir())
    if installed_toolchains:
        RUST_ENVIRONMENT["RUSTUP_TOOLCHAIN"] = installed_toolchains[0]


def operation_metrics(stderr):
    lines = [line.removeprefix("ASM-BENCH-METRICS ") for line in stderr.splitlines() if line.startswith("ASM-BENCH-METRICS ")]
    if len(lines) != 1:
        raise AssertionError(f"expected one operation metrics record, got {lines!r}")
    metrics = json.loads(lines[0])
    if set(metrics) != OPERATION_NAMES or any(not isinstance(value, int) or value < 0 for value in metrics.values()):
        raise AssertionError(f"invalid operation metrics: {metrics!r}")
    return {name: value if value > 0 else None for name, value in metrics.items()}


@unittest.skipUnless(shutil.which("gcc") and shutil.which("go") and Path(RUSTC).is_file(), "gcc, Go, and Rust are required for language checks")
class LanguageBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.c_binary = Path(cls.temp_dir.name) / "asm-bench-c.exe"
        cls.go_binary = Path(cls.temp_dir.name) / "asm-bench-go.exe"
        cls.go = shutil.which("go")
        cls.go_environment = os.environ.copy()
        adjacent_root = Path(cls.go).resolve().parent.parent / "lib" / "go"
        if (adjacent_root / "src").is_dir():
            cls.go_environment["GOROOT"] = str(adjacent_root)
        cls.go_environment["GOCACHE"] = str(Path(cls.temp_dir.name) / "go-cache")
        cls.go_environment["GOPATH"] = str(Path(cls.temp_dir.name) / "go-path")
        cls.go_environment["GO111MODULE"] = "off"
        cls.rust_environment = RUST_ENVIRONMENT.copy()
        cls.rust_binary = Path(cls.temp_dir.name) / "asm-bench-rust.exe"
        result = subprocess.run(
            ["gcc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(C_SOURCE), "-o", str(cls.c_binary)],
            capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise RuntimeError(f"C benchmark compile failed: {result.stderr}")
        result = subprocess.run(
            [cls.go, "build", "-trimpath", "-o", str(cls.go_binary)],
            cwd=ROOT / "benchmarks" / "go", env=cls.go_environment, capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Go benchmark compile failed: {result.stderr}")
        result = subprocess.run(
            [RUSTC, "--edition=2021", "-C", "opt-level=3", "-C", "codegen-units=1", *(["--target", RUST_TARGET] if RUST_TARGET else []), "-o", str(cls.rust_binary), str(ROOT / "benchmarks" / "rust" / "main.rs")],
            cwd=ROOT / "benchmarks" / "rust", env=cls.rust_environment, capture_output=True, text=True, check=False,
        )
        if result.returncode:
            raise RuntimeError(f"Rust benchmark compile failed: {result.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_all_fixture_outputs_match_expected_and_each_other(self):
        fixtures = sorted(FIXTURE_DIR.glob("*.asmbench"))
        self.assertEqual(len(fixtures), 3, "small, medium, and large fixtures should be present")
        for fixture in fixtures:
            expected_path = EXPECTED_DIR / f"{fixture.stem}.json"
            expected = json.loads(expected_path.read_text(encoding="utf-8"))
            results = []
            for command, environment in (([str(self.c_binary), str(fixture)], None), ([str(self.go_binary), str(fixture)], self.go_environment), ([str(self.rust_binary), str(fixture)], self.rust_environment)):
                completed = subprocess.run(command, env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertGreater(result["elapsed_ns"], 0)
                self.assertEqual(set(operation_metrics(completed.stderr)), OPERATION_NAMES)
                result.pop("elapsed_ns")
                self.assertEqual(result, expected, fixture.name)
                results.append(result)
            self.assertEqual(results[0], results[1], fixture.name)
            self.assertEqual(results[0], results[2], fixture.name)

    def test_no_asm_baseline_truncates_original_source_for_every_language(self):
        token_count = lambda text: len(re.findall(r"[A-Za-z0-9]+", text))
        commands = (([str(self.c_binary)], None), ([str(self.go_binary)], self.go_environment), ([str(self.rust_binary)], self.rust_environment))
        for fixture in sorted(FIXTURE_DIR.glob("*.asmbench")):
            records = [line.split("\t", 2) for line in fixture.read_text(encoding="utf-8").splitlines()[1:] if line]
            values = {record[0]: record[1] for record in records if record[0] != "fragment"}
            fragments = [record[2] for record in records if record[0] == "fragment"]
            source = " ".join(fragments)
            matches = list(re.finditer(r"[A-Za-z0-9]+", source))
            budget = int(values["budget"])
            if len(matches) > budget:
                source = source[:matches[budget - 1].end()]
            expected = {
                "input_id": values["id"], "original_source_tokens": sum(map(token_count, fragments)),
                "question_tokens": token_count(values["question"]), "retrieved_addresses": [],
                "lookups": [], "expanded": [], "context": source, "context_tokens": token_count(source),
            }
            results = []
            for command, environment in commands:
                completed = subprocess.run(command + [str(fixture), "baseline"], env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                result = json.loads(completed.stdout)
                self.assertGreater(result["elapsed_ns"], 0)
                self.assertEqual(set(operation_metrics(completed.stderr)), OPERATION_NAMES)
                result.pop("elapsed_ns")
                self.assertEqual(result, expected, (fixture.name, command))
                results.append(result)
            self.assertTrue(all(result == results[0] for result in results[1:]), fixture.name)

    def test_output_addresses_trace_to_exact_fixture_fragments(self):
        for fixture in sorted(FIXTURE_DIR.glob("*.asmbench")):
            fragments = {}
            for line in fixture.read_text(encoding="utf-8").splitlines():
                fields = line.split("\t", 2)
                if fields[0] == "fragment":
                    fragments[fields[1]] = fields[2].replace("\\t", "\t").replace("\\n", "\n").replace("\\r", "\r").replace("\\\\", "\\")
            expected = json.loads((EXPECTED_DIR / f"{fixture.stem}.json").read_text(encoding="utf-8"))
            for field in ("lookups", "expanded"):
                for item in expected[field]:
                    self.assertEqual(item["text"], fragments[item["address"]], (fixture.name, field, item["address"]))

    def test_token_accounting_and_repeated_outputs_are_deterministic(self):
        token_count = lambda text: len(re.findall(r"[A-Za-z0-9]+", text))
        for fixture in sorted(FIXTURE_DIR.glob("*.asmbench")):
            input_lines = fixture.read_text(encoding="utf-8").splitlines()
            first = {}
            for name, command, environment in (("c", [str(self.c_binary), str(fixture)], None), ("go", [str(self.go_binary), str(fixture)], self.go_environment), ("rust", [str(self.rust_binary), str(fixture)], self.rust_environment)):
                outputs = []
                for _ in range(2):
                    completed = subprocess.run(command, env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
                    self.assertEqual(completed.returncode, 0, completed.stderr)
                    operation_metrics(completed.stderr)
                    result = json.loads(completed.stdout)
                    result.pop("elapsed_ns")
                    outputs.append(result)
                self.assertEqual(outputs[0], outputs[1], (fixture.name, name))
                source_tokens = sum(token_count(line.split("\t", 2)[2]) for line in input_lines if line.startswith("fragment\t"))
                question = next(line.split("\t", 1)[1] for line in input_lines if line.startswith("question\t"))
                self.assertEqual(outputs[0]["original_source_tokens"], source_tokens)
                self.assertEqual(outputs[0]["question_tokens"], token_count(question))
                self.assertEqual(outputs[0]["context_tokens"], token_count(outputs[0]["context"]))
                first[name] = outputs[0]
            self.assertEqual(first["c"], first["go"], fixture.name)
            self.assertEqual(first["c"], first["rust"], fixture.name)
            self.assertEqual(first["go"], first["rust"], fixture.name)

    def test_escaped_text_round_trips_across_all_implementations(self):
        fixture = Path(self.temp_dir.name) / "escaped.asmbench"
        fixture.write_text(
            "ASM-BENCH-V1\n"
            "id\tescaped\n"
            "budget\t10\n"
            "question\tWhich line has Tab?\n"
            "lookup\taddr\\t2\n"
            "fragment\taddr\\t2\tTab\\tline\\nSlash \\\\ path.\n",
            encoding="utf-8",
        )
        expected = {
            "input_id": "escaped",
            "original_source_tokens": 4,
            "question_tokens": 4,
            "retrieved_addresses": ["addr\t2"],
            "lookups": [{"address": "addr\t2", "text": "Tab\tline\nSlash \\ path."}],
            "expanded": [{"address": "addr\t2", "text": "Tab\tline\nSlash \\ path."}],
            "context": "Tab\tline\nSlash \\ path.",
            "context_tokens": 4,
        }
        commands = (([str(self.c_binary), str(fixture)], None), ([str(self.go_binary), str(fixture)], self.go_environment), ([str(self.rust_binary), str(fixture)], self.rust_environment))
        for command, environment in commands:
            completed = subprocess.run(command, env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(set(operation_metrics(completed.stderr)), OPERATION_NAMES)
            result.pop("elapsed_ns")
            mismatches = {key: (str(result[key]).encode("unicode_escape"), str(expected[key]).encode("unicode_escape")) for key in expected if result[key] != expected[key]}
            self.assertFalse(mismatches, f"{command}: {mismatches}")

    def test_unicode_addresses_use_utf8_bytewise_order(self):
        fixture = Path(self.temp_dir.name) / "unicode-addresses.asmbench"
        private_use = chr(0xE000)
        emoji = chr(0x1F600)
        fixture.write_text(
            "ASM-BENCH-V1\nid\tunicode\nbudget\t10\nquestion\tshared\n"
            f"fragment\t{emoji}\tshared\nfragment\t{private_use}\tshared\n",
            encoding="utf-8",
        )
        expected = {
            "input_id": "unicode", "original_source_tokens": 2, "question_tokens": 1,
            "retrieved_addresses": [private_use, emoji], "lookups": [],
            "expanded": [{"address": private_use, "text": "shared"}, {"address": emoji, "text": "shared"}],
            "context": "shared shared", "context_tokens": 2,
        }
        commands = (([str(self.c_binary), str(fixture)], None), ([str(self.go_binary), str(fixture)], self.go_environment), ([str(self.rust_binary), str(fixture)], self.rust_environment))
        for command, environment in commands:
            completed = subprocess.run(command, env=environment, capture_output=True, text=True, encoding="utf-8", check=False)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual(set(operation_metrics(completed.stderr)), OPERATION_NAMES)
            result.pop("elapsed_ns")
            mismatches = {key: (str(result[key]).encode("unicode_escape"), str(expected[key]).encode("unicode_escape")) for key in expected if result[key] != expected[key]}
            self.assertFalse(mismatches, f"{command}: {mismatches}")

    def test_all_runners_reject_malformed_input(self):
        invalid_cases = (
            "not-a-benchmark\n",
            "ASM-BENCH-V1\nid\tbad-escape\nbudget\t1\nquestion\tBad\\q escape\nfragment\ta1\ttext\n",
            "ASM-BENCH-V1\nid\tbad-budget\nbudget\t-1\nquestion\tquery\nfragment\ta1\ttext\n",
        )
        commands = (([str(self.c_binary)], None), ([str(self.go_binary)], self.go_environment), ([str(self.rust_binary)], self.rust_environment))
        for index, invalid_input in enumerate(invalid_cases):
            bad_input = Path(self.temp_dir.name) / f"invalid-{index}.asmbench"
            bad_input.write_text(invalid_input, encoding="utf-8")
            for command, environment in commands:
                result = subprocess.run(command + [str(bad_input)], env=environment, capture_output=True, text=True, check=False)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())

    def test_repeated_runner_appends_correctness_gated_records(self):
        fixture = FIXTURE_DIR / "small-factual.asmbench"
        output = Path(self.temp_dir.name) / "language-runs.jsonl"
        command = [
            "python", str(BENCHMARK_RUNNER), "--fixture", str(fixture),
            "--iterations", "2", "--warmups", "1", "--output", str(output),
        ]
        for _ in range(2):
            result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
        records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(records), 24)
        self.assertTrue(all(record["correctness"] == "passed" for record in records))
        self.assertEqual({record["language_metrics"]["language"] for record in records}, {"c", "go", "rust"})
        self.assertEqual({record["strategy"] for record in records}, {"asm", "baseline"})
        self.assertEqual({record["language_metrics"]["strategy"] for record in records}, {"asm", "baseline"})
        baseline_records = [record for record in records if record["strategy"] == "baseline"]
        self.assertTrue(all(record["language_metrics"]["operation_times_ns"]["retrieval_ns"] is None for record in baseline_records))
        self.assertTrue(all(record["language_metrics"]["operation_times_ns"]["address_lookup_ns"] is None for record in baseline_records))
        self.assertTrue(all(set(record["language_metrics"]["operation_times_ns"]) == OPERATION_NAMES for record in records))
        self.assertTrue(all(all(value is None or value > 0 for value in record["language_metrics"]["operation_times_ns"].values()) for record in records))
        if os.name == "nt":
            self.assertTrue(all(record["language_metrics"]["memory_bytes"] > 0 for record in records))
            # CPU utilization samples depend on the OS accounting threshold; with the
            # removed JavaScript runtime, process runs may all fall below it, so only
            # the wall-time implication is asserted.
            self.assertTrue(all(
                record["language_metrics"]["cpu_utilization_percent"] is None
                for record in records if record["language_metrics"]["process_wall_time_ns"] < 50_000_000
            ))
        else:
            self.assertTrue(all(record["language_metrics"]["memory_bytes"] is None for record in records))
            self.assertTrue(all(record["language_metrics"]["cpu_utilization_percent"] is None for record in records))


if __name__ == "__main__":
    unittest.main()
