
# ASM Browser Interface

> **RETIRED 2026-11-07 by user directive (CLI-only — no browser control
> interfaces).** The `app/` implementation was pruned; the exact tree is
> preserved in `previous-history.bundle` (recover via `git clone`). All
> configuration and control is terminal-based; the central CLI is the
> repo-root `python bench.py` (see `docs/tools_registry.json`). Full
> archival of this file stays queued (WORKQUEUE C3).

## General

Create a lightweight browser-based interface for local ASM experimentation.

The application should have two primary pages:

1. Benchmark
2. Results

Avoid unnecessary navigation and configuration complexity.

## Page 1 — Benchmark

### Input

Provide a large text input area.

The user should be able to enter:
- Source material.
- A question or instruction.

Support loading source documents later.

### Configuration

Allow selection of:

- ASM enabled / disabled.
- Context budget.
- Local model.
- Repeat count.
- Benchmark category.

Provide sensible defaults.

### Execution

Display:
- Current experiment.
- Current strategy.
- Current context budget.
- Progress.
- Errors.
- Completion status.

Allow the user to inspect the completed run.

## Page 2 — Results

Create a comprehensive reporting dashboard.

### Summary

Display:
- Experiment ID.
- Date.
- Model.
- Context budget.
- ASM status.
- Execution time.
- Token consumption.
- Answer quality.
- Normalized exact-match score and model-judged criterion pass percentage as separate measures.
- Resource consumption.

### Required Charts

1. Token consumption: ASM vs baseline.
2. Answer quality: ASM vs baseline.
3. Execution time: ASM vs baseline.
4. Compression ratio.
5. Retrieval and expansion overhead.
6. Total processing time.
7. Quality versus token consumption.
8. Programming language comparison.
9. Memory consumption by language.
10. Performance by context budget.
11. Criterion pass percentage by strategy, with per-criterion results available in run inspection.

### Detailed Results

Allow inspection of:
- Original input.
- Compressed representation.
- Address references.
- Retrieved fragments.
- Reconstructed context.
- Final prompt.
- Model response.
- Evaluation results.
- Supplied evaluation criteria, each pass/fail judgment and rationale, evaluator model/version, and evaluation status.

### Data Export

Support:
- JSON.
- CSV.
- A print-ready IMRAD summary (Introduction, Methods, Results, Discussion) that can be saved as PDF from the browser print dialog.
- Separate ASM and no-ASM series in language benchmark charts.
- Separate normalized exact-match and criterion pass-rate scores. Criterion scores retain each supplied criterion's decision, rationale, evaluator model, and evaluation status.

## Visual Design

Use a clean technical dashboard.

Prioritize:
- Readability.
- Clear comparisons.
- Consistent units.
- Useful graphs.
- Detailed measurements.

Avoid decorative visualizations.

## Important

Every graph must be generated from actual stored benchmark results.

Do not substitute example data for real results without clearly labelling it as demonstration data.
