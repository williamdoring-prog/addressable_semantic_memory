# Context Pressure Pilot — 2026-11-05

Task: ASM-069 — Context Pressure Curve
Status: BLOCKED during local ASM semantic compression

## Findings Summary

The first local-model smoke run did not produce a paired ASM/baseline result. At a 512-token evidence budget, the no-ASM prefix baseline answered from the prefix and correctly did not recover the multi-hop answer. The ASM run failed before generation: its semantic-compression request returned HTTP 500 for a 12,546-token source. No result supports a claim that ASM improves answer quality.

The append-only experiment record is `data/results/context_pressure_2026-11-05.jsonl`. It preserves an earlier malformed-output attempt and the corrected fixture smoke attempt. The corrected source hash is `e274fb5b42335acec68da552db5fc3534eb45c7d62e74f18ba893ddb7331aa0b`. The local model was `qwen2.5:7b`, catalog digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`; its installed model parameters report `num_ctx 25000`.

## Methods

The pilot uses a deterministic synthetic source with multi-hop evidence at distant positions:

1. Project Orion was initially assigned Component Delta.
2. Component Delta was later replaced by Component Sigma.
3. The final source states that current Component Sigma requires 16 GB.

The source also contains a superseded 8 GB Delta value and a similar-name Orion-2/Kappa distractor. The question asks for the memory requirement of the currently used Project Orion component. The evaluation criteria check component identity, the 16 GB value, and avoiding the superseded component. The generated source has 12,546 tokens under the project tokenizer; the attempted 512-token budget is well below source size.

The runner uses the existing local app comparison path, unchanged generation settings, the same question/source/model/evaluator for both strategies, and one repetition for the smoke test. Results go to a dedicated JSONL file so the regular experiment history is untouched. This was a smoke attempt, not the planned five-budget, three-repetition curve.

## Results

Corrected fixture smoke at 512 tokens:

- Baseline: answer generation completed; normalized exact match failed (`16 GB` expected); criterion evaluator passed 1 of 3 criteria (33.33%). It correctly did not name Delta as current, but it did not identify Sigma or the 16 GB requirement.
- ASM: semantic compression returned HTTP 500. Answer generation and criterion evaluation did not run; score is unavailable.

Earlier harness attempt retained in the same log:

- Source size: 9,242 project-tokenizer tokens with 887 fragments.
- Baseline: generation completed; exact match failed; criterion score 33.33%.
- ASM: the compressor returned JSON in an unsupported shape (no `representations` list); answer generation and criterion evaluation did not run.

Automated checks for the deterministic fixture verify source size, distant evidence placement, reproducibility, and exact source-fragment address resolution.

## Limitations and Next Step

The 100,000-token source proposed in the inspiration text is outside this prototype's tested range. The current semantic compressor sends the full source and address metadata in one local inference request; it failed at the 12,546-token source in this pilot. The model's configured context value alone does not guarantee that the full request and generated representation set fit runtime memory or the effective inference limits.

ASM-069 remains blocked until the compression path can handle long sources deterministically enough to produce valid, provenance-complete representations (or an explicitly documented non-semantic-index condition is selected for a different experiment). After that, rerun the paired multi-budget curve with repeated trials, retaining all failures, and inspect retrieved evidence accuracy separately from final answer accuracy. Do not interpret the current baseline-only result as an ASM comparison.

## Conclusion

This pilot exposes a practical prerequisite for the proposed flagship experiment: the current ASM compression path cannot yet complete a long-source run. The baseline correctly fails to answer from a 512-token prefix, but there is no paired ASM answer to compare. A genuine context pressure curve and any claim about ASM capability remain unestablished.
