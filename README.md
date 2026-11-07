# Addressable Semantic Memory (ASM) — Multi-Language Benchmark

This repository contains equivalent simple deterministic ASM implementations in:

- Python (`asm.py`, embedded in the runner)
- C (`asm_c.c` + `asm_c.h`, entry point `asm_c_main.c`)
- Rust (`asm.rs`, entry point `asm_main.rs`)
- Go (`asm.go`, entry point `asm_main.go`)

Design context: `ASM_DESIGN.md` (spec for the full progressive-abstraction
memory system this benchmark's core represents). Continuation protocol and
current work queue: `WORKQUEUE.md`. A real-document retrieval challenge
(NOAA Technical Report NESDIS 142-9 + its Figure 5, transcribed with
oracle-validated math) lives in `challenge-documents/`.

Each language uses an `ASM` abstraction:

- Python: `class ASM`
- C: `struct ASM`
- Rust: `struct ASM`
- Go: `type ASM struct`

## Run

From the directory:

```text
python benchmark.py --build
python benchmark.py
```

The runner:

1. Builds C, Rust, and Go when toolchains are available; build failures are attached
   to that implementation's result instead of silently skipping it.
2. Runs each implementation against the same conceptual sample.
3. Every implementation prints the same JSON document on stdout and reports its own
   `BENCHMARK_NS` on stderr.
4. Checks whether the returned algorithm results match (parsed as JSON, so key order
   or escaping differences do not matter).

All four outputs contain: `original_source_words`, `question_words`,
`retrieved_addresses`, `selected`, `context` (the assembled text), and `context_words`.

## Important benchmark notes

`internal_ns` is measured with the same scope in every implementation: the algorithm
plus JSON serialization, with no output I/O. This is the number to compare across
languages.

The Python implementation runs in-process while C/Rust/Go are launched as separate
processes, so `process_ns` still includes each runtime's startup cost and is NOT a
fair algorithm-speed comparison.

Two caveats for tiny inputs like this sample:

- Go on Windows can report `internal_ns` of 0 because its coarse clock cannot resolve
  sub-microsecond intervals.
- All measured work here (49 words over 6 fragments) is far below a useful signal
  level; the numbers mostly measure map/hash setup and allocation.

## Requirements

- Python 3
- C: any C11 compiler (the timer uses `QueryPerformanceCounter` on Windows and
  `CLOCK_MONOTONIC` elsewhere)
- Rust: rustc; on Windows the MSVC host needs Visual Studio Build Tools (C++
  workload). Without the MSVC linker the runner falls back to the installed
  `x86_64-pc-windows-gnu` target.
- Go: `go` on PATH or in `$GOROOT/bin`; GOROOT must match the go binary version.

For serious benchmarking, the next step should be:

- warm-up runs
- many iterations
- median/min/max statistics
- identical fixture loaded from one shared input file
- separate measurement of retrieval, ranking, lookup, and context assembly
- optional CPU affinity/process priority controls
"# addressable_semantic_memory" 
