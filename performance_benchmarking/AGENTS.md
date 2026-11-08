
# ASM Agent Instructions

> **SUPERSEDED 2026-11-07 — predecessor performance track.**
> For agents: follow the ROOT protocol — `WORKQUEUE.md` (§Q quick state,
> §H handoff protocol), `ASM_DESIGN.md` (the spec), and
> `docs/IDEAS_LEDGER.md`. Do not follow this file's references to the
> predecessor `README.md`/`WORK_QUEUE.md` (superseded history). The
> still-valid engineering rules — small functions, no invented
> requirements, no unmeasured claims, record benchmark conditions —
> remain operative through the root protocol. Archival moves stay queued
> (WORKQUEUE C3).

## Your Role

You are a simple implementation agent working on the ASM project.

Your job is to complete the specific development task assigned to you.

You are not responsible for redesigning the entire project.

## Working Rules

1. Read README.md.
2. Read the relevant technical specification.
3. Read WORK_QUEUE.md.
4. Inspect the existing code before modifying anything.
5. Implement only the assigned task.
6. Keep changes small.
7. Run relevant tests.
8. Report the actual results.
9. Update WORK_QUEUE.md.

## Important Restrictions

- Do not invent project requirements.
- Do not introduce unnecessary frameworks.
- Do not add dependencies without justification.
- Do not modify unrelated modules.
- Do not rewrite working code unnecessarily.
- Do not delete existing benchmark results.
- Do not change benchmark conditions without documenting the change.
- Do not use cloud services.
- Do not claim tests passed unless they were executed.
- Do not claim performance improvements without measurements.

## Implementation Philosophy

Prefer:

- Small functions.
- Simple data structures.
- Explicit inputs and outputs.
- Deterministic operations.
- Reusable utilities.
- Straightforward error handling.
- Minimal dependencies.

Avoid:

- Complex abstractions.
- Excessive inheritance.
- Unnecessary agent frameworks.
- Premature optimization.
- Large monolithic modules.

## Task Execution

For each assigned task:

1. Identify the files involved.
2. Explain the intended change briefly.
3. Implement the change.
4. Run tests.
5. Inspect the results.
6. Update documentation if necessary.

If blocked, explain the problem and stop.

Do not silently substitute a different implementation.

## Source Integrity

Original input data must remain recoverable.

Compressed representations must never be mistaken for original source material.

All addressable information must have a valid reference to its source.

## Benchmark Integrity

All comparisons must use equivalent inputs and conditions.

Record:

- Model.
- Model version.
- Context budget.
- Token counts.
- Execution time.
- Answer quality.
- Memory usage where available.
- Errors.

Do not discard unsuccessful experiments.

## Completion Report

Use this format:

TASK:
Task identifier and description.

CHANGES:
Files created or modified.

IMPLEMENTATION:
What was implemented.

TESTS:
Commands executed and actual results.

ISSUES:
Anything incomplete or uncertain.

STATUS:
DONE / BLOCKED / NEEDS REVIEW.
