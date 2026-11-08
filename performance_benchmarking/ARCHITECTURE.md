
# ASM System Architecture

## Overview

ASM consists of four independent components.

1. Browser interface.
2. Experiment controller.
3. ASM processing engine.
4. Benchmark implementations.

## Browser Interface

Responsibilities:
- Accept user text.
- Accept benchmark questions.
- Select context budgets.
- Select benchmark configurations.
- Start experiments.
- Display results.

The browser must not implement benchmark logic.

## Experiment Controller

Responsibilities:
- Prepare benchmark inputs.
- Select ASM-enabled or baseline execution.
- Apply context budgets.
- Invoke the local model.
- Record measurements.
- Save results.

The controller must use the same model configuration for equivalent comparisons.

## ASM Engine

Responsibilities:
- Process source material.
- Create semantic representations.
- Assign addresses.
- Resolve addresses.
- Retrieve source information.
- Reconstruct relevant context.
- Report compression and retrieval statistics.

The engine must be independently testable without an LLM.

## Language Benchmarks

Each language implementation must perform equivalent operations.

The implementations must share:
- Input fixtures.
- Data formats.
- Operation definitions.
- Expected outputs.
- Benchmark conditions.

Note (2026-11-06): the standard language comparison covers C, Go, and Rust; the JavaScript implementation and its tests were removed.

## Data Flow

1. User submits text and a question.
2. Controller prepares the source material.
3. Baseline execution processes the original material.
4. ASM execution processes the compressed representation.
5. Both paths execute equivalent tasks.
6. Results are evaluated.
7. Measurements are stored.
8. Dashboard displays comparisons.

## Storage

Keep these separate:

- Original source material.
- ASM representations.
- Benchmark configurations.
- Raw model responses.
- Benchmark measurements.
- Aggregated reports.

Never overwrite original source material or historical benchmark results.

## Design Constraints

- Local-first.
- Minimal dependencies.
- No distributed architecture.
- No unnecessary databases or services.
- No mandatory cloud inference.
- No coupling between ASM and one programming language.
- No coupling between ASM and one LLM.
