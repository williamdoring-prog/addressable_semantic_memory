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
- One central CLI (`python bench.py`, repo root) runs the performance
  and/or accuracy benchmarks; output must be clear and human-readable
  and must answer: "Can ASM preserve or improve task performance while
  requiring substantially less context, memory, compute, or retrieval?"
- An agent-accessible tool registry (machine-readable JSON + human
  table) so agents discover commands without exploring the repo.

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
  — KEEP. Key finding: C2 grows 2/18 -> 9/18 with budget; C4 = 0/13 at
  all SMALL budgets. Correction 2026-11-07: an earlier "C4 = 0/13 at
  all budgets" claim was an artefact of the adequacy checker comparing
  string oracle years to int unit years (fixed in check_challenge.py;
  full serve passes C4 13/13); the real finding is that flat
  term-overlap ranking retrieves prose chunks only at small budgets —
  motivates the candidate-listing layer amendments (C3).
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
- ASM-D10 Named metric framework with full-context baseline and a
  signature ASM metric (user directive 2026-11-07): Quality Retention =
  ASM score / full-context score; Compression split into STORAGE
  (persisted memory) vs ACTIVE context reduction; Retrieval
  Recall / Precision / Expansion Efficiency; Accuracy per Token
  (facts per 1000 words; headline plot Task Quality vs Context Words);
  latency split retrieval/selection vs startup+IO; and SAE (Semantic
  Access Efficiency) = Quality Retention / active-context fraction,
  baseline 1.0. Lives in: bench.py (tables 1-3 + ANSWER SUMMARY),
  defined as WORKQUEUE §R19. Current measured shape (2026-11-07):
  retention 7% @ 150 -> 31% @ 2400 words; SAE best 13.07 @ 150;
  full-serve baseline 29/31 oracle facts. — KEEP (authoritative).
- ASM-D11 Agent-accessible tool registry: machine-readable
  docs/tools_registry.json (tool_id / invocation / workdir / outputs /
  wall) plus a human-readable table; new CLI tools must add registry
  entries in the same commit (WORKQUEUE §R20). Lives in bench.py
  TOOL_REGISTRY; regenerated via `python bench.py registry`. — KEEP.

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
- bench.py + docs/tools_registry.json — ADDED 2026-11-07 (central CLI
  per third directive; registry artifact regenerated by
  `python bench.py registry`; both KEEP).
- accuracy_benchmarking/check_challenge.py — AMENDED 2026-11-07: fixed
  string-vs-int year comparisons in check_budget (C2 hurricanes flag +
  C4 has_hurricane). No file moved; adequacy outputs regenerated in
  place (results/challenge_adequacy.*).
- ASM_DESIGN.md — AMENDED 2026-11-07 (doc-consistency pass): repository
  layout now lists bench.py + docs/; the accuracy-track paragraph names
  the central CLI; the predecessor-track reconciliation pointer was
  corrected from the nonexistent "W9" to the consolidation queue
  (C1..C6); §12 gained the operative metric-framework pointer (WORKQUEUE
  §R19) and the words-never-tokens harness rule.
- accuracy_benchmarking/README.md — AMENDED 2026-11-07: the Run section
  now leads with the central CLI (python bench.py) and keeps the
  piece-level commands as diagnosis; full-serve baseline 29/31 recorded
  (checker fix of record); stray trailing "# addressable_semantic_memory"
  artifact line removed; the serious-benchmarking list is tied to the
  §R17/W8 opt-in rule.
- performance_benchmarking/README.md + AGENTS.md + WEB_INTERFACE.md —
  STAMPED 2026-11-07 with SUPERSEDED/RETIRED banners routing agents to
  the root protocol (early action ahead of C3's full archive; banners
  only — no moves, no deletions; AGENTS.md's still-valid engineering
  rules continue through the root protocol).

## Flags

- Correction of record (2026-11-07): adequacy outputs and any line that
  claims "C4 = 0/13 at every budget including full serve" written before
  today's check_challenge.py fix are superseded — full serve passes
  29/31 (C4 13/13; C2 16/18 — the years 1984/1987 are mentioned nowhere
  in the source). Small-budget C4 = 0/13 stands as the real retrieval
  gap.
- Naive-summary and RAG comparison arms do not exist yet (§R19 target
  table; queued W8) — do not over-claim "beats RAG" before they run.
- Unclassified: the full predecessor docs/ + benchmarks/ + tests/ trees —
  C1 continues classification there (read-before-label rule; ASM-D7/D8/D9
  cover the headline items only).
- unresolved: whether standard_suite.py and the challenge harness can share
  fixture plumbing cheaply (ASM-D8 story) — read in C1, document in C4.
