# Three Language Benchmark Findings — 2026-11-05

This report records the latest correctness-gated measurements for JavaScript, C, and Go. The root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md) remain authoritative; the common fixture contract is [ASM-BENCH-V1](../benchmarks/formats/ASM_BENCHMARK_V1.md). Earlier findings reports are preserved: [JavaScript/C](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05.md), [three-language run with timing only](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_7.md), and [resource collection milestone](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_8.md).

## Measurement scope

- JavaScript: Node.js v25.9.0.
- C: GCC 11.2.0, `-std=c11 -O2 -Wall -Wextra -Werror`.
- Go: go1.17 windows/amd64, built with `go build -trimpath`; the runner sets the installed MSYS2 distribution's GOROOT for each build/run process.
- Inputs: the checked-in small, medium, and large fixtures (3, 6, and 12 fragments).
- Protocol: 2 warmups and 5 measured repetitions per language and fixture. Outputs were checked against expected fixtures before recording; invalid or zero timers reject a run.
- `execution_time_ns` covers fixture reading, parsing, retrieval, address lookup, expansion, and context assembly. Serialization is excluded. `process_wall_time_ns` includes process launch and JSON serialization. Build time is recorded separately.
- Windows peak working set is read from process memory counters. CPU utilization is calculated from Windows process CPU time only for runs at least 50 ms long; shorter runs keep it unavailable because CPU accounting is too coarse. Other platforms without these APIs record `null`.
- The results below use only records tagged `asm-bench-v1.6`. All earlier JSONL records are preserved and separated by revision; the untagged pilot records had inconsistent timing scope.

## Observed medians

| Fixture | Fragments | JavaScript (ms) | C (ms) | Go (ms) | Peak working set JS / C / Go (MiB) |
|---|---:|---:|---:|---:|---:|
| Small factual | 3 | 1.4233 | 0.3271 | 0.3324 | 36.29 / 3.76 / 7.00 |
| Medium numeric | 6 | 1.4645 | 0.3248 | 0.3034 | 36.34 / 3.76 / 7.00 |
| Large multifactual | 12 | 1.5594 | 0.3545 | 0.3141 | 36.36 / 3.76 / 7.06 |

JavaScript's median process CPU utilization was 81.04%, 80.90%, and 80.93% for the small, medium, and large fixtures. C and Go process runs were shorter than the CPU accounting threshold, so CPU utilization is unavailable for them. These results describe only this host and toolchain; they do not establish a general language ranking. Per-operation timing remains outstanding.

## Correctness and validation

- All three implementations matched expected output for all three checked-in fixtures.
- Escaped tabs, newlines, and backslashes round-tripped exactly; invalid headers, escapes, and negative budgets were rejected.
- Unicode addresses were ordered by UTF-8 byte sequence consistently across implementations.
- Lookup/expansion addresses resolved to exact source fragments; source, question, and context token counts matched the contract.
- Repeated normalized outputs matched within each implementation and across all three implementations.
- The v1.6 batch appended 45 correctness-passed records (3 fixtures × 3 languages × 5 repetitions) to append-only `data/results/language_benchmarks.jsonl`.
- `python -m unittest discover -s tests -v` — 29 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed, including runtime, memory, and CPU chart rendering.
- `go vet`, Python compilation, JavaScript syntax checks, and `git diff --check` passed.

## Remaining requirements

Rust is not installed, so the four-language benchmark suite and acceptance criteria remain incomplete. Per-operation comparisons and live Ollama quality experiments also remain outstanding.
