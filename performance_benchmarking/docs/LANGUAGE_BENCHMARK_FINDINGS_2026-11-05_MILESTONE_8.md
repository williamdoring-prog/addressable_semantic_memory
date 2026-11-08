# Three Language Benchmark Findings — 2026-11-05

This report records the latest correctness-gated measurements for JavaScript, C, and Go. The root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md) remain authoritative; the common fixture contract is [ASM-BENCH-V1](../benchmarks/formats/ASM_BENCHMARK_V1.md). Earlier [JavaScript/C findings](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05.md) and [three-language findings](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_7.md) are retained as historical milestones.

## Measurement scope

- JavaScript: Node.js v25.9.0.
- C: GCC 11.2.0, `-std=c11 -O2 -Wall -Wextra -Werror`.
- Go: go1.17 windows/amd64, built with `go build -trimpath`; the runner sets the installed MSYS2 distribution's GOROOT for each build/run process.
- Inputs: the checked-in small, medium, and large fixtures (3, 6, and 12 fragments).
- Protocol: 2 warmups and 5 measured repetitions for each language and fixture. Outputs were checked against expected fixtures before recording. Invalid or zero timers reject a run.
- `execution_time_ns` covers fixture reading, parsing, retrieval, address lookup, expansion, and context assembly. Serialization is excluded. `process_wall_time_ns` includes process launch and JSON serialization. Build time is recorded separately.
- Windows peak working set is captured from process memory counters. CPU utilization is calculated from Windows process CPU time for runs at least 50 ms long; shorter runs leave it unavailable because system CPU accounting is too coarse at that duration. Other platforms without these process APIs record `null`.
- The table below uses only records tagged `asm-bench-v1.5`. All earlier JSONL records remain preserved and are kept separate by revision; the untagged pilot runs had inconsistent timing scope.

## Observed medians

| Fixture | Fragments | JavaScript (ms) | C (ms) | Go (ms) | Peak working set JS / C / Go (MiB) |
|---|---:|---:|---:|---:|---:|
| Small factual | 3 | 1.3432 | 0.2919 | 0.2759 | 36.34 / 3.76 / 7.04 |
| Medium numeric | 6 | 1.3937 | 0.2901 | 0.2883 | 36.32 / 3.76 / 7.00 |
| Large multifactual | 12 | 1.4077 | 0.3366 | 0.3133 | 36.36 / 3.76 / 7.01 |

CPU median utilization was 81.06% (small), 80.88% (medium), and 81.49% (large) for JavaScript. C and Go executions were shorter than the CPU accounting threshold, so their CPU values are unavailable. Measurements apply only to this machine and toolchain; they do not establish a general language ranking. Per-operation timing remains outstanding.

## Correctness and validation

- All three implementations matched the expected outputs for all three checked-in fixtures.
- Escaped tabs, newlines, and backslashes round-tripped exactly across all implementations.
- Invalid headers, invalid escape sequences, and negative budgets were rejected across all implementations.
- Lookup and expansion addresses resolved to exact fixture source text; source, question, and context token counts matched the contract.
- Repeated normalized outputs matched within each implementation and across all three implementations.
- The v1.5 run appended 45 correctness-passed records (3 fixtures × 3 languages × 5 repetitions) to append-only `data/results/language_benchmarks.jsonl`.
- `python -m unittest discover -s tests -v` — 28 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed, including runtime/memory/CPU chart rendering for the three languages.
- Python compilation, JavaScript syntax checks, and `git diff --check` passed.

## Remaining requirements

Rust is not installed, so the four-language benchmark suite and its acceptance criteria are incomplete. Per-operation comparisons and live Ollama quality experiments also remain outstanding.
