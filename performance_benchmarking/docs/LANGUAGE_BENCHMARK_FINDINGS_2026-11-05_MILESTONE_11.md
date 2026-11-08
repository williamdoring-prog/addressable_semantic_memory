# Four Language Benchmark Findings — 2026-11-05

This report records the first complete correctness-gated measurements for JavaScript, C, Go, and Rust. The root [language benchmark requirements](../LANGUAGE_BENCHMARKS.md) remain authoritative; implementations share the [ASM-BENCH-V1 contract](../benchmarks/formats/ASM_BENCHMARK_V1.md). Earlier milestone reports remain preserved, including the [three-language measurements](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_10.md).

## Measurement scope

- JavaScript: Node.js v25.9.0.
- C: GCC 11.2.0, `-std=c11 -O2 -Wall -Wextra -Werror`.
- Go: go1.17 windows/amd64, built with `go build -trimpath`; the runner sets the adjacent MSYS2 GOROOT per process.
- Rust: rustc 1.99.1, `--edition=2021 -C opt-level=3 -C codegen-units=1 --target x86_64-pc-windows-gnu`; Rustup selects the installed stable toolchain per process, and MinGW GCC provides the linker.
- Fixtures: small (3 fragments), medium (6), and large (12); checked-in fixture files are the exact input data.
- Protocol: 2 warmups and 5 measured repetitions per language and fixture. Outputs are checked against expected JSON before accepting each measurement. The runner rejects invalid or zero total timers and invalid operation metrics.
- Overall runtime covers fixture reading/parsing, retrieval, address lookup, expansion, and context assembly. It excludes serialization. `process_wall_time_ns` includes launch and output. Build time, runtime version, compiler settings, output size, throughput, resource metrics, and per-operation times are stored in each record.
- Peak working set and CPU use are measured from Windows process APIs. CPU utilization is recorded only for processes lasting at least 50 ms, due Windows accounting granularity. Shorter runs retain `null`. Peak memory includes language runtime overhead.
- Summary values use records tagged `asm-bench-v1.8`. Prior pilot and three-language batches remain preserved in the append-only JSONL and are separated by measurement revision.

## Total runtime medians

| Fixture | Fragments | JavaScript (ms) | C (ms) | Go (ms) | Rust (ms) |
|---|---:|---:|---:|---:|---:|
| Small factual | 3 | 1.0412 | 0.3073 | 0.3006 | 0.3652 |
| Medium numeric | 6 | 1.1128 | 0.2935 | 0.2901 | 0.3266 |
| Large multifactual | 12 | 1.3986 | 0.3552 | 0.3233 | 0.4034 |

## Peak working set medians

| Fixture | JavaScript (MiB) | C (MiB) | Go (MiB) | Rust (MiB) |
|---|---:|---:|---:|---:|
| Small factual | 36.25 | 3.77 | 7.04 | 4.86 |
| Medium numeric | 36.27 | 3.77 | 7.04 | 4.86 |
| Large multifactual | 36.38 | 3.77 | 7.05 | 4.86 |

## Per-operation medians

Median microseconds across each language's 15 observations (three fixtures × five repetitions). Sub-resolution `null` samples are omitted from an operation median.

| Language | Input/read + parse | Retrieval | Address lookup | Expansion/assembly | Serialization/output |
|---|---:|---:|---:|---:|---:|
| JavaScript | 834.4 | 232.2 | 32.5 | 15.9 | 168.8 |
| C | 289.9 | 19.1 | 0.2 | 0.9 | 126.6 |
| Go | 282.8 | 21.9 | 1.1 | 1.1 | 195.1 |
| Rust | 352.8 | 12.7 | 1.5 | 1.4 | 141.5 |

JavaScript's median process CPU utilization was 82.12%. C, Go, and Rust runs were shorter than the supported CPU accounting threshold. Results describe this host, toolchain setup, and exact workload; they do not establish a general language ranking. Input parsing includes fixture file reading, and process memory includes runtime startup costs.

## Correctness and validation

- All four implementations matched expected standard output for every checked-in fixture.
- Escaped tabs, newlines, and backslashes round-tripped exactly; invalid headers, escapes, and negative budgets were rejected.
- Unicode addresses followed the same UTF-8 bytewise order in all four implementations.
- Lookups and expansions were checked against exact source fragments; source, question, and context token counts matched.
- Repeated normalized outputs matched within each implementation and across all four implementations.
- The v1.8 run appended 60 correctness-passed records (3 fixtures × 4 languages × 5 repetitions) to `data/results/language_benchmarks.jsonl`; all previous results were preserved.
- `python -m unittest discover -s tests -v` — 29 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed with all four languages and total/per-operation/resource charts.
- `go vet`, Rust formatting checks, Python compilation, JavaScript syntax checks, and `git diff --check` passed.

## Remaining project validation

The required four-language benchmark suite is complete. The local Ollama API adapter has unit coverage and local model manifests are present, but the Ollama service was not running; live inference and answer-quality testing remain for the final project review.
