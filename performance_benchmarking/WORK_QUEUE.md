
# ASM Development Work Queue

Statuses:
- NOT STARTED
- IN PROGRESS
- BLOCKED
- REVIEW
- COMPLETE

Only work on one task at a time.

## Phase 1 — Foundation

- [x] ASM-001: Create project directory structure.
- [x] ASM-002: Create minimal local backend.
- [x] ASM-003: Create browser home page.
- [x] ASM-004: Implement text input.
- [x] ASM-005: Implement basic result storage.
- [x] ASM-006: Verify application starts and operates locally.

## Phase 2 — Baseline

- [x] ASM-010: Implement normal LLM request.
- [x] ASM-011: Implement token counting.
- [x] ASM-012: Record response time.
- [x] ASM-013: Record baseline results.
- [x] ASM-014: Add baseline tests.

## Phase 3 — ASM Engine

- [x] ASM-020: Define ASM data structures.
- [x] ASM-021: Implement source fragmentation.
- [x] ASM-022: Implement semantic compression (local Ollama provider; output and address coverage are validated).
- [x] ASM-023: Implement address assignment.
- [x] ASM-024: Implement address resolution.
- [x] ASM-025: Implement retrieval.
- [x] ASM-026: Implement expansion.
- [x] ASM-027: Implement context assembly.
- [x] ASM-028: Test source reconstruction.

## Phase 4 — Benchmark Integration

- [x] ASM-030: Implement ASM-enabled LLM requests.
- [x] ASM-031: Implement ASM-disabled requests.
- [x] ASM-032: Implement context budget selection.
- [x] ASM-033: Implement experiment runner.
- [x] ASM-034: Implement repeated experiments.
- [x] ASM-035: Implement result persistence.
- [x] ASM-036: Validate experimental equivalence.

## Phase 5 — Language Implementations

- [x] ASM-040: Define common benchmark input/output (ASM-BENCH-V1; see `benchmarks/formats/ASM_BENCHMARK_V1.md`).
- [x] ASM-041: Implement JavaScript benchmark (fixtures, lookup, retrieval, expansion, assembly, serialization).
- [x] ASM-042: Implement C benchmark (same contract; strict optimized GCC build).
- [x] ASM-043: Implement Go benchmark (Go 1.17; process-local GOROOT recovery for the installed MSYS2 distribution).
- [x] ASM-044: Implement Rust benchmark (Rustup stable selected per process; Windows GNU target linked with MinGW GCC).
- [x] ASM-045: Implement correctness comparisons (all four implementations match expected fixture outputs; invalid input, escape, and Unicode ordering checks pass).
- [x] ASM-046: Implement performance measurements (all four implementations have repeated total/per-operation results and recorded build/runtime/resource metrics where available).

## Phase 6 — Results Interface

- [x] ASM-050: Build benchmark configuration page.
- [x] ASM-051: Build experiment progress display.
- [x] ASM-052: Build results overview.
- [x] ASM-053: Build token comparison charts.
- [x] ASM-054: Build answer quality charts (normalized exact-match score only).
- [x] ASM-055: Build execution performance charts.
- [x] ASM-056: Build language comparison charts (total and per-operation timing, peak memory, and CPU utilization by fixture/language when measured; missing metrics remain empty).
- [x] ASM-057: Build detailed experiment inspection.
- [x] ASM-058: Implement data export.

## Phase 7 — Validation

- [x] ASM-060: Run complete benchmark suite (four languages, three fixtures, two warmups, five repetitions; correctness-gated batch recorded).
- [x] ASM-061: Verify source traceability (language outputs resolve to exact fixture source text; ASM reconstruction tests pass).
- [x] ASM-062: Verify token accounting (fixture source, question, and assembled context counts validated for all four languages).
- [x] ASM-063: Verify reproducibility (repeated normalized outputs match across repetitions and implementations).
- [x] ASM-064: Document findings (`docs/LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_11.md`; measured scope and unavailable metrics stated; earlier reports preserved).
- [x] ASM-065: Final project review (automated checks and live local Ollama paired comparison completed; see `docs/PROJECT_VERIFICATION_2026-11-05_MILESTONE_12.md`).
- [x] ASM-066: Add a correctness-gated no-ASM prefix baseline to all four language benchmarks. v2.0 recorded 120 accepted runs; v1.9 pilot baseline records are retained and marked rejected due to unequal retrieval work.
- [x] ASM-067: Add a print-ready IMRAD summary report with readable comparison labels, separate per-strategy medians, rejected-record disclosure, and browser Save as PDF workflow.
- [x] ASM-068: Add a separate local-model criterion evaluator with per-criterion pass/fail rationales, percentage scoring, dashboard charts, and IMRAD PDF findings/conclusion.

## Phase 8 — Research Evaluation

- [ ] ASM-069 (BLOCKED): Run the multi-budget, repeated context pressure curve across ASM and baseline. Initial local-model smoke runs are recorded in `data/results/context_pressure_2026-11-05.jsonl`; ASM semantic compression fails on the long synthetic source. See `docs/CONTEXT_PRESSURE_PILOT_2026-11-05.md`.
- [x] ASM-070 (COMPLETE, 2026-11-06): Add three selectable Standard Benchmark execution modes (Smoke Test, Single-Pass Test, Full) and remove JavaScript from the standard language comparison and from all JavaScript testing.

  Scope decided with the user: the modes govern the fixed standard LLM suite only (language microbenchmarks stay a separate CLI runner); "remove the JavaScript testing" covers the node UI checks (`tests/test_ui.mjs` deleted) and JavaScript in the language runner and its tests.

  Files modified or created: `benchmarks/standard_suite.py` (added `SMOKE_CASE_IDS`, `build_smoke_suite()`); `app/controller/server.py` (`STANDARD_MODES`, `SMOKE_BUDGET=2048`, mode-aware `start_standard_benchmark(mode)` with modes `smoke` | `single_pass` | `full`, full mode preserves the unchanged methodology of repeat 3; `_run_standard_job` parameterized; every stored run records `benchmark_mode`); `app/interface/index.html` and `app/interface/app.js` (mode selector with per-mode descriptions, scope cells, estimate text driven by the selected mode, POST sends `{"mode": ...}`, job display shows the mode label); `benchmarks/run_benchmarks.py` (JavaScript removed; runner now requires gcc, Go, Rust); `tests/test_language_benchmarks.py` (JavaScript removed; 24 records, `{c, go, rust}`); `README.md`, `LANGUAGE_BENCHMARKS.md`, `ARCHITECTURE.md`, `DIRECTORY_STRUCTURE.md`, `benchmarks/formats/ASM_BENCHMARK_V1.md` (updated for three languages and dated 2026-11-06 notes; historical JavaScript records remain stored and charted). Deleted: `tests/test_ui.mjs`, `benchmarks/javascript/main.mjs`.

  Additional correctness fix found during verification: `benchmarks/c/main.c` left `Fragment.score` uninitialized for fixtures that extend the fragment array past the initial capacity of 8 via `realloc` (the 12-fragment `large-multifact` fixture produced garbage retrieval scores). Added `memset` of the extended tail. Upstream `realloc` slots never being written before the memset fix means prior accepted runs passed only because freshly mapped heap memory happened to be zeroed; the correctness gate had masked this on valid frames, and the memset makes the behavior deterministic. No historical accepted records were wrong in output because the runner gates every record on expected-output mismatch.

  Tests executed: `python -m compileall -q app asm benchmarks tests` (pass); `python -m unittest discover -s tests -v` — Ran 53 tests, OK (includes 12 standardized-mode tests, HTTP route tests for the explicit and default modes, and the three-language runner tests). Live end-to-end verification: real Smoke Test against local Ollama (job `07d1e9c8-ce03-43c7-90fb-699a76f2e68c`, answer model `gemma3:latest`, independent evaluator `granite4.2:8b`, 2 categories × budget 2048 × repeat 1) completed in ~51 s with 2 comparisons, 4 strategy runs, 4 responses, 0 run errors. All 4 stored runs carry `benchmark_mode: "smoke"`; exact match passed on both strategies of both cases ("Kappa" / room number not specified); the ASM run compressed the case source 28 → 16 tokens.

  Remaining issues: the four smoke runs record `criterion_evaluation.status: "error"` — `granite4.2:8b` returned JSON that failed the strict per-criterion validation ("invalid result count" / missing pass-fail or rationale). This is pre-existing behavior shared with 1,777 of 2,279 stored live runs since 2026-11-05 (122 complete / 1,777 error, same evaluator model), unrelated to the mode feature and failed live runs are deliberately preserved unmodified. A follow-up should make the criterion evaluator robust to fenced/prose-wrapped JSON returns. Node.js is no longer required by any test.

- [x] ASM-071 (COMPLETE, 2026-11-06): Implement a robust error handling mechanism with detailed logging and automatic alerts for system failures, so issues are promptly identified and addressed. Scope decided with the user: app server end-to-end (HTTP routes, Standard Benchmark background jobs, model-call failures, storage reads/writes, server startup), fully local with automatic alerts visible to the council in the application.

  Implementation: new `app/controller/system_log.py` — an append-only `EventStore` over `data/logs/system_events.jsonl` (one JSON line per event; `event_id`, `timestamp`, `severity` info/warning/error/critical, `component`, `event_type`, `message`, `details`, capped `traceback`, `alert: true` on error/critical). Every event is mirrored to stderr; write failures fall back to stderr and never break the app. Repeated failures of the same component + event type emit one escalation alert (`alert_type: repeat_failures`, severity critical) per 15-minute window at the threshold of 3 failures. `ResultStore.list(on_malformed=...)` now skips malformed JSONL lines for reads without modifying or deleting any data. `server.py` integration: GET/POST handlers catch unexpected exceptions and respond 500 with the recorded `event_id` (instead of dropping the connection); invalid payloads respond 400 with an info event; every results store read tolerates malformed lines and logs a warning; `execute_experiment` records model-call failures (`semantic_compression_failed`, `semantic_validation_failed`, `answer_generation_failed`, `criterion_evaluation_failed`) and storage write failures (`run_storage_failed`, critical); `_run_standard_job` logs per-comparison failures, job start info, completion summary info, and crashes (critical); `serve()` logs bind failures (critical, friendly SystemExit) plus start/stop info events. Interface: a "System health and automatic alerts" panel on the Results page (ids `system-health-panel`, `system-active-alert-count`, `system-error-count`, `system-malformed-count`, `system-alert-list`, `system-event-list`, `refresh-system`) fed by `GET /api/system-events` (health envelope with counts, active alerts within the last hour, recent events with tracebacks stripped). Also refreshed stale IMRAD wording ("three-language operation benchmarks", "C, Go, and Rust") left over from the JavaScript removal.

  Files created: `app/controller/system_log.py`, `tests/test_system_log.py` (27 tests). Files modified: `app/controller/server.py`, `app/controller/storage.py`, `app/interface/index.html`, `app/interface/app.js`, `app/interface/style.css`, `tests/test_http.py`, `tests/test_controller.py`, `tests/test_standard_benchmark.py` (class-level patch so test runs never append events to the real log), `README.md`.

  Tests executed: `python -m compileall -q app asm benchmarks tests` (pass); `python -m unittest discover -s tests` — Ran 80 tests, OK (27 new: event fields/alert flags, traceback capture, stderr mirroring, write-failure fallback, escalation once-per-window threshold 3, per-component/type streak isolation, newest-first/filter reads, malformed-line handling with intact original data, health envelope, 500-with-event handler path, 400-info path, `/api/system-events` route, results route malformed tolerance, comparison-failure logging, job crash critical, job-start event, bind-failure SystemExit, criterion-evaluator error alert, and static UI checks). Live verification on 127.0.0.1:8002 (another process owns port 8000): startup wrote `launcher/server_started` to `data/logs/system_events.jsonl`; invalid POST returned 400 and logged `http/invalid_request`; `/api/system-events` served the envelope with tracebacks stripped; the home page served the System health panel.

  Remaining issues: none for this task. The recurring `granite4.2:8b` criterion-evaluator failures (1,777 of 2,279 stored runs) will now surface automatically as escalation alerts once live; making that evaluator robust to fenced/prose-wrapped JSON remains the recommended follow-up.

## Task Completion Rules

Every completed task must include:

1. Files created or modified.
2. Description of implementation.
3. Tests executed.
4. Actual test results.
5. Remaining issues.

Do not mark tasks COMPLETE without verification.

## Agent Handoff

After completing a task, recommend the next task based on dependencies.

Do not automatically begin unrelated work.

Preserve all previous benchmark results.

## Current implementation notes

- The local Python backend and browser interface are available for testing. Offline ASM preparation and baseline context preparation work without model services.
- ASM-022 has an optional Ollama semantic-compression path; offline operation uses the deterministic keyword index. Provider behavior has passed mocked tests and a live local-model comparison with validated source-address coverage.
- ASM-036 now runs paired baseline/ASM trials under one comparison ID, alternates run order across repeats, records a shared input/settings signature, and reports whether source, question, budget, model, model version, and generation settings match.
- The local Ollama API adapter is implemented and unit-tested with mocked responses. A live `gemma3:latest` paired baseline/ASM check completed; both strategies produced the expected full-sentence answer, and semantic compression passed address-coverage validation. The append-only records are in `data/results/experiments.jsonl`. Exact match and criterion pass-rate judgments are recorded separately.
- Go 1.17 is usable after setting its valid adjacent MSYS2 GOROOT for each build/run process. Rustup stable is selected per process; the Windows GNU target links through the installed MinGW GCC because Visual Studio's linker is absent. All four implementations share `ASM-BENCH-V1`, three fixtures, expected-output validation, and repeated operation/resource measurements.
- The interface, measured-result charts, repeated-comparison summary, run inspector, and JSON/CSV export are implemented and UI-tested. Language charts aggregate total/per-operation runtime, peak memory, and CPU utilization by measurement revision, fixture, and language when process metrics are available.
- Language benchmarks run both ASM retrieval/expansion and a no-ASM prefix-truncation baseline for every implementation and fixture. Results records and charts retain the strategy label; invalid historical baseline records are explicitly excluded and explained.
- The results page builds a human-readable IMRAD summary with an opening findings summary, criterion-by-criterion judgments, and a conclusion. Use Summary PDF (IMRAD), then choose Save as PDF in the browser print dialog.
- Criterion pass rate is the percentage of supplied criteria the selected local judge marked as passed. Exact-match scoring remains separate; model judgments are not presented as gold-standard accuracy.
- The Standard Benchmark panel offers three modes. Smoke Test verifies the pipeline with the two smallest fixed tasks at budget 2048, one selected answer model, and a single pass; its numbers are not statistically meaningful. Single-Pass Test runs the full ten-task workload under all standard budgets with every local answer model once each (preliminary only). Full Standard Benchmark keeps the original methodology with three repetitions per strategy and condition. Every stored run records its producing mode in `benchmark_mode`; records without the field are full-profile runs.
- The standard language comparison covers C, Go, and Rust (JavaScript and its tests were removed 2026-11-06; node is no longer part of any check). Historical JavaScript measurement records are retained and chart as before. `benchmarks/c/main.c` now zeroes the realloc-extended fragment array so scores are deterministic for fixtures larger than the initial capacity.
- Criterion evaluation with `granite4.2:8b` currently errors on most live runs (1,777 of 2,279 stored runs as of 2026-11-06) because the judge returns malformed or incomplete per-criterion JSON. Errors are recorded per run without substituted scores. Evaluating robustness of the criterion parsing is planned follow-up work.
- ASM-069 context-pressure work is blocked at the 12,546-token synthetic source: the paired baseline generated an answer, but the ASM semantic-compression request returned HTTP 500 before answer generation. An earlier many-fragment attempt returned JSON without the required representations array. Pilot records and scope limits are preserved in `docs/CONTEXT_PRESSURE_PILOT_2026-11-05.md`.
- ASM-060–068 validation is complete. Verification reports document automated checks, inference evidence, and known scope limits; the project is ready for user testing.
- ASM-071 adds system-wide failure logging and automatic alerts, fully local: all server failures are appended to `data/logs/system_events.jsonl` and mirrored to the console; error/critical events become interface alerts; the same component/type failing 3+ times inside 15 minutes raises one critical escalation alert per window. The council sees the alert log in the System health panel on the Results page (also served at `GET /api/system-events`). Malformed JSONL data lines are now skipped for reads (recorded as warnings, never modified), unexpected request exceptions answer 500 with the event identifier, and the event log write path itself never breaks the application.
