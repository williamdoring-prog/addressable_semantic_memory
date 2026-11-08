
# ASM — Addressable Semantic Memory

## Project Purpose

Build a local experimental platform to investigate Addressable Semantic Memory (ASM), a proposed approach to reducing LLM context requirements through semantic compression and addressable information retrieval.

The project must establish experimentally whether ASM can:

1. Reduce the amount of information passed to an LLM.
2. Preserve important information from the original source.
3. Reconstruct relevant details through address-based retrieval.
4. Maintain answer quality when operating under small context windows.
5. Improve efficiency without introducing unacceptable retrieval or reconstruction overhead.

Do not assume ASM works. The purpose of this project is to test the hypothesis.

## Primary Objectives

### Objective 1 — ASM Engine
Implement a small, independently testable ASM engine.

### Objective 2 — Benchmark Platform
Build a browser interface that accepts user input and runs controlled experiments with ASM enabled and disabled.

### Objective 3 — Context Window Experiments
Test multiple context budgets:

- 512 tokens
- 1,024 tokens
- 2,048 tokens
- 4,096 tokens
- 8,192 tokens
- 16,384 tokens

Allow additional budgets to be configured.

### Objective 4 — Language Comparison
Benchmark equivalent ASM operations implemented in:

- JavaScript
- C
- Go
- Rust

### Objective 5 — Results Dashboard
Produce a comprehensive results page with graphs, comparisons, raw measurements, and experiment details.

## Core Requirements

- Entirely local operation.
- No mandatory cloud services.
- No paid APIs.
- Reproducible benchmarks.
- Preserve original source data.
- Record actual token consumption.
- Separate model performance from implementation performance.
- Never fabricate or estimate benchmark results when measurements are available.
- Keep the implementation simple.

## Technology Approach

Use a lightweight local web application.

Python may coordinate experiments and serve the interface.

JavaScript, C, Go, and Rust must implement comparable low-level benchmark operations.

Use a local LLM interface, initially supporting Ollama.

Keep the ASM implementation independent of the selected model.

## Local Prototype

The initial application uses only the Python standard library and browser-native HTML, CSS, and JavaScript.

Start the local server from the repository root:

```powershell
python -m app.controller.server
```

Open `http://127.0.0.1:8000/` in a browser. Offline preparation works without Ollama. To run model inference, start Ollama locally, install a model, select it in the interface, and enable local inference.

The Standard Benchmark panel offers three execution modes. **Smoke Test** verifies the pipeline quickly with the two smallest fixed tasks at the 2,048-token budget, one selected answer model, and a single pass (its results are not statistically meaningful). **Single-Pass Test** runs the normal ten-task workload at every standard budget with all answer models exactly once (preliminary only). **Full Standard Benchmark** keeps the unchanged methodology with three repetitions per strategy and condition. Every stored run records which mode produced it in `benchmark_mode`; earlier records without the field were full-profile runs.

The results page includes **Summary PDF (IMRAD)**. It opens a print-ready report; choose **Save as PDF** in the browser print dialog.

For answer-quality evaluation, enter one criterion per line. With local inference enabled, the app sends the generated answer, original source, question, and criteria through a second local-model inference pass. The answer model is used by default; a separate installed evaluator model can be selected. Each criterion stores a pass/fail decision and rationale, and the displayed percentage is the proportion of criteria passed. This model-judged percentage is separate from normalized exact match. Total run time includes the judge pass, which is also timed separately.

The benchmark form defaults to paired ASM/baseline comparisons and three repetitions. Each strategy run is saved separately under one comparison ID.

Run the automated checks with:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q asm app benchmarks tests
python -m unittest discover -s tests -p test_language_benchmarks.py -v
```

Experiment records are appended to `data/results/experiments.jsonl`; prior runs are not overwritten. Tests use temporary storage.

Run the local C/Go/Rust correctness-gated benchmark with:

```powershell
python benchmarks/run_benchmarks.py --iterations 5 --warmups 2 --output data/results/language_benchmarks.jsonl
```

This appends correctness-gated per-run ASM and no-ASM baseline measurements, including per-operation timings. On Windows, process peak working set and CPU utilization are collected when the OS accounting resolution supports them. See the root [language benchmark requirements](LANGUAGE_BENCHMARKS.md) and the shared [benchmark input/output format](benchmarks/formats/ASM_BENCHMARK_V1.md). The runner covers C, Go, and Rust. The JavaScript implementation and all JavaScript testing (the node UI checks and `tests/test_ui.mjs`) were removed from the standard comparison on 2026-11-06; earlier JavaScript measurement records remain stored and charted in the results page. On this Windows setup it discovers the MSYS2 Go installation and sets its adjacent GOROOT, and it selects the installed Rustup toolchain for each benchmark process. It uses Rust's Windows GNU target when Visual Studio's linker is unavailable and MinGW GCC is installed.

### Prototype measurement notes

- Offline ASM uses a deterministic keyword index. With local Ollama enabled, it also supports model-generated semantic representations whose source-address coverage is validated before use. Generated representations remain derived material; source fragments are retained and can be expanded verbatim.
- The built-in tokenizer counts Unicode word and punctuation tokens with the documented `ASM word/punctuation tokenizer v1`. It is useful for consistent local comparisons, but differs from model tokenizers. When Ollama is used, its actual prompt and generation token counts are stored separately.
- Answer scoring is a normalized exact match against an optional expected answer. It is not a general answer-quality evaluator.
- Optional criterion scoring runs a separate local evaluator inference and records per-criterion judgments, rationales, evaluator model/version, token counts, and measured time. Its percentage is a model judgment, not a gold-standard quality score.
- For ASM/LLM experiment records, CPU and memory measurements remain unavailable rather than estimated. The language benchmark runner records process peak working set and CPU utilization on Windows; platforms without supported process metrics store `null`.
- The UI only graphs measured stored results. It does not populate charts with sample values.

### System logging and automatic alerts

The app server end-to-end feeds one local system event log: HTTP request handling and server startup, Standard Benchmark background jobs, model-call failures (semantic compression, answer generation, criterion evaluation), and storage reads/writes. Events are appended to `data/logs/system_events.jsonl`, one JSON line per event, with `event_id`, `timestamp`, `severity` (`info`/`warning`/`error`/`critical`), `component`, `event_type`, `message`, optional `details` and `traceback`, and an `alert` flag that is set on every `error` or `critical` event. Every event is also mirrored to the console (stderr).

Automatic alert behavior:

- Every `error` or `critical` event is an automatic alert in the interface.
- When the same `component` + `event_type` fails repeatedly, one escalation alert (`alert_type: repeat_failures`, severity `critical`) is emitted per fixed window — currently 3 failures inside 15 minutes (for example, the recurring granite4.2:8b criterion-evaluator failures surface this way).
- Unexpected request exceptions return HTTP 500 with the recorded `event_id` instead of dropping the connection; invalid request payloads return HTTP 400 and an `info` event without raising an alert.
- Malformed JSONL lines in a results store are counted and skipped for reads (they are never modified or deleted) and produce a warning event, so one bad line no longer breaks a listing endpoint.
- The logging mechanism never breaks the application: if the event file cannot be written, events fall back to the console only.

The council reads the alert log in the application: open **Results** and use the **System health and automatic alerts** panel (data served by `GET /api/system-events`, active alerts within the last hour, full recent event list, and a short link back to the underlying failures).

## Agent Instructions

Read AGENTS.md before doing any work.

Follow PROJECT_PLAN.md and WORK_QUEUE.md.

Complete one task at a time.

Do not redesign the project without approval.
