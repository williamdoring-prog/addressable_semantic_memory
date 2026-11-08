# Three Language Benchmark Findings — 2026-11-05

This report records the latest correctness-gated measurements for JavaScript, C, and Go. The root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md) remain authoritative; implementations follow the shared [ASM-BENCH-V1 contract](../benchmarks/formats/ASM_BENCHMARK_V1.md). Earlier [JavaScript/C findings](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05.md) and [three-language reports](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_7.md), [8](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_8.md), and [9](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_9.md) remain preserved.

## Measurement scope

- JavaScript: Node.js v25.9.0.
- C: GCC 11.2.0, `-std=c11 -O2 -Wall -Wextra -Werror`.
- Go: go1.17 windows/amd64, built with `go build -trimpath`; the runner sets the installed MSYS2 distribution's GOROOT for each build/run process.
- Fixtures: small (3 fragments), medium (6), and large (12); the checked-in input files are the exact benchmark data.
- Protocol: 2 warmups and 5 measured repetitions per language and fixture. Each run is checked against expected output first. The runner rejects invalid or zero total timers and validates all per-operation metrics.
- Overall `execution_time_ns` covers fixture reading/parsing, retrieval, address lookup, expansion, and assembly. It excludes serialization. Separate operation timings are emitted for input parsing, retrieval/filtering/ranking, address lookup, expansion/assembly, and JSON serialization/output. `process_wall_time_ns` also includes process launch. Build time is recorded separately.
- Windows peak working set is measured from process memory counters. CPU utilization is calculated from process CPU time for runs at least 50 ms long; shorter runs are marked unavailable because CPU accounting is too coarse. Runtime memory includes language runtime overhead. Other platforms without Windows process APIs record resource metrics as `null`.
- Summary values below use records tagged `asm-bench-v1.7`; all older append-only results are retained and kept separate by revision.

## Total runtime and peak working set medians

| Fixture | Fragments | JavaScript (ms / MiB) | C (ms / MiB) | Go (ms / MiB) |
|---|---:|---:|---:|---:|
| Small factual | 3 | 1.1024 / 36.28 | 0.2864 / 3.77 | 0.2872 / 7.04 |
| Medium numeric | 6 | 1.1744 / 36.30 | 0.3257 / 3.77 | 0.3232 / 7.04 |
| Large multifactual | 12 | 1.3754 / 36.37 | 0.3200 / 3.77 | 0.3449 / 7.09 |

## Per-operation medians

Median microseconds across the 15 measured runs per language (three fixtures × five repetitions); sub-resolution `null` samples are omitted from the operation median:

| Language | Input/read + parse | Retrieval | Address lookup | Expansion/assembly | Serialization/output |
|---|---:|---:|---:|---:|---:|
| JavaScript | 883.6 | 229.1 | 33.5 | 16.4 | 188.0 |
| C | 280.3 | 23.1 | 0.1 | 0.9 | 129.6 |
| Go | 291.4 | 25.2 | 1.0 | 1.2 | 200.8 |

JavaScript process CPU medians were 85.5%, 83.18%, and 80.9% for the large, medium, and small fixtures respectively. C and Go runs were shorter than the supported CPU accounting threshold, so their CPU metrics are unavailable. These values describe this machine and these exact implementations; they are not a general language ranking. Input parsing includes fixture file reading. Peak working set includes each runtime's process overhead.

## Correctness and validation

- JavaScript, C, and Go matched expected standard output on all three fixtures.
- Escaped tabs, newlines, and backslashes round-tripped exactly; invalid headers, escapes, and negative budgets were rejected.
- Unicode addresses used UTF-8 bytewise ordering consistently across implementations.
- Lookup/expansion addresses resolved to exact fixture source text; source, question, and context token counts matched the common tokenizer.
- Repeated normalized outputs matched within and across implementations.
- The v1.7 batch appended 45 correctness-passed records to `data/results/language_benchmarks.jsonl`; all previous results were preserved.
- `python -m unittest discover -s tests -v` — 29 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed, covering language and per-operation runtime, memory, and CPU chart rendering.
- `go vet`, Python compilation, JavaScript syntax checks, and `git diff --check` passed.

## Remaining requirements

Rust is not installed, so four-language correctness and performance acceptance remain incomplete. Live Ollama inference/quality validation also remains unavailable; no local Ollama service was listening during this work.
