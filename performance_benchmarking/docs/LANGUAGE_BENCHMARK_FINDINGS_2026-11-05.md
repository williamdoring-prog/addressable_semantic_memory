# Language Benchmark Findings — 2026-11-05

This report records measurements from the available JavaScript and C implementations. The planned four-language comparison remains defined by the root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md); the shared operation contract is documented in [ASM-BENCH-V1](../benchmarks/formats/ASM_BENCHMARK_V1.md). These findings do not establish a universal language winner.

## Measurement scope

- Implementations: JavaScript on Node.js v25.9.0; C compiled by GCC 11.2.0 with `-std=c11 -O2 -Wall -Wextra -Werror`.
- Inputs: the checked-in small, medium, and large fixtures (3, 6, and 12 source fragments).
- Protocol: 2 warmups and 5 measured repetitions per language and fixture; each output was checked against expected output before recording.
- `execution_time_ns` is implementation-reported monotonic wall time from before fixture reading through context assembly; serialization is excluded. `process_wall_time_ns` also includes process launch and JSON output.
- Compiler time is recorded separately. Memory and CPU metrics are `null`/unavailable and are not inferred.
- The records from this corrected run carry `measurement_revision: asm-bench-v1.1`. An earlier pilot batch remains in the append-only JSONL file with no revision marker; its timer scope was inconsistent and it should not be combined with v1.1 measurements.

## Observed medians

| Fixture | Fragments | JavaScript median (ms) | C median (ms) |
|---|---:|---:|---:|
| Small factual | 3 | 2.6819 | 0.3227 |
| Medium numeric | 6 | 2.6032 | 0.3585 |
| Large multifactual | 12 | 2.5985 | 0.3824 |

Values are medians of five runs on this environment. The fixture set is small, process startup materially affects whole-process timings, and neither CPU nor memory usage was measured. Treat these as implementation observations for the specified contract and machine only.

## Correctness and test results

- JavaScript and C outputs matched all three expected fixtures, excluding only `elapsed_ns`.
- Every returned lookup/expansion address was checked against its exact fixture fragment; source, question, and assembled-context token counts matched the shared tokenizer.
- Repeated normalized outputs matched within each implementation and between JavaScript and C.
- Both implementations rejected malformed input in the automated checks.
- The repeated runner appended measurements only after correctness checks passed.
- `python -m unittest discover -s tests -v` — 27 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed, including language-result rendering.
- Python compilation, JavaScript syntax checks, and `git diff --check` passed.

## Outstanding work

Go and Rust runs are not available: the installed Go command has no valid GOROOT and `rustc` is unavailable. Full four-language equivalence, performance comparison, per-operation comparisons, and memory/resource measurements remain outstanding. Live Ollama faithfulness testing also remains outside this language microbenchmark report.
