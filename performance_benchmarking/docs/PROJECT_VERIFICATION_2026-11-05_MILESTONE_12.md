# Project Verification — 2026-11-05 — Milestone 12

This report records the final project review for ASM-065. It supplements the root specifications and preserves the live test evidence without replacing earlier research reports.

## Scope

- Confirmed four-language benchmark implementation and recorded v1.8 batch (60 runs across three fixtures, four languages, and five measured repetitions, plus two warmups per configuration); see [Milestone 11 findings](LANGUAGE_BENCHMARK_FINDINGS_2026-11-05_MILESTONE_11.md).
- Ran one live paired baseline/ASM comparison through `app.controller.server.execute_comparison` using the installed local Ollama model `gemma3:latest`.
- Used one repetition, context budget 32, deterministic generation settings (`temperature: 0`, `seed: 0`), and an identical source, question, model, and expansion setting for both strategies.
- Used source: “Aster stores the lithium sample at 4 degrees. The backup sample is at 9 degrees.” The expected answer was “The lithium sample is stored at 4 degrees.”

## Live inference results

The comparison ID was `ea602a0b-a736-40ed-91c3-4172350a84d0`. All recorded equivalence controls matched, including the installed model digest `68ceab7e468a31c988b44d5a4984a0e21f58c4f7158c6ce29c1804babac38df7`.

| Strategy | Context tokens | Answer | Normalized exact match | Errors |
|---|---:|---|---:|---|
| Baseline | 17 | The lithium sample is stored at 4 degrees. | 1.0 | None |
| ASM | 17 | The lithium sample is stored at 4 degrees. | 1.0 | None |

ASM used `local-model-semantic` representations. Its compression response covered both source addresses; controller validation accepted the representation, and retrieval/expansion completed. The recorded semantic-compression model time was approximately 1.04 seconds. For this short source, ASM and baseline assembled the same 17 context tokens, so this run shows a functional path, not a reduction or performance advantage.

The experiment records are appended to `data/results/experiments.jsonl`. An earlier calibration run with the shorter expected answer `4 degrees` also remains in the log; both model responses were correct full sentences, but normalized exact match appropriately scored that shorter reference as a mismatch. No prior record was replaced.

## Automated verification

Recorded in the project validation run:

- `python -m unittest discover -s tests -v` — 29 tests passed.
- `node --test tests/test_ui.mjs` — 1 test passed.
- `python -m compileall -q asm app benchmarks tests` — passed.
- `node --check app/interface/app.js` — passed.
- `node --check benchmarks/javascript/main.mjs` — passed.
- `rustup run stable rustfmt --check --edition 2021 benchmarks/rust/main.rs` — passed.
- `go vet` — passed.
- `git diff --check` — passed.

The complete four-language correctness-gated benchmark batch completed successfully and is documented in the linked Milestone 11 report. The latest code milestone is commit `c160fb7`.

## Limits and status

- The live check is a single paired repetition on one small factual example; it is functional verification, not a quality or efficiency study.
- Answer scoring is normalized exact match and does not assess semantic equivalence generally.
- Local inference was checked with one installed Ollama model. Other models and larger context-budget workloads remain available for user experiments.
- Resource metrics for ASM model runs are not measured by this controller; they remain null rather than estimated.

ASM-065 is complete. The project is ready for user testing.
