
# Programming Language Benchmarks

## Objective

Compare the execution performance of equivalent ASM operations and a no-ASM baseline implemented in three languages.

Languages:

1. C
2. Go
3. Rust

Note (2026-11-06): the JavaScript implementation was removed from the standard language comparison together with its tests. Historical JavaScript measurements remain stored in `data/results/language_benchmarks.jsonl` and are still displayed by the results page.

## Important Separation

These benchmarks measure implementation performance.

They do not measure the intelligence or reasoning capability of an LLM.

Keep language results separate from ASM-versus-baseline LLM results.

## Required Operations

Implement equivalent versions of:

1. Input parsing.
2. Fragment processing.
3. Address lookup.
4. Semantic-unit filtering.
5. Retrieval.
6. Expansion.
7. Context assembly.
8. Serialization.

## Test Data

All implementations must use identical input fixtures.

Create at least three dataset sizes:

- Small.
- Medium.
- Large.

Document their exact sizes and contents.

The current shared inputs are `benchmarks/fixtures/inputs/small-factual.asmbench` (3 fragments), `medium-numeric.asmbench` (6 fragments), and `large-multifact.asmbench` (12 fragments). Those fixture files are the authoritative exact contents; matching expected JSON is stored in `benchmarks/fixtures/expected_outputs/`. Each language runs both `asm` and `baseline` strategies against every fixture. The baseline concatenates original fragment text in fixture order and takes the source prefix through the last word token fitting the same evidence budget; it skips ASM retrieval, address lookup, and expansion. Implementations follow the shared [ASM-BENCH-V1 input/output and timing contract](benchmarks/formats/ASM_BENCHMARK_V1.md).

## Correctness

Before performance testing:

- Validate outputs.
- Compare results against expected fixtures.
- Verify address resolution.
- Verify reconstruction.
- Reject invalid outputs.

Performance measurements from incorrect implementations must not be accepted.

## Performance Measurements

Record:

- Execution time.
- Throughput.
- Peak memory usage.
- CPU utilization where available.
- Output size.
- Compilation time separately.
- Runtime version.
- Compiler version.
- Compiler optimization settings.

## Test Conditions

Use equivalent algorithms and work.

Compile C and Rust using optimized release configurations.

Record Go build settings.

Perform warm-up iterations.

Run multiple repetitions.

Report median and spread.

## Results

Provide:

- Language comparison charts.
- Per-operation comparison.
- Dataset-size comparison.
- Memory comparison.
- Correctness results.

Do not declare a universal winner based on a single operation.

## Acceptance Criteria

All three implementations must:

- Produce equivalent outputs.
- Pass the same test fixtures.
- Support the same operations.
- Produce machine-readable benchmark results.
- Match baseline prefix-truncation outputs across all fixtures and record strategy alongside each run.
