# WORK QUEUE — addressable_semantic_memory (consolidation edition)

Purpose: single continuation document so any agent (including small local
models with tiny context windows) can resume work across handoffs. Read §Q,
then work the first `status: todo` item top-down. One item at a time.

Repo: https://github.com/williamdoring-prog/addressable_semantic_memory

---

## §Q Quick state (read this first)

Project: ONE repository consolidating two benchmark projects of the same
Addressable Semantic Memory (ASM) idea — 2026-11-07 user directive:
*"There are two different benchmark projects being consolidated. I want to
conserve all the valuable ideas, prune outdated and unused contents."*

1. **accuracy_benchmarking/** — active accuracy track: four equivalent
   deterministic ASM implementations (Python/C/Rust/Go) + toy parity runner,
   the NOAA challenge harness (budget sweep in words, cross-impl MATCH,
   retrieval-adequacy checker), prompt files + criteria checklist for
   testing local models. All W2..W6 harness items done 2026-11-07.
2. **performance_benchmarking/** — predecessor performance track, absorbed
   2026-11-07 as plain files. Nested .git REMOVED; full history preserved in
   `performance_benchmarking/previous-history.bundle` (tracked; recover via
   `git clone performance_benchmarking/previous-history.bundle`). Contents:
   web app (`app/`), `asm/` engine, `benchmarks/` (standard suite,
   context-pressure pilot, `.asmbench` fixture format), `data/`, extensive
   findings/milestone docs, tests.
3. **deploy-package/** — empty release-staging dir, purpose documented in
   ASM_DESIGN.md "Repository layout".

Product direction locked 2026-11-07 (second user directive): the package is
CLI-ONLY — no browser/server control interfaces, configuration via terminal
args; keep it LEAN; default benchmark runs finish within a few minutes;
benchmark focus = performance across a range of small context windows, with
the goal of maximizing utility of context space (fewer tokens + inference
loads). Consequences applied already: predecessor `app/` pruned (preserved
in previous-history.bundle; see docs/IDEAS_LEDGER.md); challenge sweep now
prints a simple per-impl performance table plus total wall time.

The queue below follows: C1..C6 = consolidation (active), W1 = deferred
transcription (user directive stands), W8 = stretch. §C rules govern how
pruning happens (archive + ledger, never silent deletion).

If unsure where you were: re-run §V, then continue at the first `todo`.

---

## §E Environment facts (Windows machine, PowerShell)

- Repo root: `C:\Users\willi\Projects\asm_multilang_benchmark` — benchmarking
  workspace: `accuracy_benchmarking/` (active accuracy track),
  `performance_benchmarking/` (absorbed predecessor, plain files),
  `deploy-package/` (empty, reserved). Shared documents at root:
  `ASM_DESIGN.md`, `WORKQUEUE.md` (this file), `.gitignore`.
- Working directory for §V commands: `accuracy_benchmarking/`.
- Python 3.10 at `python` (site-packages: pymupdf installed, PIL installed; no pypdf).
- `go` on PATH is STALE (msys2 Go 1.17). Use `& $env:GOROOT\bin\go.exe` for builds
  and formatting. `benchmark.py` already handles this automatically.
- `rustc` (MSVC host) lacks link.exe; gnu target installed. `benchmark.py` falls
  back to `--target x86_64-pc-windows-gnu` automatically. Do not "fix" toolchain.
- `gcc` (msys2) works: `gcc -O2 -std=c11 -Wall -Wextra` builds C warning-free.
- GOFMT: `& $env:GOROOT\bin\gofmt.exe -w asm.go asm_main.go` (PATH gofmt is stale 1.17).
- git identity: repo-local `williamdoring-prog <williamdoring-prog@users.noreply.github.com>`.
- No `gh` CLI; pushes use Git Credential Manager.

## §I File inventory (state at 2026-11-07 consolidation start)

Root: `ASM_DESIGN.md` (spec, has "Repository layout" section),
`WORKQUEUE.md`, `.gitignore` (excludes the 97 MB
`performance_benchmarking/data/results/experiments.jsonl` — working-tree-only
by design).

`accuracy_benchmarking/`:
- Four impls + entries: `asm.py`, `asm_c.c`+`asm_c.h`+`asm_c_main.c`,
  `asm.rs`+`asm_main.rs`, `asm.go`+`asm_main.go`, `asm_main.py`;
  mains take argv[1]=input file, argv[2]=budget (no args = embedded toy).
- Runners/harness: `benchmark.py` (toy parity), `challenge.py` (sweep + prompt
  files), `check_challenge.py` (adequacy), `challenge-documents/mk_fixture.py`.
- Generated (hash-stable): `asm_fixture.json`, `asm_input.txt` (550 units,
  28,177 words). Committed results: `results/` (5 prompt files, criteria
  checklist, results + adequacy json/md).
- `challenge-documents/`: oracles (`challenge.txt`, PDF + text extract),
  `figure5_events_draft.json` (PROVISIONAL — W1 deferred), `validate_events.py`
  (intentionally failing; known-fail list in §V), 4 keeper images
  (`page_18.png`, `page_18_hi.png`, `figure5_full.png`, `fig5_grid.png`),
  ~81 scratch transcription crops (ACCIDENTALLY TRACKED in the restructure
  commit; untrack in C5 step 1), ft px/`fx_*`/`mc_*` crops same status.
- `README.md` (challenge-harness section done).

`performance_benchmarking/` (absorbed; 79 tracked files, contents assume no
posts before reading): `previous-history.bundle` (history backup — PROTECTED),
`README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `ASM_SPECIFICATION.md`,
`BENCHMARK_PROTOCOL.md`, `DIRECTORY_STRUCTURE.md`, `LANGUAGE_BENCHMARKS.md`,
`PROJECT_PLAN.md`, `WEB_INTERFACE.md`, `WORK_QUEUE.md` (superseded → C3
archive), docs/ (implementation logs + findings including milestone series,
CONTEXT_PRESSURE_PILOT_2026-11-05, CRITERION_EVALUATION_FINDINGS M14,
LANGUAGE_BENCHMARK_FINDINGS series, PROJECT_VERIFICATION M12), benchmarks/
(run_benchmarks.py, standard_suite.py, run_context_pressure.py,
formats/ASM_BENCHMARK_V1.md, fixtures incl. expected_outputs, C/Rust/Go mains),
asm/engine.py, app/ (interface + controller), tests/, data/results jsonls
(experiments.jsonl 97 MB ignored; language_benchmarks.jsonl ~1 MB tracked).

`deploy-package/`: empty (git does not track the empty dir).

## §V Verification commands (run at session start; all commands from `accuracy_benchmarking/`)

- [x] Toy parity (must ALWAYS stay green):
      command: `python benchmark.py`
      pass criteria: Python/C/Rust/Go all `MATCH`, no ERROR rows.
      State 2026-11-07: 4/4 MATCH.
- [x] Transcription validator (INTENTIONALLY failing; W1 deferred — do not
      "fix" without a new directive):
      command: `python challenge-documents\validate_events.py`
      state: exits 1, known-fail list unchanged (1983/1985/1999/2005
      percentages, 2008, zero-years 1981/1984/1987 coverage, count 100 != 99).
- [x] Challenge sweep + adequacy:
      command: `python challenge.py --budgets 150,300,600,1200,2400`
      then `python check_challenge.py`
      state (2026-11-07, final): cross-impl MATCH x4 at every budget;
      adequacy C1 PASS; C2 grows 2/18 -> 9/18 (150 -> 2400 words); C3 FAIL
      (prose chunks carry years outside 1980-2010); C4 0/13 at every budget —
      no figure5/* unit ever selected (2-3 term overlap vs 5-7 for prose).
      This finding motivates the candidate-listing layer amendments (C3).
- Consolidation changes file paths? Update §V/§I/README/ASM_DESIGN in the
  SAME item that moves files, then re-run all three checks before commit.

## §R Locked decisions (do NOT re-derive or re-decide)

Transcription/challenge rules (W1 background):

1. The challenge is a BENCHMARK TEST INPUT, not a task for the agent. Never "answer"
   the challenge question in analysis.
2. Eval scope: retrieval-adequacy only (context contains the facts each criterion
   needs). No LLM in the loop.
3. Fixture content: document text chunks + structured Figure 5 event entries.
4. Context budgets RANGE over small windows; counted in whitespace-delimited
   WORDS (ASCII `[A-Za-z0-9]+` runs), labeled `words`, never `tokens`
   (ASM_DESIGN.md §5.2).
5. All four implementations consume the same input and emit the same JSON shape:
   `{original_source_words, question_words, retrieved_addresses:[], selected:[{address,score}],
   "context":"...", context_words}`.
6. Figure 5 interpretation rules (locked by math cross-check against challenge.txt):
   - "hurricane" = filled red dot with slash; counts in the numerator.
   - Tropical-storm swirl and every other icon type (flood house, fires, storm,
     ice, blizzard, nor'easter, freeze, heat/rain) are denominator-only.
   - Multi-year spans divide cost evenly per year (`1982-83/$2.3` = 1.15/yr,
     `1995-1996/$6.8` = 3.4/yr); denominator = ALL events that year.
7. Math identities the final dataset must reproduce EXACTLY (locked oracle anchors;
   if a planned edit breaks one, the EDIT is wrong, not the identity):
   1983: 6.3/12.8; 1985: 5.4/7.7; 1989: 15.3/17.0; 1991: 2.3/6.2; 1992: 42.7/45.0;
   1995: 7.0/22.0; 1996: 6.6/17.25; 1998: 8.7/27.7; 1999: 7.4/12.2; 2003: 5.6/14.0;
   2004: every 2004 event is a hurricane; 2005: 170.1/171.2; 2008: 58.6% (see X3).
8. Event fragment text form (W2): `Figure 5 event: <type>. Location: <loc>. <year>/
   <years>: cost <cost> billion dollars.` Document chunks keep source prose verbatim.

Consolidation rules (user directive 2026-11-07; §C):

9. **Archive, never silently delete.** Superseded/finished documentation moves
   to `docs/archive/` with a one-line status header added in place of its
   authoritative role. Files marked PRUNE that are regenerable (caches, build
   artifacts, scratch crops) may be removed outright — tracked scratch files
   are UNTRACKED (`git rm --cached`) not deleted, unless physically worthless.
10. **Every prune/merge/archive decision gets an IDEAS_LEDGER.md entry** with
    provenance (where the content lived, why the action, where its value
    survives). Valuable IDEAS are conserved even when their documents are
    archived: the ledger is the index of ideas, not of files.
11. `performance_benchmarking/previous-history.bundle` is PROTECTED — never
    delete; it is the only copy of the predecessor's git history.
12. `performance_benchmarking/data/results/experiments.jsonl` stays
    working-tree-only (root .gitignore); this is deliberate, not an accident.
13. Code is not deleted unless C1/C5 confirmed it unreferenced (grep for
    references incl. docs and tests before marking dead).
14. After ANY file move: update path references in same item (scripts, docs,
    §V/§I here), then run §V before committing.
15. **CLI-only**: no browser/server control interfaces anywhere in the
    package; all configuration via terminal arguments; the predecessor web
    app was pruned on this basis (theme preserved in the history bundle).
16. **Lean tree**: caches and build artifacts stay out of the working tree
    (deleted and regenerated on demand); heavy data stays working-tree-only.
17. **Fast benchmarks**: the default challenge sweep must finish in a few
    minutes total wall time (single pass over the anchor budgets
    150/300/600/1200/2400); repeats stay opt-in (W8), never default.
18. **Utility metric**: benchmark value is measured as retrievable facts
    (adequacy criteria coverage) per context WORD served, at increasing
    stress from small budgets.

## §X Do-not list + deferred transcription notes

Do-not list:

- Do NOT resume W1 transcription (PDF/digit processing) without a new user
  directive; validator stays intentionally failing.
- Do NOT edit oracles (`challenge.txt`, PDF-derived text extract).
- Do NOT invent Figure 5 events to close counts.
- Do NOT delete `previous-history.bundle`, oracle files, or the four keeper
  images; do not untrack them either.
- Do NOT add dependencies (stdlib + pymupdf + PIL only).
- Do NOT run an LLM in the harness (prompt files are the interface to models).

Deferred transcription open questions (decided by pixel crops only — kept as
record; X-question background for a future W1 resumption):

- X1 east-coast stack (~(1990-2200,1340-1470) in figure coords): expect
  `1983 / $4.2` + `1985 / $2.3`; confirm both lines + icon types at >=3x zoom.
- X2 plains severe stack (~860-1180, 1040-1215): confirmed readable
  `1999/$2.0, 2003/$1.8, 2006/$1.0, 2008/$1.1, 2008/$2.4, 2010/$3.0`.
  If BOTH 2008 lines are truly 2008 events, 2008 denominator = 51.7 -> 54.5%
  (breaks the 58.6 oracle). Verify years at 3x; if genuinely `2008/$1.1`+`2008/$2.4`,
  exclude from events and record the discrepancy in `oracle-notes.md`.
- X3 Gulf 2008 cluster (~1080-1560, 1470-1640): Dolly `2008/$1.2` (hurricane) and Ike
  `2008/$27.0` vs `$27.1`. With non-H 2008 = 20.0 (fire 2.0 + mw severe 1.0 +
  drought 2.0 + Iowa flood 15.0), 58.6% needs T = 48.3 -> Ike 27.1 OR Dolly 1.3.
  Read both at >=3x. If truly 27.0/1.2, note the 0.1 rounding difference in
  oracle-notes.md and choose the config that matches the oracle percentage.
- X4 midwest stacks: verify `1993/$30.2, 2008/$15.0, 1999/$1.6, 2001/$2.2, 2002/$1.9,
  2003/$3.8` and the VA-area combined labels `2006/$1.1&1.5` + `2009/$1.0&1.1`
  (each combined label = TWO events) plus separate `2008/$1.0`.
- X5 NE corner (~1900-2420, 430-880): `1998/$1.8` ice storm, `1992/$2.3` nor'easter
  (L icon), `1991/$2.3` hurricane, `1996/$4.0` blizzard, `2006/$1.0`, `2010/$1.5`,
  mid-Atlantic `1998/$1.3` icon identity, coastal stack `1996/$6.6, 1999/$7.4,
  2003/$5.6, 1989/$15.3`.
- X6 FL/Caribbean (~1650-2150, 1470-1800 incl. VI label): `2004/$15.4, 2004/$16.5,
  2004/$9.9, 2004/$7.7, 1992/$40.0, 2005/$17.1` (peninsula), `2005/$133.8`,
  `1995/$2.9` (Virgin Islands), `1998/$7.4` (Georges, arrow), `2005/$2.1`,
  `1994/$1.4` (TS Alberto swirl), `1995/$4.1` (Opal), `2001/$5.6` (Allison swirl),
  `1985/$2.5` + `1985/$2.9` (LA pair, both hurricanes).
- X7 zero-years 1981, 1984, 1987: no events found yet. Sweep gt tiles; if the map
  truly has none for a year, that is a legal 0% (no disasters) — record in
  oracle-notes.md, count unchanged.

---

## §B Blockers

(format: date — what — what would unblock it — owner/approach)

(none)

---

## The Queue

### C1  Curation audit → docs/IDEAS_LEDGER.md
status: in_progress (ledger seeded 2026-11-07 with directive-driven entries:
product directives, ASM-D1..D9 headline ideas, app/ prune + app-position
actions; remaining: classify the rest of both trees by reading)
depends: nothing (predecessor is absorbed and readable)
Read-before-classify audit of BOTH trees; conservation first.
  1. Walk `performance_benchmarking/` and `accuracy_benchmarking/` (docs
     before code). For every substantive file/dir assign exactly one label:
     KEEP (active, authoritative) / ARCHIVE (superseded but historical
     value) / PRUNE (outdated or unused) / MERGE (fold content into another
     doc/file). NEVER classify without reading. Known pointers — verify all
     by reading: predecessor design docs (ARCHITECTURE, ASM_SPECIFICATION,
     BENCHMARK_PROTOCOL, DIRECTORY_STRUCTURE, LANGUAGE_BENCHMARKS,
     PROJECT_PLAN, WEB_INTERFACE, AGENTS, its README/WORK_QUEUE), the
     milestone findings series, CONTEXT_PRESSURE_PILOT,
     CRITERION_EVALUATION_FINDINGS, PROJECT_VERIFICATION, IMPLEMENTATION_LOGs;
     predecessor benchmarks trio + formats/ASM_BENCHMARK_V1.md (.asmbench) +
     fixtures (inputs/expected outputs) + C/Rust/Go benchmark mains;
     asm/engine.py; app/ (web interface: server/controller/system_log/
     storage, interface js/css/html); tests/ (8 test files); accuracy track
     harness + artifacts (all KEEP candidates).
  2. Create `docs/IDEAS_LEDGER.md` at repo root of docs/: (a) IDEA LIST —
     every valuable idea found in either project, one line each with
     provenance and where it now lives; (b) ACTION LIST — per file/dir the
     chosen label + reason + destination; (c) FLAGS — anything uncertain.
  3. Record the consolidation-state baseline in §I of this file is done;
     ledger becomes the moving inventory henceforth.
done-check: docs/IDEAS_LEDGER.md exists; every directory-level entry of both
  trees classified; ≥0 PRUNE items each have a reason; no idea lost (cross-
  check the idea list against the action list).

### C2  Target layout decision (record, then execute in C3..C6)
status: todo
depends: C1
Default (already partially documented in ASM_DESIGN.md "Repository layout"):
  - Directory names stay: `accuracy_benchmarking/`, `performance_benchmarking/`,
    `deploy-package/` (keep user's naming; avoid rename churn).
  - NEW repo-root `docs/`: `IDEAS_LEDGER.md`, `archive/` (superseded docs,
    status headers), `findings-index.md` (chronological, both projects,
    one line each).
  - Root: single README.md (merged entry point), single ASM_DESIGN.md spec.
  - Predecessor root docs AGENTS/ARCHITECTURE/ASM_SPECIFICATION/
    BENCHMARK_PROTOCOL/DIRECTORY_STRUCTURE/LANGUAGE_BENCHMARKS/PROJECT_PLAN/
    WEB_INTERFACE/WORK_QUEUE/README -> docs/archive/ (status headers); any
    still-actionable instruction does not silently die: alive items move
    into this queue's C-items or W-items explicitly.
  - Predecessor internals (benchmarks/, asm/, app/, tests/, data/) stay in
    place; organization inside the tracks, not at their root names.
If C1 shows a materially better layout (e.g. crunching benchmarks/ dirs),
write the deviation here + ASM_DESIGN + user-visible note BEFORE executing.
done-check: layout recorded in queue; deviations documented; user-visible
  note exists for any non-default choice.

### C3  Documentation consolidation (one spec, one README, archive the rest)
status: todo
depends: C1, C2
  1. Root README.md: merge accuracy-track README content (challenge-harness
     section, run commands) + predecessor pointer ("what it contains, how to
     run its benchmark trio, where its findings live (docs/findings-index)").
     One "Consolidated project" intro naming all three dirs.
  2. ASM_DESIGN.md = the ONE specification: reconcile predecessor's
     ASM_SPECIFICATION.md/ARCHITECTURE.md — extract distinctive valuable
     ideas (data model differences, benchmark protocol ideas, interface
     concepts) into ASM_DESIGN with provenance notes, then ARCHIVE the two
     files; APPLY the three pending review amendments to ASM_DESIGN
     (candidate-listing layer; listing token-list cap; `fits_budget` field
     in §6.3) marked "Added in review, 2026-11-07" (W7 leftover — this is
     the empirical answer to the C4=0/13 adequacy finding).
  3. Move superseded docs to docs/archive/ per ledger (status headers);
     predecessor WORK_QUEUE.md gets note "superseded by root WORKQUEUE.md
     consolidation edition"; its still-valid open items if any are dragged
     into this queue explicitly (conservation rule §R10).
  4. docs/findings-index.md: one line per findings/milestone/pilot doc
     (both projects), chronological, with takeaways worth keeping.
done-check: no two root-level docs claim spec authority; all archived files
  have status headers; ledger + findings-index updated; ASM_DESIGN has the
  three amendments.

### C4  Benchmark protocol + entry-point unification (docs-level)
status: todo
depends: C3
  1. Root README gains ONE consolidated "Running the benchmarks" section:
     (a) accuracy parity run: `cd accuracy_benchmarking; python benchmark.py;
     python challenge.py --budgets 150,300,600,1200,2400; python
     check_challenge.py`; (b) performance run: predecessor trio per
     benchmarks docs (verify exact commands while reading, do not guess);
     (c) deploy/package note pointing at deploy-package/ purpose.
  2. Document the relationship of the two benchmark ideas: predecessor's
     context-pressure pilot vs accuracy track's budget sweep + adequacy
     checker cross-reference (same phenomenon, two instruments). If the
     pilot reveals runnable ideas the accuracy harness lacks, list them as
     W-items (conservation, not implementation-by default).
  3. Fixture formats: predecessor `formats/ASM_BENCHMARK_V1.md`(.asmbench)
     vs accuracy `asm_fixture.json`/asm_input line format — document both in
     the README/spec; note adapter scope; only unify if genuinely cheap.
done-check: one consolidated runbook; no contradicting commands; formats
  documented; ledger updated.

### C5  Hygiene prune (untrack scratch, delete regenerables)
status: todo (predecessor app/ already pruned 2026-11-07 via ledger; rest pending)
depends: C1, C2 (ledger decides exact list)
  1. `git rm --cached` ALL scratch transcription crops in
     accuracy_benchmarking/challenge-documents/ (keep the 4 images: page_18,
     page_18_hi, figure5_full, fig5_grid); files remain on disk; extend root
     .gitignore with matching rules for the new path (keep rules anchored to
     `challenge-documents/*.png`+negations, or replace with explicit
     keeper-list approach — pick ONE and make it cover both current paths).
  2. Delete regenerable artifacts: all `__pycache__/` dirs, remaining
     accuracy-track built binaries (asm_c.exe, asm_rust.exe, asm_go.exe —
     rebuilt by `python benchmark.py --build`), any predecessor build
     leftovers listed in ledger. Tracked-and-dead files per ledger (§R13
     grep-confirmed) may be deleted outright.
  3. Keep: oracle files, W1 scratch IMAGES on disk (deferred work), bundle,
     experiments.jsonl (ignored), all KEEP/ARCHIVE ledger items.
done-check: git status clean of scratch; §I updated; §V green; ledger
  reflects every removal.

### C6  Consolidation verification + finish line
status: todo
depends: C3, C4, C5
  1. Re-run full §V (toy parity 4/4; challenge sweep 4/4 MATCH x5 budgets;
     adequacy report unchanged); rebuild binaries once to prove C5 didn't
     break the build.
  2. Update ASM_DESIGN.md "Repository layout" to the FINAL consolidated
     truth (predecessor paragraph: absorbed + consolidated per ledger names);
     fix any straggling path references (grep ASM_DESIGN/README/WORKQUEUE
     for old paths).
  3. Update §I to post-consolidation inventory; record completion date here;
     commit + push.
done-check: §V all green from a cache-less working tree; docs match
  reality; pushed.

### W1  Lock Figure 5 transcription  (DEFERRED — directive stands)
status: deferred (user directive 2026-11-07)
No work. If a future directive resumes it: the §X X1..X7 record + W1 history
contains the full plan (validator target: exits 0 — 13/13 percentages,
18/18 zero-years, count exactly 99; fixture rewrite `figure5_events.json` +
`challenge-documents/oracle-notes.md` with tile-read log and X-resolutions).

### W8  Stretch — after consolidation only
status: stretch
    - Baseline comparison: same sweep on a text-only fixture (event units
      disabled) to quantify the sufficiency drop against criteria 2/4.
    - Multiple repeats with min/median/max per (impl, budget).
    - Candidate-listing layer experiments against the C4=0/13 adequacy
      finding, if the user wants retrieval-layer work after consolidation.

---

## Completed-work record (history; one line each)

- 2026-11-07 Repository restructured by user into accuracy_benchmarking/ +
  performance_benchmarking/ (nested repo) + deploy-package/; layout
  documented in ASM_DESIGN.md; commit 758f13c.
- 2026-11-07 Challenge harness delivered (W2..W6): fixture
  (mk_fixture.py, question-unit amendment), four parameterized mains with
  toy fallback (asm_main.py added; cross-impl MATCH in file mode), budget
  sweep 150/300/600/1200/2400 words with prompt files + criteria checklist
  for local-model testing (user directive), deterministic adequacy checker
  (C2 gains with budget, C4=0/13 headline finding). Commit ec8f0df.
- 2026-11-07 Nested predecessor repo removed by user request; absorbed as
  plain files; history preserved in previous-history.bundle (tracked);
  97 MB experiments.jsonl working-tree-only via .gitignore; ASM_DESIGN
  predecessor section rewritten; scratch-crop untracking discovered as
  restructure fallout and queued (C5).
- 2026-11-07 Product direction (CLI-only, lean, fast, small-window
  performance focus) applied: app/ pruned, per-budget performance table
  added to challenge.py, rules §R15-18 + ledger seeded; commit this one.

## §H Handoff protocol (for the next agent)

1. Read §Q; scan §E/§I; run §V (from `accuracy_benchmarking/`). Do not skip §V.
2. Continue the first `status: todo` item (consolidation: C1 first unless a
   listed `in_progress` exists — finish THAT instead). Read that item fully
   plus §C/rule references it cites; work it one step at a time.
3. §X constraints and §R rules always apply. Conserve ideas (R10); archive
   before delete (R9); after moves, refresh references (R14) and re-run §V.
4. After completing an item: flip its status, append a dated line to the
   Completed-work record, re-run §V, update snapshots, commit + push.
5. If a done-check fails twice: STOP, add a dated entry to §B Blockers with
   what would unblock it, and pick the next todo whose dependencies are met.
