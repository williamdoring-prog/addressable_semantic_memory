# Addressable Semantic Memory (ASM)
## Design Specification: Progressive Abstraction and Token-Length Lists

**Status:** Design proposal  
**Revision:** 1.0  
**Date:** 2026-11-07  
**Purpose:** Define an addressable, progressively expandable memory architecture, including an abstraction ladder and tokenizer-specific token-length lists that expose the cost of retrieving more detail.

---

## Repository layout

Added 2026-11-07. The repository root is a benchmarking workspace: three
directories plus the shared documents `README.md` (entry point; agents
start there to adopt the registered tools for development), `ASM_DESIGN.md`
(this specification, applying across both benchmarking tracks), `WORKQUEUE.md`
(the
continuation protocol and work queue), `bench.py` (the central
command-line utility that runs the performance and/or accuracy benchmark
suites and prints their metric tables; metric definitions in WORKQUEUE
§R19), and `docs/` (`IDEAS_LEDGER.md` — consolidation inventory;
`tools_registry.json` — the agent tool registry refreshed by
`python bench.py registry`). This section is
deliberately unnumbered so that section numbers referenced elsewhere
(§5.2, §6.3, W7 amendments) stay stable.

### `accuracy_benchmarking/` — accuracy track (primary)

The active implementation and measurement of this design's first concrete
question: does the addressable-memory retrieval layer preserve the facts a
consumer needs as the served context shrinks? Contents at purpose level:
four equivalent deterministic ASM implementations (Python/C/Rust/Go), the
challenge harness, the NOAA challenge inputs and oracle
(`challenge-documents/`), generated fixture files, and the committed
`results/` artifacts — the complete file inventory is maintained once, in
WORKQUEUE §I. Piece-level harness commands run from inside this directory;
the central CLI `python bench.py` runs them from the repo root and prints
the consolidated metric tables (WORKQUEUE §R19, agent registry §R20).
Layout, adequacy semantics, and the harness word-count rule live in
README.md and `WORKQUEUE.md` (§R4); the design obligations behind them are
in this specification (§5.2 and §6).

### `performance_benchmarking/` — predecessor track

The earlier sibling project, now absorbed into this repository as plain
files (2026-11-07). The nested repository that came with the move was
removed; its complete history (`master` at `0dd9839`, 3 commits) was
exported to `performance_benchmarking/previous-history.bundle` beforehand
and is itself tracked here, so the prior work stays fully recoverable
(`git clone performance_benchmarking/previous-history.bundle`). Its
contents (web app, engine, benchmark suites, data, findings docs, tests)
are inventoried once in WORKQUEUE §I, not re-listed here. It holds the
prior multi-language performance benchmarking of the same memory idea —
timing and throughput measurements rather than agreement and
retrieval-adequacy checks. Keep it as prior art of record: do not couple
its code to `accuracy_benchmarking/`; the 2026-11-07 consolidation queue
(WORKQUEUE C1..C6) governs reconciliation — predecessor root docs are
scheduled for archive (C3) and their superseded objectives (browser
interface, token budgets) are stamped as superseded. Version-control
note: `data/results/experiments.jsonl` is a 97 MB append-only experiment
log, deliberately excluded from version control by the root `.gitignore`
— it stays working-tree-only.

### `deploy-package/` — release staging (reserved)

Currently empty. Reserved as the staging area where a deployable release
package is assembled: the built binaries of the four implementations, the
fixture set and runner needed to reproduce a measurement run, and the
minimal documentation to operate it — packaged as one self-contained
deliverable. Because git does not track empty directories, this directory
will gain a README once release packaging (a future item in `WORKQUEUE.md`)
starts populating it.

---

## 1. Executive summary

Addressable Semantic Memory (ASM) is a model-independent memory and retrieval layer. It stores original source material, creates linked semantic representations at different abstraction levels, and allows a model to request additional detail only where it is needed.

The central mechanism is **progressive semantic resolution**:

1. The model receives a compact representation of a large information pool.
2. The representation exposes the measured token cost of expanding it to more detailed levels, including the complete original source pool.
3. The model identifies a concept, claim, section, or other address that needs more detail.
4. ASM resolves that address to the requested representation or source fragments.
5. The host reconstructs the model's working context with the requested material.
6. The model continues reasoning with the expanded context.
7. The host may later rebuild a smaller context from compact representations and retained findings.

ASM preserves the original source and its provenance. Abstraction is an additional representation, never a destructive replacement for the only copy of the source.

A key feature is the **token-length list**. Each representation and expandable source pool can expose its measured token count for supported tokenizers. This lets the model and host estimate the actual cost of expansion before requesting it. Counts are measurements, not arbitrary size labels or fixed token targets.

## 2. Goals and non-goals

### 2.1 Goals

- Preserve original source content, subject only to explicitly recorded normalization.
- Make concepts, claims, passages, sections, procedures, and source fragments addressable.
- Link compact representations to progressively more detailed representations and original evidence.
- Retrieve targeted material instead of loading an entire document by default.
- Expose actual token costs for each representation and expandable pool.
- Support multiple model tokenizers without coupling the memory format to one model family.
- Preserve provenance, relationships, qualifications, uncertainty, and contradictions.
- Keep semantic processing separate from deterministic storage, hashing, token counting, indexing, retrieval, and context assembly.
- Allow independent implementations and interchangeable model providers.

### 2.2 Non-goals

- ASM is not itself an LLM, agent, inference server, or prompt template.
- ASM does not require every source to be rewritten into one universal summary.
- ASM does not assume shorter representations are always more accurate or useful.
- ASM does not assume different model tokenizers produce interchangeable counts.
- ASM does not silently discard original material when a representation is updated.
- ASM does not require every source to contain every abstraction level.

## 3. Core data model

ASM should distinguish sources, semantic units, representations, and expansion pools.

### 3.1 Source

A source is an immutable or versioned record of original input.

Suggested fields:

- `source_id`: stable unique identifier.
- `source_version`: immutable version identifier.
- `source_uri`: original location, when available.
- `content_hash`: hash of stored source bytes or canonical source text.
- `media_type`: text, PDF, HTML, code, transcript, and so on.
- `ingested_at`: timestamp.
- `normalization`: transformations applied before storage.
- `metadata`: author, title, timestamps, access scope, and other attributes.

The source record is authoritative. Every derived representation must retain links to it.

### 3.2 Semantic unit

A semantic unit is an addressable item such as a claim, concept, paragraph, procedure, entity, relationship, event, or section.

Suggested fields:

- `unit_id`: stable unique identifier.
- `unit_type`: declared semantic type.
- `label`: concise human-readable address.
- `source_spans`: one or more exact source ranges.
- `parent_ids` and `child_ids`: structural relationships.
- `related_unit_ids`: cross-references.
- `created_at` and `updated_at`.
- `status`: active, superseded, disputed, or archived.

A semantic unit may map to multiple non-contiguous source fragments, and a source fragment may support multiple semantic units. The mapping is many-to-many.

### 3.3 Representation

A representation is one rendering of a semantic unit at a particular abstraction level.

Suggested fields:

- `representation_id`
- `unit_id`
- `abstraction_level`
- `content`
- `content_hash`
- `parent_representation_ids`
- `source_span_refs`
- `fidelity_notes`
- `coverage_notes`
- `verification_status`
- `generation_method`
- `model_or_processor`
- `created_at`

A representation is not the source itself. It retains a path to the source fragments from which it was derived.

### 3.4 Expansion pool

An expansion pool is the complete set of source or intermediate material that an address can yield at a requested level. A pool may contain multiple non-contiguous source fragments or linked semantic units.

Suggested fields:

- `pool_id`
- `unit_id`
- `target_level`
- `member_refs`
- `ordering`
- `deduplication_policy`
- `pool_content_hash`
- `token_measurements`

Pool membership and ordering must be deterministic for a given version. If either changes, create a new pool version or hash.

## 4. Progressive abstraction ladder

### 4.1 Levels

Representations are ordered from most abstract and compact to most detailed. The original source is the terminal authoritative level.

| Level | Intended representation |
|---|---|
| L4 | Highly abstract conceptual index: topic, purpose, key relationships, and pointers |
| L3 | Compact semantic summary: central meaning and important relationships |
| L2 | Detailed synthesis: important claims, qualifications, conditions, and supporting structure |
| L1 | Source-near representation: selected verbatim passages or detailed extracted material |
| L0 | Original source content, exactly as retained |

These labels describe intended roles, not fixed token budgets. Length varies by source. A source may not need every intermediate level. Do not pad or force a representation to hit a predetermined token count.

### 4.2 Abstraction is not a quality score

Track these properties independently:

- **Abstraction level:** how far the representation is removed from the original.
- **Fidelity:** how accurately it preserves source meaning.
- **Evidence coverage:** how much relevant source material it represents.
- **Verification status:** whether source links, transformations, and constraints have been checked.
- **Token length:** measured size under a named tokenizer.

A lower level number does not automatically mean higher quality. A compact summary may omit a qualification; an intermediate representation may be more useful for a question than either a summary or the entire source.

### 4.3 Linked expansion

The normal progression is:

`L4 -> L3 -> L2 -> L1 -> L0`

Every representation points to the next more detailed representation and/or directly to its supporting source spans. A request may skip levels when the caller explicitly requests a target level or an intermediate representation does not exist. The response must identify what was actually returned.

Every level must preserve a route to the original source. No abstraction may become an orphaned summary.

### 4.4 Targeted expansion

Expansion operates on the smallest useful addressable unit, not automatically on the whole document.

Illustrative operations:

```text
EXPAND(unit="progressive-context-resolution")
EXPAND(unit="progressive-context-resolution", target_level="L2")
EXPAND(unit="progressive-context-resolution", target_level="L0")
EXPAND(unit="progressive-context-resolution", include_related=true)
```

A concept may resolve to multiple source fragments. The result identifies the returned fragments and their relationships. If an address is ambiguous, return candidate matches and request disambiguation rather than silently choosing one.

## 5. Token-length list feature

### 5.1 Requirement

Every model-facing compact reference should expose the measured token cost of the information available behind it. The model should be able to see the size of the **complete uncompressed expansion pool**, not merely the length of the compact reference.

This enables informed context-budget decisions. A model can decide not to expand a reference if the underlying material is too large, or request a narrower unit or intermediate level instead.

The token-length list is metadata about content. It is not a fixed abstraction scale and must not be used to force summaries into arbitrary token bands.

### 5.2 Tokenizer-specific measurements

Token counts depend on the tokenizer. Store each measurement with:

- tokenizer identifier and family;
- tokenizer version or revision;
- vocabulary/configuration hash where practical;
- counting implementation and version;
- measured token count;
- measurement timestamp;
- exact content hash measured.

A count is valid only for the exact content hash and tokenizer configuration recorded. If content changes, its count is stale and must be recomputed.

Never label a count simply `tokens` without identifying its tokenizer. Never compare counts from different tokenizers as if they were equivalent.

### 5.3 What to count

For each representation and expansion pool, measure:

1. The representation's own content.
2. The next more detailed representation, when available.
3. The complete original/source expansion pool.
4. Optionally, each individual source fragment in the pool.
5. Optionally, the assembled payload including serialization overhead, if that exact payload is what the host will send.

The **full-pool count** is especially important. It tells the model the cost of expanding the reference all the way to its original supporting material.

The host should distinguish content-token counts from transport or prompt overhead. If the final request wrapper adds tokens, expose that separately or measure the exact assembled payload.

### 5.4 Example model-facing representation

The following values are illustrative placeholders, not benchmark results:

```text
[REF asm:ctx-resolution]
Progressive context resolution: ASM supplies increasingly detailed evidence
for a selected concept while preserving links to original source material.

Token lengths:
  tokenizer: qwen3.5
  L4 representation: 18
  L3 representation: 74
  L2 representation: 286
  L1 representation: 1,240
  L0 full source pool: 8,912

Expand: asm:ctx-resolution
Source pool: 3 fragments
Source integrity: verified
```

A more compact form may be used when prompt efficiency matters:

```text
[REF asm:ctx-resolution | qwen3.5 L4:18 L3:74 L2:286 L1:1240 L0:8912]
Progressive context resolution; 3 source fragments; source verified.
```

The display format is an implementation choice. The semantic requirements are not: tokenizer identity, level-specific measured counts, and the full uncompressed pool count must remain available.

### 5.5 Multiple tokenizer list

When multiple target models are supported, expose a separate list for each tokenizer:

```text
Token lengths:
  qwen3.5:
    L4: 18
    L3: 74
    L2: 286
    L1: 1,240
    L0: 8,912
  llama:
    L4: 20
    L3: 81
    L2: 301
    L1: 1,318
    L0: 9,406
```

These values are illustrative only. Real counts must come from the corresponding tokenizer implementation. The host may show only the active model's tokenizer in the prompt while retaining all supported measurements in storage.

### 5.6 Missing or stale counts

- If a tokenizer is unsupported, report the count as unavailable; do not silently estimate.
- If only an estimate is available, mark it explicitly as estimated and identify the method.
- If the content hash changes, invalidate the old measurement.
- If a representation is regenerated, recompute its count.
- If a pool is assembled dynamically, count the exact deterministic assembly or expose fragment counts and clearly mark the total as an estimate.
- Never present a stale count as current.

### 5.7 Tokenizer registry

Use a pluggable tokenizer registry rather than hard-coded model assumptions.

```json
{
  "tokenizer_id": "qwen3.5",
  "family": "qwen",
  "revision": "recorded-version-or-commit",
  "implementation": "tokenizer-adapter-name",
  "configuration_hash": "sha256:...",
  "status": "available"
}
```

The registry can support Qwen, Llama, Mistral, and other tokenizer families as needed. Actual support is determined by installed adapters, not assumptions in the data format.

## 6. Model-facing addressing and expansion protocol

The model receives a readable compact representation and stable expansion handles. The host translates those handles into deterministic ASM operations.

Suggested logical operations:

```text
LIST(address)
EXPAND(address, target_level)
EXPAND(address, target_level, fragment_limit)
EXPAND(address, target_level, include_related)
INSPECT_SOURCE(address)
```

The API may use JSON, function calls, tool calls, or another structured protocol. The visible compact representation should not require embedding large amounts of metadata into prose.

### 6.1 Stable addresses

Prefer stable semantic IDs over using the displayed phrase as the sole identifier. Labels are useful, but phrases can be duplicated, edited, translated, or ambiguous.

```text
[REF asm:unit:01J...]
Label: progressive context resolution
```

### 6.2 Resolution behavior

- Resolve stable IDs exactly.
- Resolve labels through a search/index layer only when no ID is supplied.
- Return multiple candidates when ambiguous.
- Preserve source ordering where ordering matters.
- Preserve duplicate fragments when they have distinct evidentiary roles; deduplicate only under an explicit policy.
- Return provenance with every expansion.
- Report missing, superseded, inaccessible, or unavailable source material explicitly.

### 6.3 Expansion response

An expansion response should include:

- requested address and target level;
- returned representation IDs;
- content;
- source fragment references;
- tokenizer-specific token measurements;
- omissions or truncation;
- fidelity and verification notes;
- whether the returned material is complete for that target.

If a requested pool exceeds a supplied budget, ASM must not silently truncate it. Return a budget warning and offer deterministic subdivisions or a smaller abstraction level.

## 7. Dynamic context assembly

ASM stores and resolves memory. The **Context Assembler** is a separate host-side component responsible for constructing the actual model input.

A typical cycle:

1. The Context Assembler selects compact representations for the current task.
2. It includes token-length metadata for each expandable reference.
3. The model identifies an area that needs more evidence.
4. The model requests a targeted expansion.
5. ASM returns the requested representation and provenance.
6. The Context Assembler reconstructs the next model input, replacing or supplementing the compact reference.
7. The model continues reasoning with the expanded context.
8. When detail is no longer needed, the assembler can rebuild a compact context while retaining validated findings and relevant provenance.

Most inference APIs do not permit the host to remove tokens from a request already submitted. Context reduction therefore requires constructing and submitting a new request. The host must manage this reconstruction and preserve continuity through stable task state, references, and retained findings.

### 7.1 Context budget policy

- Reserve space for system instructions, current task, response, and tool overhead.
- Use tokenizer-specific counts for the active model.
- Prefer targeted expansion over full-pool retrieval.
- Before expanding, compare measured cost with the remaining budget.
- Allow the host to impose a hard expansion budget.
- Keep pinned instructions and critical constraints in the reconstructed context.
- Do not contract away unresolved contradictions, safety constraints, or essential qualifications.
- Track currently expanded details to avoid redundant retrieval.

The model may recommend an expansion, but the host remains responsible for enforcing the actual context limit.

## 8. Generation, validation, and source integrity

### 8.1 Abstraction generation

A pluggable synthesis pipeline may generate L1-L4 representations. Model inference is used where semantic interpretation is required; deterministic code handles storage, hashing, tokenization, indexing, and retrieval.

The generation pipeline should:

1. Ingest and preserve the source.
2. Segment it into addressable semantic units.
3. Generate useful abstraction levels.
4. Link every representation to its parent and source spans.
5. Measure token lengths with configured tokenizers.
6. Validate structural constraints and source traceability.
7. Mark unverified representations as such.

Not every document requires every level. Avoid unnecessary inference and storage when a useful ladder can be generated with fewer representations.

### 8.2 Validation

Validation should check:

- every derived representation has source references;
- all referenced source IDs and spans exist;
- the original source hash matches the stored source;
- the abstraction ladder has valid ordering and links;
- token measurements match the content hash and tokenizer revision;
- no representation claims complete coverage when it is partial;
- important qualifications, negations, dates, quantities, and conditions are not silently dropped;
- contradictions remain visible and linked to their evidence;
- generated content is distinguished from verbatim source content.

Automated checks can verify structure and provenance. Semantic fidelity may require model-assisted or human review; it must not be represented as mathematically guaranteed.

### 8.3 Updating source material

Do not overwrite historical representations in place when source content changes. Create a new source or unit version, regenerate affected representations, and retain prior versions and hashes for traceability.

## 9. Storage and implementation boundaries

A practical implementation can use a relational database for metadata and relationships, plus content-addressed files or blobs for source and representation content.

Recommended logical modules:

- **Ingestion:** imports and normalizes source material.
- **Semantic segmentation:** identifies addressable units and source spans.
- **Abstraction pipeline:** generates linked representations.
- **Tokenizer registry:** provides tokenizer adapters and exact counts.
- **Index and resolver:** maps IDs, labels, and semantic queries to units.
- **Expansion service:** retrieves the requested level and evidence.
- **Validation service:** checks provenance, hashes, structure, and measurements.
- **Context Assembler:** constructs model-specific working context outside ASM's storage core.

Keep these interfaces independent so a different model, tokenizer, database, or host application can be substituted without redesigning the memory model.

## 10. Suggested storage schema

The following is a conceptual schema, not a mandated database implementation.

```sql
CREATE TABLE sources (
    source_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    source_uri TEXT,
    media_type TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content_location TEXT NOT NULL,
    normalization_json TEXT,
    metadata_json TEXT,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (source_id, source_version)
);

CREATE TABLE semantic_units (
    unit_id TEXT PRIMARY KEY,
    unit_type TEXT NOT NULL,
    label TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json TEXT
);

CREATE TABLE source_spans (
    span_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    locator_json TEXT,
    FOREIGN KEY (source_id, source_version)
        REFERENCES sources(source_id, source_version)
);

CREATE TABLE unit_source_links (
    unit_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    PRIMARY KEY (unit_id, span_id, relationship)
);

CREATE TABLE representations (
    representation_id TEXT PRIMARY KEY,
    unit_id TEXT NOT NULL,
    abstraction_level INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    fidelity_notes TEXT,
    coverage_notes TEXT,
    verification_status TEXT NOT NULL,
    generation_metadata_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (unit_id) REFERENCES semantic_units(unit_id)
);

CREATE TABLE representation_links (
    from_representation_id TEXT NOT NULL,
    to_representation_id TEXT NOT NULL,
    relationship TEXT NOT NULL,
    PRIMARY KEY (from_representation_id, to_representation_id, relationship)
);

CREATE TABLE tokenizers (
    tokenizer_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    configuration_hash TEXT NOT NULL,
    implementation TEXT NOT NULL,
    metadata_json TEXT,
    PRIMARY KEY (tokenizer_id, revision, configuration_hash)
);

CREATE TABLE token_measurements (
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    tokenizer_id TEXT NOT NULL,
    tokenizer_revision TEXT NOT NULL,
    configuration_hash TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    token_count INTEGER NOT NULL,
    measured_at TEXT NOT NULL,
    measurement_kind TEXT NOT NULL,
    PRIMARY KEY (
        object_type, object_id, tokenizer_id,
        tokenizer_revision, configuration_hash, content_hash
    )
);
```

A production schema also needs migrations, indexes, access control, source-version constraints, and explicit expansion-pool records. The essential rule is that token measurements are tied to both the exact content hash and tokenizer configuration.

## 11. Example end-to-end flow

Assume a source document contains 9,000 tokens under the active model tokenizer and discusses a concept across three separate sections.

1. Ingestion stores the original document and computes its content hash.
2. Semantic segmentation creates a unit called `progressive-context-resolution`.
3. The abstraction pipeline creates L4, L3, L2, and L1 representations, each linked to relevant source spans.
4. The tokenizer adapter measures every representation and the full original expansion pool.
5. The model receives the compact L4 representation and its token-length list.
6. The model decides that L2 is sufficient and requests it.
7. ASM returns L2 with provenance and its measured token count.
8. The model identifies one unresolved claim and requests L0 for only the supporting source fragments.
9. The Context Assembler reconstructs the model input with those fragments, not the entire document.
10. The model resolves the question and produces a finding linked to the evidence.
11. The assembler later rebuilds a compact context containing the finding, its evidence reference, and the original expandable handle.

The intended benefit is that the model can reason over a large information pool without paying the full context cost until it needs the detail.

## 12. Performance and measurement considerations

Evaluate more than compression ratio. Measure:

- source ingestion time;
- abstraction-generation time and inference cost;
- storage overhead;
- tokenizer measurement time;
- resolver latency;
- expansion latency;
- context assembly time;
- total tokens submitted to the model;
- number and size of expansions;
- answer correctness;
- evidence traceability;
- qualification and constraint preservation;
- recovery of exact original source passages.

A smaller representation is useful only if it preserves enough information to guide correct retrieval. A system that saves tokens but causes incorrect expansion choices or loses important qualifications has not succeeded.

Benchmark against a no-ASM baseline using the same source material, model, tokenizer, prompt budget, and answer criteria. Record exact experimental conditions. Report exact-match scoring separately from semantic or rubric-based evaluation.

The active benchmark suite operationalizes the named metric framework via
the repo-root central CLI `bench.py`; authoritative definitions live in
WORKQUEUE §R19 (budget unit: words per §R4 — token-specific
measurements in this spec, §5, apply to storage-side token-length lists,
not to the harness's budget accounting).

## 13. Initial implementation sequence

1. **Immutable source and span storage:** store originals, hashes, and stable source locators.
2. **Semantic unit addressing:** create stable IDs and many-to-many links to source spans.
3. **Minimal abstraction ladder:** support a compact representation and at least one more detailed representation, plus original source.
4. **Tokenizer registry and token-length lists:** count every representation and the full source pool with the active tokenizer.
5. **Expansion API:** resolve stable IDs and return a requested level with provenance and counts.
6. **Context Assembler integration:** reconstruct model context using measured costs and targeted expansion.
7. **Validation and versioning:** detect stale counts, broken links, and source changes.
8. **Benchmarking:** compare quality, token use, latency, and traceability against a controlled baseline.
9. **Additional abstraction levels and tokenizer adapters:** add only where measurements demonstrate value.

Do not begin with a complex multi-agent abstraction pipeline. First prove the source-to-reference-to-expansion path, exact token accounting, and context reconstruction.

## 14. Open research questions

Investigate these experimentally rather than treating them as settled:

- Which semantic segmentation methods provide useful addressability without creating excessive tiny units?
- How should overlapping concepts and shared source fragments be represented?
- When is it better to expand to an intermediate level versus retrieve original fragments?
- How should source fragments be ranked when a unit has many supporting passages?
- How should confidence and evidence coverage be exposed without implying false precision?
- Which compact reference format gives models enough information while minimizing prompt overhead?
- Can the host predict useful expansions from task context without retrieving too much?
- How should contradictions and later corrections be represented across versions?
- Which tokenizer adapters are worth supporting based on actual target models?
- How much generation and validation effort is justified by downstream retrieval savings?

## 15. Design invariants

1. **Original preservation:** derived representations never replace the only copy of the source.
2. **Traceability:** every derived representation has a recoverable path to its source evidence.
3. **Progressive resolution:** the caller can request more detail for a specific address.
4. **Measured token lengths:** counts identify the tokenizer and exact content measured.
5. **Full-pool visibility:** compact references expose the measured cost of retrieving their complete original expansion pool.
6. **No arbitrary size labels:** abstraction levels are semantic roles, not fixed token-count bands.
7. **Deterministic retrieval:** the same versioned request resolves to the same ordered material.
8. **Explicit incompleteness:** truncation, missing source, estimates, and stale counts are disclosed.
9. **Separation of concerns:** ASM memory operations remain separate from model-specific context assembly and inference.
10. **Evidence before confidence:** fidelity and coverage are assessed independently of abstraction level and token length.

## 16. Summary

ASM is an addressable, progressively expandable semantic memory system. Its abstraction ladder gives models a compact overview and a controlled route toward detailed evidence and original source material. The token-length list makes that route measurable: a model can see not only the cost of the compact representation it is reading, but also the actual tokenizer-specific cost of expanding the complete source pool.

The design avoids fixed token-size tiers. It records real measured lengths, preserves the source, and lets the model and host choose the appropriate level of detail for the current task.
