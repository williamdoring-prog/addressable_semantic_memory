# Implementation Log — 2026-11-05

This log records work performed and verification results. Requirements remain in the root [README](../README.md), [ASM specification](../ASM_SPECIFICATION.md), [architecture](../ARCHITECTURE.md), [benchmark protocol](../BENCHMARK_PROTOCOL.md), [web interface specification](../WEB_INTERFACE.md), [directory structure](../DIRECTORY_STRUCTURE.md), and [work queue](../WORK_QUEUE.md); this file does not replace or duplicate them.

## Completed and verified

### ASM-001 — Project directory structure

- Added tracked placeholders for the agreed project folders and created separate `app/interface/` and `app/controller/` modules.
- Updated the root directory structure document to reflect the current folders and the project documentation rules.
- Directory check passed for all 18 required directories.

### ASM-002–006 — Local application foundation

- Added the standard-library Python HTTP backend, browser interface, source/question input, experiment configuration, and append-only JSONL result storage.
- Added local health/model discovery and optional Ollama generation. Offline preparation works without Ollama.
- Verified a live loopback smoke flow: browser document GET returned HTTP 200; ASM experiment POST returned HTTP 201; results GET returned the saved temporary run; JavaScript asset GET returned HTTP 200. The smoke run used a temporary result file and did not add a benchmark result to `data/results/`.

### ASM-010–014 — Baseline request and accounting

- Added baseline context preparation, the local Ollama adapter, prompt and response token fields, response timing, exact-match evaluation when an expected answer is supplied, and persistent run records.
- Unit tests verify the Ollama request/response shape with a mocked local response. Live inference was not available because no Ollama service/model was running.

### ASM-020, ASM-021, ASM-023–028 — Initial addressable engine

- Added fragment and representation records, stable source-derived addresses, source fragmentation, keyword retrieval, address resolution, duplicate-aware lookup, exact source expansion, context-budget assembly, and measurements.
- Source reconstruction, source preservation, unknown addresses, duplicate references, retrieval, and budget behavior are covered by unit tests.
- **ASM-022 is not complete.** The current compact keyword index is a deterministic retrieval baseline, not semantic compression. See the [work queue](../WORK_QUEUE.md).

### ASM-030–035 — Benchmark request flow and persistence

- Added the common Ollama request path for baseline and ASM strategies, configurable evidence/context budgets, a single-run API, browser-driven repetitions, and append-only result storage.
- Automated tests cover the offline path and request construction. Live inference remains unverified; experimental equivalence validation (ASM-036) is still open.

## Verification results

- `python -m unittest discover -s tests -v` — **15 tests passed**.
- `python -m compileall -q asm app tests` — passed.
- `node --check app/interface/app.js` — passed.
- `git diff --check` — passed.
- Live HTTP smoke test — GET `/` 200, POST `/api/experiments` 201, GET `/api/results` 200, GET `/app.js` 200; result storage was temporary.

## Outstanding work and constraints

- Semantic compression is not implemented; the current ASM path is lexical and extractive.
- A live Ollama run and answer-quality evaluation could not be performed because the local Ollama service was unavailable.
- Go is present only as a misconfigured command with no valid GOROOT; Rust `rustc` is unavailable. Cross-language benchmark implementation and verification remain blocked.
- Several requested dashboard charts and complete experimental validation remain outstanding; no charts use fabricated data.
