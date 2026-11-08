# Implementation Log — Comparison and Results Interface

This supplementary log records the paired-comparison and results-interface milestone. The authoritative requirements remain in the root [benchmark protocol](../BENCHMARK_PROTOCOL.md), [ASM specification](../ASM_SPECIFICATION.md), [web interface specification](../WEB_INTERFACE.md), and [work queue](../WORK_QUEUE.md). Earlier reports are retained as historical milestone records.

## Implemented

- Added paired baseline/ASM repetitions under one comparison ID, alternating run order and recording a shared input/settings signature. Controls include source, question, context budget, category, expected answer, selected model/version, expansion policy, tokenizer, and generation settings.
- Model version equivalence is reported as false when a live-model run cannot establish a digest.
- Preserved separators in source fragments; expanding every address and concatenating the fragments reconstructs the original source exactly.
- Added retrieval, expansion, representation indexing, fragmentation, assembly, and total execution timing fields.
- Added paired-run aggregation (median/min/max, response count, error count), token, timing, compression, retrieval/expansion, exact-match, quality/token, and context-budget charts. Language panels show empty states until actual language measurements exist.
- Added detailed comparison/model-call inspection and expanded CSV export. JSON export retains each raw result.
- UI defaults to three paired repetitions; all runs remain individually stored.

## Verification

- `python -m unittest discover -s tests -v` — **21 tests passed**.
- `node --test tests/test_ui.mjs` — **1 UI behavior test passed** (paired submit, progress, stored-result rendering, and empty data states).
- `python -m compileall -q asm app tests` — passed.
- `node --check app/interface/app.js` — passed.
- `git diff --check` — passed.

Tests use offline data or mocked local-model responses. No fabricated chart values or benchmark results were added.

## Outstanding work

- Live Ollama semantic summary faithfulness and answer-quality experiments remain unverified.
- Cross-language benchmark implementations/comparisons remain open; Go has no valid GOROOT and Rust `rustc` is unavailable in the current environment.
- Full benchmark suite, reproducibility analysis, resource measurement, and findings remain open.
