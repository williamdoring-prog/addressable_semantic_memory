# addressable_semantic_memory — benchmarking workspace

## Benchmark Results at a Glance — ASM vs Non-ASM Effects
  - benchmarks run against GDP.pdf long context "Hurricane Share of Disaster Costs" challenge: https://artificialanalysis.ai/evaluations/gdp-pdf

**Control (no-ASM) runs verbatim the first context words without retrieval or selection. ASM runs select and retrieve addresses within the context budget. Both tracked across 5 context budgets (150, 300, 600, 1200, 2400 words).**

### Quality Retention (C2 zero-years criterion)
*How many of 18 target years (1980–2010) correctly identified as hurricane-zero years? Higher = ASM preserves more task performance with less context.*

| Budget | Context Words | ASM Selected | C2 Passing / 18 | Trend |
|--------|--------------|-------------|-----------------|-------|
| 150    | 147 (control) | 3           | 2/18            | baseline |
| 300    | 299 (control) | 7           | 4/18            | +2 vs 150 |
| 600    | 600 (control) | 12          | 5/18            | +1 vs 300 |
| 1200   | 1199 (control) | 19          | 8/18            | +3 vs 600 |
| 2400   | 2399 (control) | 38          | 9/18            | +1 vs 1200 |

**Effect**: More selected addresses and more context words gradually improve zero-year retention, but diminishing returns after 1200 words. Even at 2400 words (near-full context), ASM reaches only 9/18 vs full-context baseline of 18/18.

### Retrieval Efficiency
*Fewer addresses selected while retaining comparable quality retention indicates better compression.*

| Budget | Addresses Selected | Context Words per Address |
|--------|-------------------|---------------------------|
| 150    | 3                 | 49 words/address |
| 300    | 7                 | 43 words/address |
| 600    | 12                | 50 words/address |
| 1200   | 19                | 63 words/address |
| 2400   | 38                | 63 words/address |

**Effect**: Selecting more addresses does not linearly improve quality retention — e.g., 38 addresses at B2400 yields only 9/18 C2 passing, vs 3 addresses at B150 yielding 2/18.

### Language Parity
*All four implementations (Python/C/Rust/Go) report `all_match: true` at every budget — cross-language results are equivalent.*

### Key Comparative Effect
- **B150/300**: Minimal C2 passing (2–4/18) — ASM with very limited context struggles to identify zero-hurricane years
- **B600**: Moderate improvement (5/18) — more context allows meaningful gains
- **B1200**: Significant improvement (8/18) — doubling budget from 600 yields substantial quality retention increase
- **B2400**: Near-saturation (9/18) — further context yields marginal gains; C3/C4 adequacy criteria still fail

**Full-context baseline**: 18/18 C2 passing with 28177 source words. ASM at B2400 uses 2399 context words (≈8.5% of full context) and achieves 9/18 — roughly half the baseline performance with ~1/12 the context.

## ASM Operational Summary (continued)

**Purpose**: Can ASM preserve or improve task performance while requiring substantially less context, memory, compute, or retrieval?

**Evidence Basis**: All claims derive from committed benchmark results in `accuracy_benchmarking/results/` and `performance_benchmarking/data/results/`.

**Metric Framework** (defined in `WORKQUEUE.md` §R19):
- **Quality Retention**: ASM score / full-context score, measured by the C2 zero-years criterion across 18 target years (1980-2010). Full-context baseline = 1.00.
- **Active-context Compression**: Measured as the ratio of context words used versus the full source corpus size, reported per-budget. Context budgets are ranges of small windows counted in whitespace-delimited WORDS (rule §R4), never tokens.
- **Retrieval Recall / Precision / Expansion Efficiency**: Measured by the number of addresses selected versus retrieved per budget.
- **Accuracy per 1000 words**: Budget-sweep and adequacy results from the challenge harness.
- **Latency splits**: Internal nanosecond timings versus process wall time, reported per-implementation and per-budget.
- **SAE (Semantic Access Efficiency)**: Full-context baseline = 1.00; ASM implementations report SAE relative to this baseline.

**Implementation Tracks**:
- `accuracy_benchmarking/` — active track: four equivalent deterministic ASM implementations (Python/C/Rust/Go), challenge harness, NOAA challenge + oracle, generated fixtures, committed `results/` artifacts. Its own README has the piece-level detail.
- `performance_benchmarking/` — predecessor track as plain files; entry docs carry SUPERSEDED/RETIRED banners. Prior art of record; full history recoverable via `git clone performance_benchmarking/previous-history.bundle`.

**Product Directives**: CLI-only (no browser interfaces); lean package; fast default runs (minutes); small-window performance focus per `WORKQUEUE.md` §R15-18.

## Agent instructions (read first, on EVERY session)

1. **Adopt the registered tools as soon as you are available for development.** Do the same the moment you take on a development task inside this repo: open `docs/tools_registry.json` — the machine-readable tool registry — and use its listed invocations (`python bench.py ...`, per-suite commands) instead of hand-rolling or rediscovering commands.
2. **Register any new command you create in the same commit** (rule §R20 in `WORKQUEUE.md`): extend the table in `bench.py`'s `TOOL_REGISTRY` and refresh `docs/tools_registry.json` with `python bench.py registry`.
3. **Verify before pushing**: run `python bench.py all` from the repo root (full gate: 4/4 cross-language parity + metric tables + full-context baseline), then follow `WORKQUEUE.md` §V from `accuracy_benchmarking/` for the piece-level checks.
4. Work the queue: read `WORKQUEUE.md` §Q, then the first `status: todo` item. Continuation protocol: `WORKQUEUE.md` §H.

## Run (humans and machines)

From the repo root:

```text
python bench.py all          # registry + performance + tool suite + accuracy
python bench.py performance  # cross-language parity + internal/process timing
python bench.py tools        # LLM tool-interface suite (json/xml/yaml/toml/csv/plain)
python bench.py accuracy     # budget sweep + adequacy + full-serve baseline
python bench.py registry     # print + write docs/tools_registry.json
```

LLM tool interface (`accuracy_benchmarking/asm_tool.py`, ASM_DESIGN §6): structured tool requests reach ASM the way function calling works — in JSON, XML, a documented YAML subset, TOML (tomllib, Python 3.11+), CSV (one flat header+data row), or plain text; ops `serve` (budgeted context assembly), `list` (stable addresses), `inspect` (exact-ID resolve); responses echo the sniffed request format (`--format` overrides the response only; csv responses are address/error rows, others default to json), and `expand` is reported as `unsupported_op` until the abstraction ladder exists. `--schema openai|anthropic|jsonschema` prints the function-calling tool definition a harness binds. Examples:

```text
python accuracy_benchmarking/asm_tool.py --input accuracy_benchmarking/asm_input.txt --op serve `
    --budget 600 --question "Which state had the most ice?" --format json
python accuracy_benchmarking/asm_tool.py --schema openai     # tool definition
```

Human-readable tables print to the console; deterministic artifacts (prompts, adequacy reports, criteria checklist) land in `accuracy_benchmarking/results/`.

## What the output measures

Named metrics defined once in `WORKQUEUE.md` §R19: Quality Retention (ASM score / full-context score), active-context Compression (vs the storage footprint, reported separately), Retrieval Recall / Precision / Expansion Efficiency, Accuracy per 1000 words, latency splits (internal ns vs process wall), and SAE (Semantic Access Efficiency, full-context baseline = 1.00). Context budgets are ranges of small windows counted in whitespace-delimited WORDS (`[A-Za-z0-9]+` runs), never tokens — rule §R4. `bench.py --help` shows the CLI surface.

## Where things live

- `accuracy_benchmarking/` — active track: four equivalent deterministic ASM implementations (Python/C/Rust/Go), challenge harness, NOAA challenge + oracle, generated fixtures, committed `results/` artifacts. Its own README has the piece-level detail.
- `performance_benchmarking/` — predecessor track as plain files; entry docs carry SUPERSEDED/RETIRED banners. Prior art of record; full history recoverable via `git clone performance_benchmarking/previous-history.bundle`.
- `deploy-package/` — reserved release-staging dir (empty today).
- `ASM_DESIGN.md` — the one specification. `WORKQUEUE.md` — the one continuation protocol + locked rules (§R). `docs/IDEAS_LEDGER.md` — consolidation inventory; `docs/tools_registry.json` — agent registry.
- Product directives: **CLI-only** (no browser interfaces); **lean** package; **fast** default runs (minutes); small-window performance focus per `WORKQUEUE.md` §R15-18.