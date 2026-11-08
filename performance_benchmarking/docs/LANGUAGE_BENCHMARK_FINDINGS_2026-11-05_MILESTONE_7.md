# Three Language Benchmark Findings — 2026-11-05

This report records the latest correctness-gated measurements for JavaScript, C, and Go. The root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md) remain authoritative; the common fixture contract is [ASM-BENCH-V1](../benchmarks/formats/ASM_BENCHMARK_V1.md). The earlier [JavaScript/C findings report](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05.md) is retained as a historical milestone.

## Measurement scope

- JavaScript: Node.js v25.9.0.
- C: GCC 11.2.0, `-std=c11 -O2 -Wall -Wextra -Werror`.
- Go: go1.17 windows/amd64, built with `go build -trimpath`; the runner sets the installed MSYS2 distribution's GOROOT for each build/run process.
- Inputs: the checked-in small, medium, and large fixtures (3, 6, and 12 fragments).
- Protocol: 2 warmups and 5 measured repetitions for each language and fixture. Each result was checked against its expected fixture before recording. Invalid or zero timers reject the batch.
- `execution_time_ns` covers fixture reading, parsing, retrieval, address lookup, expansion, and context assembly. Serialization is excluded. `process_wall_time_ns` includes launch and JSON serialization. Build time is recorded separately.
- Peak memory and CPU utilization were unavailable and are recorded as `null`; no values are estimated.
- The table below uses only records tagged `asm-bench-v1.3`. All earlier JSONL records are preserved. Untagged pilot records had inconsistent timing scope; other tagged batches are kept separate by the dashboard.

## Observed medians

| Fixture | Fragments | JavaScript (ms) | C (ms) | Go (ms) |
|---|---:|---:|---:|---:|
| Small factual | 3 | 2.4564 | 0.3416 | 0.3014 |
| Medium numeric | 6 | 2.5958 | 0.2943 | 0.2906 |
| Large multifactual | 12 | 2.4517 | 0.3554 | 0.3222 |

These measurements apply to this machine, toolchain configuration, and fixture set. They do not establish a general language ranking. The runner reports total operation time; per-operation timing and resource measurements remain outstanding.

## Correctness and validation

- All three implementations matched the expected outputs on all three checked-in fixtures.
- Valid escaped tabs, newlines, and backslashes round-tripped exactly across all three implementations.
- Invalid headers, invalid escape sequences, and negative budgets were rejected across all three implementations.
- Address lookups and expanded text were checked against their exact fixture source fragments. Source, question, and context token counts were verified.
- Repeated normalized outputs matched within each implementation and across all three implementations.
- The final v1.3 run appended 45 correctness-passed records (3 fixtures × 3 languages × 5 repetitions) to the append-only `data/results/language_benchmarks.jsonl`.
- `python -m unittest discover -s tests -p test_language_benchmarks.py -v` — 6 tests passed.

## Remaining requirements

Rust is not installed, so this is not the required four-language benchmark suite. The complete cross-language acceptance, per-operation timing, and memory/resource comparison remain incomplete until the Rust implementation and measurements can be built and verified.
