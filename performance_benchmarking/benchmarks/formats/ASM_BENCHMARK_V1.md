# ASM Benchmark Input/Output Format v1

This contract is shared by the C, Go, and Rust operation benchmarks. It is linked from the root [language benchmark requirements](../../LANGUAGE_BENCHMARKS.md). The JavaScript implementation was removed from the standard comparison in 2026-11-06; historical JavaScript records remain stored. These programs benchmark deterministic parsing, filtering, address lookup, retrieval, expansion, context assembly, and serialization. They do not measure semantic compression or LLM quality. Every fixture runs under both `asm` and `baseline` strategies; the runner passes the strategy after the fixture path. Omitted strategy defaults to `asm` for direct invocations.

## Input

UTF-8, one record per line, with literal tab characters separating fields:

```text
ASM-BENCH-V1
id<TAB>fixture identifier
budget<TAB>positive evidence-context token budget
question<TAB>query text
lookup<TAB>address to resolve                 # zero or more
fragment<TAB>stable address<TAB>original text # one or more
```

Text fields escape backslash as `\\`, tab as `\t`, newline as `\n`, and carriage return as `\r`. Records may appear in any order after the header. Addresses must be unique. Invalid headers, records, budgets, duplicate addresses, and unknown record types are errors.

## Shared token and retrieval rules

- A token is a maximal ASCII `[A-Za-z0-9]+` sequence.
- Matching is case-insensitive. No stemming or language-specific normalization is applied.
- Each fragment's score is the number of distinct question tokens present in that fragment.
- Return only fragments with a score greater than zero, ordered by score descending and then address ascending by bytewise/ordinal comparison.
- Expand retrieved fragments in that order, retaining a fragment only when its word-token count fits the remaining context budget. Continue checking later fragments after a skip.
- The budget applies to evidence/context tokens; the question is reported separately.
- Context joins selected original fragments with one ASCII space. Original fixture text is never modified in the fragment records.
- `asm` retrieves question-matching fragments and expands them in score/address order within budget.
- `baseline` concatenates original fragment text in fixture order, then takes the prefix ending at the last ASCII word token that fits within budget. It emits empty retrieved-address, lookup, and expanded lists. It performs no ASM retrieval, address lookup, or expansion.

## Output

One JSON object per invocation with these fields:

- `input_id`
- `original_source_tokens`
- `question_tokens`
- `retrieved_addresses`
- `lookups`: input address and exact fragment text or `null`
- `expanded`: selected address/text pairs in assembly order
- `context`
- `context_tokens`
- `elapsed_ns`

Correctness comparisons ignore only `elapsed_ns`. `elapsed_ns` measures monotonic wall-clock time from before reading the fixture through retrieval and context assembly; JSON serialization/output is excluded from this internal field. The Python runner separately records whole-process wall time, which includes serialization and process launch. Timings must be collected across repeated runs; compile/build time is reported separately from runtime.

## Per-operation timings

On successful runs, each implementation writes one additional line to standard error, prefixed `ASM-BENCH-METRICS ` and followed by a JSON object with nonnegative integer nanosecond values:

- `input_parse_ns`: fixture reading and record parsing/validation.
- `retrieval_ns`: tokenization, fragment scoring/filtering, and ranking.
- `address_lookup_ns`: address resolution for requested lookups.
- `expansion_assembly_ns`: budget selection and evidence-context assembly.
- `serialization_ns`: output serialization and writing the result object.

The metrics line is measurement metadata and is not part of the expected standard-output JSON. A zero indicates that the operation fell below the timer's resolution; the runner records that metric as `null`. It rejects missing, duplicate, or invalid metrics and records each operation separately.
