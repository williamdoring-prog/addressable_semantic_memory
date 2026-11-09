# ASM Agent Guide

This document explicitly explains when an AI agent should use ASM to manage scoped
context. Use ASM as a proactive context management strategy, not as a fallback.

## Triggers for Using ASM

Use ASM when any of the following conditions apply:

1. **Project context becoming large** — the accumulated knowledge about the project
   exceeds a reasonable word budget for the LLM to process effectively.

2. **Multiple subsystems being involved** — the task touches different domain areas
   (e.g., frontend + backend + database + infrastructure) that benefit from separate
   scope management.

3. **Uncertainty about previous decisions** — the agent cannot easily recall why
   certain architectural decisions were made, or what the trade-offs were.

4. **Conflicting information** — different sources or subsystems provide contradictory
   information about the same topic, and the agent needs to track multiple perspectives.

5. **Repeated searches for the same information** — the agent is re-querying for
   facts it has already served, indicating the current context doesn't retain them.

6. **Returning after context compression** — the agent previously compressed context
   via `asm.summarize` and is returning to the project; need to recover the compressed
   view.

7. **Inability to explain the current task's relationship to the larger system** —
   the agent cannot articulate how its current subtask fits into the overall project.

8. **Suspected loss of context** — the agent has reason to believe important context
   has been dropped or forgotten.

## Context Recovery Protocol

**DO NOT GUESS WHEN CONTEXT CONFIDENCE IS LOW.** Instead, follow this exact protocol:

### Step 1: Inspect the Current Scope

Call `asm.inspect(scope_id="<current_scope>")` to determine:
- The active scope's status (healthy, too_broad, too_narrow, mixed_topics,
  stale_summary, missing_context, conflicting_info, rebuild_needed)
- The current summary and any identified issues
- Which addresses are present and which are missing

### Step 2: Retrieve the Relevant Semantic Summary

If a summary exists, retrieve it via `asm.summarize(scope_id="<current_scope>", budget=<N>)`
where budget is appropriate for the desired compression level. This gives a compressed
working representation that preserves references to deeper detail.

### Step 3: Retrieve Deeper Context Using Addresses

From the summary or inspection, identify missing or key addresses, then call
`asm.get(scope_id="<current_scope>", address="<addr>", depth=<N>)` to retrieve
deeper detail. Use increasing depth values to explore the abstraction ladder.

### Step 4: Adjust Scope Boundaries If Necessary

If inspection reveals issues:
- **scope is too broad** → `asm.adjust_scope(scope_id=..., address=..., operation="narrow")`
- **scope is too narrow** → `asm.adjust_scope(scope_id=..., address=..., operation="broaden")`
- **unrelated topics mixed together** → `asm.adjust_scope(scope_id=..., address=..., operation="split")`
- **conflicting information** → `asm.adjust_scope(scope_id=..., address=..., operation="rebuild")`
- **stale summary** → `asm.adjust_scope(scope_id=..., address=..., operation="rebuild")`

### Step 5: Rebuild Working Understanding

After adjusting boundaries, reconstruct the coherent context:
1. Re-query with updated scope
2. Re-summarize with fresh budget
3. Verify the recovered context addresses the original question

### Step 6: Continue Only When Sufficient Context Has Been Recovered

Only proceed with the task when `asm.inspect` returns status "healthy" or when
the agent has sufficient context confidence to proceed. If confidence remains low
after the full protocol, document the unresolved gaps and seek external human
guidance.

## When ASM Is NOT Needed

- The project has very few components/subsystems (single-digit address count)
- The task is short-lived and context fits comfortably within the LLM's window
- No uncertainty about decisions, no conflicting information, no repeated searches
- The agent has perfect recall of all relevant project details

## Integration Notes for Agent Frameworks

- Register `tool-registry.json` with your agent's tool system
- The ASM tools operate under a **WORD budget** (whitespace-delimited word count,
  never tokens)
- Each scope has an associated addressed store (asm_input.txt format or inline units)
- ASM is deterministic: identical inputs always produce identical outputs
- ASM manages context; the LLM performs reasoning over the served context