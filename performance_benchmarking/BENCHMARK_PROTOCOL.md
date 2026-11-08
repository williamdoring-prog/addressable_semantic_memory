
# ASM Benchmark Protocol

## 1. Objective

Measure the effects of ASM on:

1. Context consumption.
2. Answer quality.
3. Execution time.
4. Memory consumption.
5. Information retrieval accuracy.
6. Total computational overhead.

## 2. Primary Comparison

Compare:

A. ASM Disabled
- Original source material.
- Conventional context preparation.
- Normal LLM execution.

B. ASM Enabled
- Original source material processed through ASM.
- Addressable semantic representations.
- Selective retrieval and expansion.
- LLM execution using assembled context.

Both approaches must receive equivalent source information and answer the same questions.

## 3. Context Budgets

Initial benchmark budgets:

512
1,024
2,048
4,096
8,192
16,384

Allow custom values.

Record the actual token count rather than assuming the requested budget was reached.

Distinguish evidence/context tokens from system instructions, question tokens, and generation tokens.

## 4. Benchmark Categories

Create tests covering:

- Simple factual retrieval.
- Numerical information.
- Long-document comprehension.
- Multiple-document reasoning.
- Information located far apart in source material.
- Contradictory information.
- Exact wording retrieval.
- Relationships between concepts.
- Missing information.
- Questions requiring detailed source reconstruction.

## 5. Measurements

### Token Efficiency

- Original input tokens.
- Compressed representation tokens.
- Retrieved tokens.
- Expanded tokens.
- Final model input tokens.
- Total tokens across all model calls.

### Answer Quality

- Correctness.
- Completeness.
- Numerical accuracy.
- Evidence accuracy.
- Missing-information handling.

### Performance

- Compression time.
- Indexing time.
- Retrieval time.
- Expansion time.
- Context assembly time.
- Model response time.
- Total execution time.

### Resource Consumption

Where measurable:

- CPU utilization.
- System RAM.
- GPU utilization.
- VRAM.
- Peak memory consumption.

## 6. Experimental Controls

Keep constant between comparable experiments:

- Model.
- Model version.
- Source material.
- Question.
- Tokenizer.
- Generation settings.
- System instructions.
- Evaluation criteria.

Record all settings.

Use identical generation settings and seeds where supported.

Randomize execution order where practical.

## 7. Repetition

Run each experiment at least three times initially.

Store every individual result.

Report:
- Median.
- Minimum.
- Maximum.
- Number of successful runs.
- Number of failed runs.

Use additional repetitions before making strong performance claims.

## 8. Result Storage

Each experiment must retain:

- Unique run ID.
- Timestamp.
- Strategy.
- Context budget.
- Model information.
- Input text or source reference.
- Question.
- Raw response.
- Expected answer or scoring rubric.
- Evaluation results.
- Token counts.
- Timing measurements.
- Resource measurements.
- Errors.

Never overwrite previous results.

## 9. Important Rules

A reduction in token count is not automatically an improvement.

An improvement in response time is not automatically an improvement in efficiency if the ASM processing overhead is excluded.

Report total processing cost.

A successful benchmark must consider both answer quality and resource consumption.

Do not conceal cases where ASM performs worse than the baseline.
