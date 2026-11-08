
# ASM Technical Specification

## 1. Purpose

Implement an Addressable Semantic Memory mechanism capable of representing source information compactly while preserving the ability to retrieve relevant original information.

The implementation must be measurable independently of the LLM.

## 2. Core Concepts

### Source Material

Original text or other supported input data.

Source material must remain unchanged.

### Semantic Representation

A compressed representation of information extracted from source material.

A representation may contain:
- A semantic description.
- Important facts.
- Relationships.
- Keywords or identifiers.
- Address references.

### Address

A stable identifier that points to an original information unit.

Addresses must be resolvable.

### Retrieval

The process of identifying relevant representations or source fragments for a particular task.

### Reconstruction

The process of using addresses to recover relevant original information.

## 3. Required Operations

Implement the following operations as independent functions:

### INGEST

Input:
Original source material.

Output:
Addressable source fragments and associated metadata.

### COMPRESS

Input:
Source fragments.

Output:
Compressed semantic representations.

### ADDRESS

Input:
Source fragment or semantic representation.

Output:
A stable reference to the underlying information.

### RETRIEVE

Input:
Question or task.

Output:
Relevant semantic representations and their addresses.

### EXPAND

Input:
One or more addresses.

Output:
The corresponding original information.

### ASSEMBLE

Input:
Task, representations, retrieved information, token budget.

Output:
A context suitable for an LLM request.

## 4. Required Measurements

Record:

- Original source token count.
- Compressed representation token count.
- Compression ratio.
- Number of representations created.
- Number of addresses created.
- Number of addresses retrieved.
- Number of expansions.
- Tokens recovered through expansion.
- Final assembled context tokens.
- Processing time.

Compression ratio:

Original token count / compressed representation token count.

Also report percentage reduction:

(1 - compressed token count / original token count) × 100.

Do not treat compression ratio as a measure of information quality.

## 5. Correctness Requirements

- Addresses must resolve to the correct source.
- Source material must remain unchanged.
- Retrieval must not silently invent source content.
- Expansion must return the correct original fragment.
- Missing addresses must produce explicit errors.
- Duplicate references must be handled consistently.
- Context assembly must respect the configured budget.
- All transformations must be measurable.

## 6. Algorithm Development

The first implementation should prioritize correctness and simplicity.

Do not prematurely optimize.

The precise compression, indexing, retrieval, and reconstruction algorithms should remain modular so they can be replaced and compared experimentally.

## 7. Future Extensions

Possible future experiments:

- Hierarchical semantic representations.
- Multiple levels of abstraction.
- Relationship graphs.
- Cross-document references.
- Incremental updates.
- Adaptive compression.
- Query-dependent compression.
- Recursive retrieval.
- Selective expansion.
- Multimodal addressable information.

These are not requirements for the initial prototype.
