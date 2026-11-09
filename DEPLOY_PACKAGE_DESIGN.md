Create a portable production-oriented ASM deployment package inside the ASM project.

## Primary Goal

Create a new directory:

deploy-package/

This directory represents the portable, deployable ASM package.

It must be possible to copy the contents of:

deploy-package/asm/

into another AI development project and provide an AI agent with the included documentation and tool registry so the agent can use ASM to manage its own scoped context.

The deploy package is NOT a benchmark or research environment.

## Strict Separation Requirements

Do NOT include:

- benchmarks
- benchmark runners
- benchmark datasets
- benchmark reports
- performance comparison code
- test suites
- experimental implementations that are not required for deployment
- research-only documentation

The deploy package should contain only the runtime components, documentation, schemas, and tool interfaces necessary to integrate ASM into another AI project.

## Required Structure

Create:

deploy-package/
    README.md
    INSTALL.md
    tool-registry.json

    asm/
        README.md
        AGENT_GUIDE.md
        ASM_SCOPE.md
        INTEGRATION_GUIDE.md

        core/
        tools/
        schemas/

Use the existing ASM implementation as the source of truth where possible. Reuse or refactor production-relevant code rather than duplicating experimental benchmark code.

## ASM Design Goal

The deployable ASM system must help an AI agent manage bounded semantic context.

ASM should organize information into scopes.

Examples:

- project architecture
- subsystem
- feature
- bug investigation
- migration
- deployment
- current task

Each scope should support multiple levels of abstraction and addressable retrieval of deeper detail.

The agent should not need to load an entire project's context when only a small portion is relevant.

## Required Tool Registry

Create:

deploy-package/tool-registry.json

with stable tool handles for:

asm.create_scope
asm.add
asm.query
asm.get
asm.inspect
asm.adjust_scope
asm.summarize
asm.recover

Each tool entry must include:

- stable handle
- description
- required parameters
- optional parameters
- expected result format where appropriate

The registry must be designed so another AI agent framework can discover the available ASM capabilities.

## Required Tool Behavior

### asm.create_scope

Create a bounded semantic context.

Inputs should support:

- scope identifier
- purpose
- optional initial context
- optional parent scope

### asm.add

Add information to a scope.

The system should preserve semantic information and create addressable context where appropriate.

### asm.query

Retrieve the most relevant context for a query.

Support:

- scope identifier
- semantic query
- token budget
- abstraction depth

The result should prefer the smallest useful amount of context.

### asm.get

Retrieve deeper information using an address or context identifier.

Support multiple abstraction levels where the underlying information is available.

### asm.inspect

Inspect the health of the active scope.

This is a critical feature.

The system should help identify conditions such as:

- scope is too broad
- scope is too narrow
- unrelated topics are mixed together
- relevant detail exists below the current abstraction level
- referenced context is missing
- the working summary may be stale
- conflicting information exists
- the agent may need to rebuild its understanding

Return structured recommendations rather than pretending certainty.

### asm.adjust_scope

Allow an agent to adjust context boundaries.

Support operations such as:

- split
- merge
- narrow
- broaden
- rebuild

Do not silently destroy context.

### asm.summarize

Create or update a compressed working representation of a scope.

The summary should preserve references to deeper addressable information whenever possible.

### asm.recover

Provide a context recovery workflow for an agent that suspects it has lost track of the project or current task.

The recovery result should help the agent:

1. inspect the active scope
2. identify missing or conflicting context
3. retrieve the relevant working summary
4. retrieve deeper detail where necessary
5. rebuild a coherent working context

## Required Agent Documentation

Create:

asm/AGENT_GUIDE.md

This document must explicitly explain when an AI agent should use ASM.

Include triggers such as:

- project context becoming large
- multiple subsystems being involved
- uncertainty about previous decisions
- conflicting information
- repeated searches for the same information
- returning after context compression
- inability to explain the current task's relationship to the larger system
- suspected loss of context

Include a Context Recovery Protocol.

The protocol should explicitly tell the agent:

DO NOT GUESS WHEN CONTEXT CONFIDENCE IS LOW.

Instead:

1. inspect the current scope
2. retrieve the relevant semantic summary
3. retrieve deeper context using addresses
4. adjust scope boundaries if necessary
5. rebuild working understanding
6. continue only when sufficient context has been recovered

## Required Integration Documentation

Create:

asm/INTEGRATION_GUIDE.md

Explain how another AI development project can:

1. copy the asm directory
2. register tool-registry.json with its agent/tool system
3. initialize ASM
4. create project scopes
5. invoke the ASM tools
6. provide the agent with AGENT_GUIDE.md

Do not assume a specific AI framework unless required by the existing implementation.

Keep framework-specific integration separate from the core portable package.

## Design Principles

Follow these principles:

1. ASM manages context; the LLM performs reasoning.
2. Prefer minimal relevant context over maximum context.
3. Preserve addressability to deeper detail.
4. Scopes should be explicit and inspectable.
5. The agent should be able to recognize context uncertainty.
6. ASM should support recovery rather than allowing the agent to confidently hallucinate missing context.
7. Avoid unnecessary dependencies.
8. Do not include benchmark or research infrastructure.
9. Keep the deploy package portable.
10. Do not modify benchmark behavior while creating the deployment package.

## Verification

Before finishing:

1. Inspect the deploy-package directory.
2. Verify that no benchmark or testing content was copied into it.
3. Verify that tool-registry.json matches actual available tool implementations.
4. Verify that all documented paths exist.
5. Verify that an external AI project could reasonably copy asm/ and integrate it using the documentation.
6. Report the final directory tree.
7. Report any existing ASM functionality that could not be cleanly included and explain why.

Do not claim functionality exists unless the corresponding implementation exists.
Do not invent benchmark results or deployment capabilities.
Prefer a small working deploy package over a large incomplete abstraction.