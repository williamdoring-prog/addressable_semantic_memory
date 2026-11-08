"""Run correctness-gated, repeated local language microbenchmarks."""

from __future__ import annotations

import argparse
import ctypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
INPUTS = ROOT / "benchmarks" / "fixtures" / "inputs"
EXPECTED = ROOT / "benchmarks" / "fixtures" / "expected_outputs"
METRIC_PREFIX = "ASM-BENCH-METRICS "
OPERATION_NAMES = (
    "input_parse_ns", "retrieval_ns", "address_lookup_ns", "expansion_assembly_ns", "serialization_ns",
)


def process_resource_metrics(process: subprocess.Popen, wall_ns: int) -> tuple[int | None, float | None]:
    if os.name != "nt" or wall_ns <= 0:
        return None, None

    from ctypes import wintypes

    class FileTime(ctypes.Structure):
        _fields_ = [("low", wintypes.DWORD), ("high", wintypes.DWORD)]

    class ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD), ("page_fault_count", wintypes.DWORD),
            ("peak_working_set_size", ctypes.c_size_t), ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t), ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_nonpaged_pool_usage", ctypes.c_size_t), ("quota_nonpaged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t), ("peak_pagefile_usage", ctypes.c_size_t),
            ("private_usage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime), ctypes.POINTER(FileTime)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(ProcessMemoryCountersEx), wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    handle = wintypes.HANDLE(int(process._handle))

    counters = ProcessMemoryCountersEx()
    counters.cb = ctypes.sizeof(counters)
    peak_memory = None
    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        peak_memory = int(counters.peak_working_set_size)

    creation, exit_time, kernel, user = FileTime(), FileTime(), FileTime(), FileTime()
    cpu_percent = None
    # Short Windows processes can finish before the OS CPU-time accounting tick is updated.
    if wall_ns >= 50_000_000 and kernel32.GetProcessTimes(handle, ctypes.byref(creation), ctypes.byref(exit_time), ctypes.byref(kernel), ctypes.byref(user)):
        ticks = lambda value: (value.high << 32) | value.low
        cpu_ns = (ticks(kernel) + ticks(user)) * 100
        cpu_percent = cpu_ns * 100 / wall_ns
    return peak_memory, cpu_percent


def execute(command: list[str], fixture: Path, environment: dict[str, str] | None = None, strategy: str = "asm") -> tuple[dict, int, int | None, float | None, dict[str, int]]:
    started = time.perf_counter_ns()
    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(command + [str(fixture), strategy], stdout=stdout_file, stderr=stderr_file, env=environment)
        while process.poll() is None:
            time.sleep(0.001)
        return_code = process.wait()
        wall_elapsed = time.perf_counter_ns() - started
        peak_memory, cpu_percent = process_resource_metrics(process, wall_elapsed)
        stdout_file.seek(0)
        stderr_file.seek(0)
        stdout = stdout_file.read().decode("utf-8")
        stderr = stderr_file.read().decode("utf-8", errors="replace")
    if return_code:
        raise RuntimeError(f"{command[0]} failed on {fixture.name}: {stderr.strip()}")
    metric_lines = [line[len(METRIC_PREFIX):] for line in stderr.splitlines() if line.startswith(METRIC_PREFIX)]
    if len(metric_lines) != 1:
        raise RuntimeError(f"{command[0]} did not report exactly one operation-metrics record on {fixture.name}")
    operation_metrics = json.loads(metric_lines[0])
    if set(operation_metrics) != set(OPERATION_NAMES) or any(not isinstance(operation_metrics[name], int) or operation_metrics[name] < 0 for name in OPERATION_NAMES):
        raise RuntimeError(f"{command[0]} reported invalid operation metrics on {fixture.name}")
    operation_metrics = {name: value if value > 0 else None for name, value in operation_metrics.items()}
    return json.loads(stdout), wall_elapsed, peak_memory, cpu_percent, operation_metrics


def normalized(output: dict) -> dict:
    return {key: value for key, value in output.items() if key != "elapsed_ns"}


def baseline_expected(fixture: Path) -> dict:
    fixture_id = question = None
    budget = 0
    fragments = []
    for line in fixture.read_text(encoding="utf-8").splitlines()[1:]:
        fields = line.split("\t", 2)
        if fields[0] == "id":
            fixture_id = fields[1]
        elif fields[0] == "question":
            question = fields[1]
        elif fields[0] == "budget":
            budget = int(fields[1])
        elif fields[0] == "fragment":
            value = fields[2]
            decoded = []
            index = 0
            while index < len(value):
                if value[index] == "\\" and index + 1 < len(value):
                    index += 1
                    decoded.append({"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}.get(value[index], value[index]))
                else:
                    decoded.append(value[index])
                index += 1
            fragments.append("".join(decoded))
    source = " ".join(fragments)
    matches = list(__import__("re").finditer(r"[A-Za-z0-9]+", source))
    if len(matches) > budget:
        source = source[:matches[budget - 1].end()]
    import re
    count = lambda value: len(re.findall(r"[A-Za-z0-9]+", value))
    return {
        "input_id": fixture_id,
        "original_source_tokens": sum(count(fragment) for fragment in fragments),
        "question_tokens": count(question or ""),
        "retrieved_addresses": [],
        "lookups": [],
        "expanded": [],
        "context": source,
        "context_tokens": count(source),
    }


def append_records(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_commands(temp_dir: Path) -> tuple[list[tuple[str, list[str], str, int | None, dict[str, str] | None]], dict]:
    gcc = shutil.which("gcc")
    go = shutil.which("go")
    rustc = shutil.which("rustc")
    if not rustc:
        cargo_bin = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")) / "bin"
        rust_candidate = cargo_bin / ("rustc.exe" if os.name == "nt" else "rustc")
        if rust_candidate.is_file():
            rustc = str(rust_candidate)
    if not gcc or not go or not rustc:
        raise RuntimeError("gcc, Go, and Rust are required for the three-language benchmark runner.")
    gcc_version = subprocess.run([gcc, "--version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    binary = temp_dir / ("asm-bench-c.exe" if os.name == "nt" else "asm-bench-c")
    compile_started = time.perf_counter_ns()
    compile_result = subprocess.run(
        [gcc, "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(ROOT / "benchmarks" / "c" / "main.c"), "-o", str(binary)],
        capture_output=True, text=True, check=False,
    )
    compile_ns = time.perf_counter_ns() - compile_started
    if compile_result.returncode:
        raise RuntimeError(f"C release build failed: {compile_result.stderr.strip()}")
    c_command = ("c", [str(binary)], gcc_version, compile_ns, None)

    go_environment = os.environ.copy()
    adjacent_root = Path(go).resolve().parent.parent / "lib" / "go"
    if (adjacent_root / "src").is_dir():
        go_environment["GOROOT"] = str(adjacent_root)
    go_environment["GOCACHE"] = str(temp_dir / "go-cache")
    go_environment["GOPATH"] = str(temp_dir / "go-path")
    go_environment["GO111MODULE"] = "off"
    go_root_result = subprocess.run([go, "env", "GOROOT"], capture_output=True, text=True, env=go_environment, check=False)
    if go_root_result.returncode or not (Path(go_root_result.stdout.strip()) / "src").is_dir():
        raise RuntimeError(f"Go toolchain has no valid GOROOT: {go_root_result.stderr.strip() or go_root_result.stdout.strip()}")
    go_version = subprocess.run([go, "version"], capture_output=True, text=True, env=go_environment, check=True).stdout.strip()
    go_binary = temp_dir / ("asm-bench-go.exe" if os.name == "nt" else "asm-bench-go")
    go_started = time.perf_counter_ns()
    go_build = subprocess.run(
        [go, "build", "-trimpath", "-o", str(go_binary)],
        cwd=ROOT / "benchmarks" / "go", capture_output=True, text=True, env=go_environment, check=False,
    )
    go_compile_ns = time.perf_counter_ns() - go_started
    if go_build.returncode:
        raise RuntimeError(f"Go release build failed: {go_build.stderr.strip()}")
    go_command = ("go", [str(go_binary)], go_version, go_compile_ns, go_environment)
    rust_environment = os.environ.copy()
    rustup_shim = Path(rustc).parent == (Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo")) / "bin")
    if rustup_shim and not rust_environment.get("RUSTUP_TOOLCHAIN"):
        rustup_home = Path(os.environ.get("RUSTUP_HOME", Path.home() / ".rustup"))
        toolchains = sorted(path.name for path in (rustup_home / "toolchains").glob("*") if path.is_dir())
        if not toolchains:
            raise RuntimeError("Rustup has no installed toolchain; install one before running the benchmark.")
        rust_environment["RUSTUP_TOOLCHAIN"] = toolchains[0]
    rust_version = subprocess.run([rustc, "--version"], capture_output=True, text=True, env=rust_environment, check=True).stdout.strip()
    rust_binary = temp_dir / ("asm-bench-rust.exe" if os.name == "nt" else "asm-bench-rust")
    rust_flags = ["--edition=2021", "-C", "opt-level=3", "-C", "codegen-units=1"]
    rust_target = None
    if os.name == "nt" and not shutil.which("link.exe"):
        if not gcc:
            raise RuntimeError("Rust's MSVC linker is unavailable and no MinGW gcc is available for the Windows GNU target.")
        rust_target = "x86_64-pc-windows-gnu"
    rust_started = time.perf_counter_ns()
    rust_build = subprocess.run(
        [rustc, *rust_flags, *(["--target", rust_target] if rust_target else []), "-o", str(rust_binary), str(ROOT / "benchmarks" / "rust" / "main.rs")],
        cwd=ROOT / "benchmarks" / "rust", capture_output=True, text=True, env=rust_environment, check=False,
    )
    rust_compile_ns = time.perf_counter_ns() - rust_started
    if rust_build.returncode:
        raise RuntimeError(f"Rust release build failed: {rust_build.stderr.strip()}")
    rust_command = ("rust", [str(rust_binary)], rust_version, rust_compile_ns, rust_environment)
    return [c_command, go_command, rust_command], {
        "c_compiler": gcc_version,
        "c_flags": "-std=c11 -O2 -Wall -Wextra -Werror",
        "go_compiler": go_version,
        "go_build_settings": "go build -trimpath (default compiler optimization settings)",
        "rust_compiler": rust_version,
        "rust_flags": "--edition=2021 -C opt-level=3 -C codegen-units=1" + (f" --target {rust_target}" if rust_target else ""),
    }


def run(iterations: int, warmups: int, fixture_paths: list[Path], output_path: Path | None) -> dict:
    if iterations < 1 or warmups < 0:
        raise ValueError("iterations must be positive and warmups must not be negative")
    records = []
    summary = []
    with tempfile.TemporaryDirectory(prefix="asm-language-bench-") as temporary:
        commands, toolchain = build_commands(Path(temporary))
        for fixture in fixture_paths:
            expected = json.loads((EXPECTED / f"{fixture.stem}.json").read_text(encoding="utf-8"))
            for language, command, version, compile_ns, environment in commands:
                for strategy in ("asm", "baseline"):
                    expected_output = expected if strategy == "asm" else baseline_expected(fixture)
                    for _ in range(warmups):
                        warm_output, _, _, _, _ = execute(command, fixture, environment, strategy)
                        if not isinstance(warm_output.get("elapsed_ns"), int) or warm_output["elapsed_ns"] <= 0:
                            raise RuntimeError(f"{language} reported an invalid timer value during warm-up on {fixture.name}")
                        if normalized(warm_output) != expected_output:
                            raise RuntimeError(f"{language} {strategy} produced incorrect warm-up output for {fixture.name}")
                    language_times = []
                    wall_times = []
                    for repetition in range(1, iterations + 1):
                        actual, wall_ns, peak_memory, cpu_percent, operation_metrics = execute(command, fixture, environment, strategy)
                        if not isinstance(actual.get("elapsed_ns"), int) or actual["elapsed_ns"] <= 0:
                            raise RuntimeError(f"{language} reported an invalid timer value on {fixture.name}; measurement rejected")
                        if normalized(actual) != expected_output:
                            raise RuntimeError(f"{language} {strategy} produced incorrect output for {fixture.name}; measurements rejected")
                        language_times.append(actual["elapsed_ns"])
                        wall_times.append(wall_ns)
                        records.append({
                        "run_id": str(uuid.uuid4()),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "benchmark_format": "ASM-BENCH-V1",
                        "measurement_revision": "asm-bench-v2.0",
                        "measurement_validity": "accepted",
                        "strategy": strategy,
                        "language_metrics": {
                            "language": language,
                            "strategy": strategy,
                            "measurement_revision": "asm-bench-v2.0",
                            "measurement_validity": "accepted",
                            "fixture_id": actual["input_id"],
                            "repetition": repetition,
                            "warmup_iterations": warmups,
                            "execution_time_ns": actual["elapsed_ns"],
                            "execution_time_ms": actual["elapsed_ns"] / 1e6,
                            "process_wall_time_ns": wall_ns,
                            "memory_bytes": peak_memory,
                            "cpu_utilization_percent": cpu_percent,
                            "throughput_tokens_per_second": (actual["original_source_tokens"] * 1e9 / actual["elapsed_ns"]) if actual["elapsed_ns"] else None,
                            "output_size_bytes": len(json.dumps(normalized(actual), ensure_ascii=False).encode("utf-8")),
                            "operation_times_ns": operation_metrics,
                            "compile_time_ns": compile_ns,
                            "toolchain_version": version,
                            "toolchain_settings": toolchain,
                        },
                        "correctness": "passed",
                        "raw_output": normalized(actual),
                        "error": None,
                        })
                    summary.append({
                        "fixture_id": fixture.stem,
                        "language": language,
                        "strategy": strategy,
                        "repetitions": iterations,
                        "median_execution_ns": statistics.median(language_times),
                        "min_execution_ns": min(language_times),
                        "max_execution_ns": max(language_times),
                        "median_process_wall_ns": statistics.median(wall_times),
                    })
    if output_path:
        append_records(output_path, records)
    return {"toolchain": toolchain, "summary": summary, "runs": records, "results_appended_to": str(output_path) if output_path else None}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="append", help="fixture filename or path; repeatable; defaults to all checked-in fixtures")
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--output", type=Path, help="append per-run JSONL records here; omitted means report only")
    args = parser.parse_args()
    fixtures = [Path(item).resolve() for item in args.fixture] if args.fixture else sorted(INPUTS.glob("*.asmbench"))
    if not fixtures:
        parser.error("no benchmark fixtures found")
    report = run(args.iterations, args.warmups, fixtures, args.output)
    print(json.dumps({"toolchain": report["toolchain"], "summary": report["summary"], "results_appended_to": report["results_appended_to"]}, indent=2))


if __name__ == "__main__":
    main()
