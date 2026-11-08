# IDEAS LEDGER — consolidation inventory

Seeded 2026-11-07 during the consolidation of the accuracy and performance
benchmark tracks. Governance: WORKQUEUE.md §R9-R14 (archive before delete;
every action logged here; ideas are conserved even when documents move).

## Product directives locked 2026-11-07

- CLI-only: no browser control interfaces; configuration via terminal
  args/flags only.
- Lean package; benchmark runs complete within a few minutes.
- Benchmark focus: performance across a range of small context windows;
  purpose = maximize utility of context space (reduce token + inference
  loads).

## Idea list (conserved; provenance + where it lives now)

- ASM-D1 Progressive-abstraction ladder + measured expansion costs
  (root ASM_DESIGN.md 1-6) — KEEP (authoritative spec).
- ASM-D2 Four-language deterministic parity as the correctness instrument
  (accuracy_benchmarking/benchmark.py + asm_main.*) — KEEP.
- ASM-D3 Challenge-driven retrieval-adequacy scoring with prompt files +
  criteria checklist; no LLM in the harness (challenge.py,
  check_challenge.py, results/prompt_budget_*.txt,
  results/criteria_checklist.md) — KEEP (the local-model test interface).
- ASM-D4 Budget sweep = range of small context windows counted in WORDS
  (challenge.py --budgets; adequacy table results/challenge_adequacy.md)
  — KEEP. Key finding: C2 grows 2/18 -> 9/18 with budget; C4 = 0/13 at all
  budgets (flat term-overlap never selects structured units) — motivates
  the candidate-listing layer amendments (C3).
- ASM-D5 Utility of context space measured as criteria-facts served per
  context word (adequacy tables per budget) — KEEP as the headline metric;
  documented in the consolidated runbook (C4).
- ASM-D6 Context-pressure pilot using progressively larger served contexts
  (performance_benchmarking/docs/CONTEXT_PRESSURE_PILOT_2026-11-05.md +
  benchmarks/run_context_pressure.py) — KEEP idea; same phenomenon as the
  budget sweep seen from the performance side; doc/action reconciliation
  in C1/C4.
- ASM-D7 Criterion-based evaluation scoring approach
  (performance_benchmarking/docs/CRITERION_EVALUATION_FINDINGS...M14) —
  KEEP idea; classify fully when read (C1).
- ASM-D8 `.asmbench` fixture format + fixtures with expected outputs
  (performance_benchmarking/benchmarks/formats/ASM_BENCHMARK_V1.md,
  benchmarks/fixtures/) — candidate idea: standardized cross-project
  benchmark input format; read/decide in C1.
- ASM-D9 Language-performance measurement trio with per-language timers
  (performance_benchmarking/benchmarks/{c,go,rust}, run_benchmarks.py,
  standard_suite.py) — KEEP idea (CLI, fits the directives); classify
  fully in C1.

## Action list

- performance_benchmarking/app/ — PRUNE 2026-11-07. Reason: user directive
  retires browser control interfaces outright ("no more browser control
  interfaces"). Nothing is lost: the exact tree exists in
  performance_benchmarking/previous-history.bundle (git clone recovers
  it), so conservation = bundle ref, not the working tree. Companion doc
  performance_benchmarking/WEB_INTERFACE.md gets an archive status header
  in C3.
- 81 transcription scratch crops in accuracy_benchmarking/challenge-documents/
  — UNTRACK (keep on disk; regenerable from the source page render) —
  queued C5 step 1; they were accidentally tracked by the restructure commit.
- Root __pycache__/ + built binaries (asm_c.exe/asm_rust.exe/asm_go.exe)
  — PRUNE (regenerable via benchmark.py --build) — queued C5 step 2.

## Flags

- Unclassified: the full predecessor docs/ + benchmarks/ + tests/ trees —
  C1 continues classification there (read-before-label rule; ASM-D7/D8/D9
  cover the headline items only).
- unresolved: whether standard_suite.py and the challenge harness can share
  fixture plumbing cheaply (ASM-D8 story) — read in C1, document in C4.
