# addressable_semantic_memory — benchmarking workspace

Consolidation of two ASM benchmark projects into one repository:
`accuracy_benchmarking/` (active) + `performance_benchmarking/`
(predecessor, absorbed 2026-11-07). One central command-line utility runs
everything; every printed number answers the central question:

> **Can ASM preserve or improve task performance while requiring
> substantially less context, memory, compute, or retrieval?**

This is the **initial edition** of the root README (2026-11-07); the
consolidation item C3 will refine it after the two tracks are reconciled.

## Agent instructions (read first, on EVERY session)

1. **Adopt the registered tools as soon as you are available for
   development.** Do the same the moment you take on a development task
   inside this repo: open `docs/tools_registry.json` — the machine-
   readable tool registry — and use its listed invocations (`python
   bench.py ...`, per-suite commands) instead of hand-rolling or
   rediscovering commands.
2. **Register any new command you create in the same commit** (rule
   §R20 in `WORKQUEUE.md`): extend the table in `bench.py`'s
   `TOOL_REGISTRY` and refresh `docs/tools_registry.json` with
   `python bench.py registry`.
3. **Verify before pushing**: run `python bench.py all` from the repo
   root (full gate: 4/4 cross-language parity + metric tables +
   full-context baseline), then follow `WORKQUEUE.md` §V from
   `accuracy_benchmarking/` for the piece-level checks.
4. Work the queue: read `WORKQUEUE.md` §Q, then the first
   `status: todo` item. Continuation protocol: `WORKQUEUE.md` §H.

## Run (humans and machines)

From the repo root:

```text
python bench.py all          # registry + performance + accuracy
python bench.py performance  # cross-language parity + internal/process timing
python bench.py accuracy     # budget sweep + adequacy + full-serve baseline
python bench.py registry     # print + write docs/tools_registry.json
```

Human-readable tables print to the console; deterministic artifacts
(prompts, adequacy reports, criteria checklist) land in
`accuracy_benchmarking/results/`.

## What the output measures

Named metrics defined once in `WORKQUEUE.md` §R19: Quality Retention
(ASM score / full-context score), active-context Compression (vs the
storage footprint, reported separately), Retrieval Recall / Precision /
Expansion Efficiency, Accuracy per 1000 words, latency splits
(internal ns vs process wall), and SAE (Semantic Access Efficiency,
full-context baseline = 1.00). Context budgets are ranges of small
windows counted in whitespace-delimited WORDS (`[A-Za-z0-9]+` runs),
never tokens — rule §R4. `bench.py --help` shows the CLI surface.

## Where things live

- `accuracy_benchmarking/` — active track: four equivalent deterministic
  ASM implementations (Python/C/Rust/Go), challenge harness, NOAA
  challenge + oracle, generated fixtures, committed `results/`
  artifacts. Its own README has the piece-level detail.
- `performance_benchmarking/` — predecessor track as plain files; entry
  docs carry SUPERSEDED/RETIRED banners. Prior art of record; full
  history recoverable via
  `git clone performance_benchmarking/previous-history.bundle`.
- `deploy-package/` — reserved release-staging dir (empty today).
- `ASM_DESIGN.md` — the one specification. `WORKQUEUE.md` — the one
  continuation protocol + locked rules (§R). `docs/IDEAS_LEDGER.md` —
  consolidation inventory; `docs/tools_registry.json` — agent registry.
- Product directives: **CLI-only** (no browser interfaces);
  **lean** package; **fast** default runs (minutes); small-window
  performance focus per `WORKQUEUE.md` §R15-18.
