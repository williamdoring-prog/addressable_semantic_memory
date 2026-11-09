# ASM Integration Guide

This document explains how another AI development project can integrate ASM into
their system. The integration is framework-agnostic — ASM provides a portable,
deterministic runtime that any AI agent can use.

## 1. Copy the `asm/` Directory

The minimum integration requires copying the `asm/` directory from this package:

```
your-project/
  asm/           ← copy from deploy-package/asm/
  tool-registry.json  ← register with agent framework
  asm_input.txt     ← your addressed store
  your-agent-code/
```

The `asm/` directory contains:
- `core/asm.py` — the ASM runtime (ASM class, Fragment dataclass, WORD_RE)
- `AGENT_GUIDE.md` — when and how to use ASM
- `ASM_SCOPE.md` — scope organization and addressable retrieval
- `INTEGRATION_GUIDE.md` — this document (you are here)
- `tools/` — tool interface (dispatch, render, load_fragments)
- `schemas/` — function-calling tool schemas

## 2. Register `tool-registry.json`

Register the `tool-registry.json` file with your agent/tool framework. This provides
stable tool handles that the agent can discover and bind:

```json
{
  "version": 1,
  "tools": [
    { "tool_id": "asm.create_scope", ... },
    { "tool_id": "asm.add", ... },
    { "tool_id": "asm.query", ... },
    { "tool_id": "asm.get", ... },
    { "tool_id": "asm.inspect", ... },
    { "tool_id": "asm.adjust_scope", ... },
    { "tool_id": "asm.summarize", ... },
    { "tool_id": "asm.recover", ... }
  ]
}
```

The framework can then bind these to function calls or tool invocations.

## 3. Initialize ASM

Create an ASM instance and initialize an addressed store. The store format is:

```
 Line 1: question (single line, the agent's query)
 Line 2: default budget (integer words, e.g. 600)
 Lines 3+: <address>\t<text>   (one unit per line, tab-separated)
```

Example `asm_input.txt`:

```
How does ASM retrieve relevant context and keep it bounded?
600
doc/chunk/0001	NOAA Technical Report NESDIS 142-9 ...
doc/chunk/0002	The National Environmental Satellite...]
...
```

In Python:

```python
import sys
sys.path.insert(0, "asm")
from asm.core.asm import ASM, Fragment

asm = ASM()

# Option A: Load from file store
# The store format is parsed by asm_tool.load_fragments or manually

# Option B: Inline units
fragments = [
    Fragment("architecture", "ASM uses deterministic retrieval and bounded context assembly."),
    Fragment("memory", "Persistent memory should preserve important project state across sessions."),
    Fragment("retrieval", "Retrieval ranks relevant fragments using question term overlap."),
]
result = asm.run("How does ASM retrieve relevant context?", fragments, 600)
```

## 4. Initialize Scopes

Use `asm.create_scope` to create project scopes relevant to your domain:

```python
# Create a scope for the authentication subsystem
result = asm.create_scope(
    scope_id="auth",
    purpose="Authentication and authorization subsystem",
    initial_context=[
        {"address": "auth/login", "text": "Login form validates credentials against user store"},
        {"address": "auth/oauth", "text": "OAuth2 integration with Google and GitHub"},
    ],
    parent_scope="project"
)
```

## 5. Invoke ASM Tools

The core ASM tools an agent can invoke:

### `asm.query` — Retrieve relevant context

```python
result = asm.query(
    scope_id="auth",
    question="What are the password requirements?",
    budget=150
)
# Returns: context, selected addresses, context_words, original_source_words
```

### `asm.inspect` — Resolve address to verbatim text

```python
result = asm.inspect(
    scope_id="auth",
    address="auth/login"
)
# Returns: address, text, words (verbatim resolution)
```

### `asm.add` — Add information to a scope

```python
result = asm.add(
    scope_id="auth",
    address="auth/mfa",
    text="Multi-factor authentication via TOTP is supported for all user accounts"
)
```

### `asm.adjust_scope` — Adjust context boundaries

```python
result = asm.adjust_scope(
    scope_id="auth",
    address="auth/password",
    operation="narrow",
    preserve=["auth/mfa"]  # preserve relevant detail through the narrowing
)
```

### `asm.summarize` — Create compressed working representation

```python
result = asm.summarize(
    scope_id="auth",
    budget=200  # compress to 200 words
)
# Returns: summary text, preserved addresses referencing deeper detail
```

### `asm.recover` — Context recovery workflow

```python
result = asm.recover(
    scope_id="auth",
    check_active=True,
    rebuild=True
)
# Returns: inspection of active scope, missing/conflicting context,
#   relevant summary, deeper detail addresses, rebuild steps
```

## 6. ASM Principles to Honor

1. **ASM manages context; the LLM performs reasoning.** — ASM serves minimal
   relevant context; the LLM reasons over it.

2. **Prefer minimal relevant context over maximum context.** — Use budgets that
   serve just enough context, not everything.

3. **Preserve addressability to deeper detail.** — Summaries should reference
   deeper addresses so the agent can always retrieve more detail when needed.

4. **Scopes should be explicit and inspectable.** — Agents should always be able
   to inspect the current scope's health and boundaries.

5. **The agent should be able to recognize context uncertainty.** — Use `asm.inspect`
   to check scope health before proceeding.

6. **ASM should support recovery rather than allowing the agent to confidently
   hallucinate missing context.** — Always follow the Context Recovery Protocol
   when confidence is low.

7. **Avoid unnecessary dependencies.** — The ASM runtime uses stdlib only
   (Python 3.10+). No external packages required.

8. **Keep framework-specific integration separate from the core portable package.**
   — ASM itself is framework-agnostic. Framework bindings (OpenAI function calling,
   Anthropic tool use, etc.) go in the integrating project, not in ASM.

## 7. Verification

After integration, verify:

1. `asm.run()` with known inputs produces deterministic outputs
2. `asm.inspect()` resolves addresses to correct verbatim text
3. `asm.summarize()` preserves references to deeper addresses
4. `asm.recover()` follows the Context Recovery Protocol
5. Tool registry is in sync with available implementations
6. An external AI project can copy `asm/` and integrate using the documentation