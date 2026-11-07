# WORK QUEUE — asm_multilang_benchmark

Purpose: single continuation document so any agent (including small local models with
tiny context windows) can resume development across handoffs. Read §Q (quick state),
then work the first `status: todo` item top-down. One item at a time.

Repo: https://github.com/williamdoring-prog/addressable_semantic_memory

---

## §Q Quick state (read this first; ~340 words)

Project: benchmark of equivalent deterministic "ASM retrieval + bounded context
assembly" implementations in Python, C, Rust, Go. All four currently build and
produce byte-identical results on a toy sample (verified end of review phase).
New work: feed a real document challenge (NOAA report + Figure 5 map
transcription) and measure retrieval adequacy across a **range of small context
windows** (budget sweep — user requirement, in progress).

Status (after 2026-11-07 session; see queue for details):

USER DIRECTIVE (2026-11-07): stop processing the challenge document/PDF for
transcription purposes. Build the benchmark that tests local models with the
question prompt and the criteria. Figure 5 digit work is deferred; the
existing draft event list ships as a PROVISIONAL fixture.

1. **Figure 5 transcription (W1)** — DEFERRED by directive. The draft JSON
   with `_flag` notes is the fixture source as-is; `validate_events.py`
   intentionally still exits 1 (known-fail list in §V). Do NOT resume digit
   work unless the directive is lifted.
2. **Challenge harness (W2..W6)** — DONE. mk_fixture.py -> fixture; four
   parameterized mains (toy fallback intact); challenge.py budget sweep
   (150/300/600/1200/2400 words) with cross-impl MATCH at every budget;
   prompt files + criteria checklist for local-model testing; deterministic
   adequacy checker. See §V for the snapshot and W6 notes for findings.

Ground rules a resumed agent must not violate: see §R (rules) and §X (do-not).
If unsure which item you were working on: re-run §V (verification) commands and
continue at the first `todo`.

---

## §E Environment facts (Windows machine, PowerShell)

- Repo root: `C:\Users\willi\Projects\asm_multilang_benchmark`
- Python 3.10 at `python` (site-packages: pymupdf installed, PIL installed; no pypdf).
- `go` on PATH is STALE (msys2 Go 1.17). Use `& $env:GOROOT\bin\go.exe` for builds
  and formatting. `benchmark.py` already handles this automatically.
- `rustc` (MSVC host) lacks link.exe; gnu target installed. `benchmark.py` falls
  back to `--target x86_64-pc-windows-gnu` automatically. Do not "fix" toolchain.
- `gcc` (msys2) works: `gcc -O2 -std=c11 -Wall -Wextra` builds C warning-free.
- GOFMT: `& $env:GOROOT\bin\gofmt.exe -w asm.go asm_main.go` (PATH gofmt is stale 1.17).
- git identity: repo-local `williamdoring-prog <williamdoring-prog@users.noreply.github.com>`.
- No `gh` CLI; pushes use Git Credential Manager.

## §I File inventory

- Core impls (all verified MATCH on toy sample): `asm.py`, `asm_c.c`+`asm_c.h`+`asm_c_main.c`,
  `asm.rs`+`asm_main.rs`, `asm.go`+`asm_main.go`, runner `benchmark.py`,
  challenge harness `challenge.py`, `check_challenge.py`, CLI entry
  `asm_main.py` (2026-11-07), `README.md`,
  `ASM_DESIGN.md` (design spec for the real system; reviewed 2026-11-07, see W7),
  `.gitignore`.
  Mains take argv[1]=input file, argv[2]=budget (W4); no args = embedded toy.
  Generated (hash-stable, rerun mk_fixture.py to refresh): `asm_fixture.json`,
  `asm_input.txt`. Results artifacts (committed): `results/`.
- Challenge dir `challenge-documents/`:
  - ORACLES (never modify): `challenge.txt` (question + 5 criteria),
    `noaaTechnicalReport.pdf`/`noaTechnicalReport.txt` (source doc; fig5 caption at
    text line ~501; figure is 0-indexed PDF page 18 / printed page 15).
  - `figure5_events_draft.json` — transcription WIP with `_flag` notes. Inconsistent in
    known ways; W1 fixes it. Editing allowed.
  - `validate_events.py` — transcription validator (runs vs. challenge.txt). Keep in sync.
  - Working images KEEP: `page_18.png`, `page_18_hi.png`, `figure5_full.png` (2420x1800
    crop of the figure at 400 dpi), `fig5_grid.png` (same crop + 200px blue grid +
    magenta pixel-coordinate labels — USE IT to locate crops; displayed renders are
    downscaled ~0.83x, so eyeballed coordinates drift).
  - Everything else matching `fig5*.png` / `gt_*.png` / `z_*.png` in that dir is a
    scratch crop; safe to delete ONLY after W1 passes (W7).

## §V Verification commands (run at session start)

- [x] Toy parity (must ALWAYS stay green):
      command: `python benchmark.py`
      pass criteria: Python/C/Rust/Go all `MATCH`, no ERROR rows.
- [x] Transcription validator (INTENTIONALLY failing after the 2026-11-07
      user directive; W1 deferred — do not "fix" without a new directive):
      command: `python challenge-documents\validate_events.py`
      state: exits 1, same known-fail list as before (1983/1985/1999/2005
      percentages, 2008, zero-years 1981/1984/1987 coverage, count 100 != 99).
- [x] Challenge sweep + adequacy:
      command: `python challenge.py --budgets 150,300,600,1200,2400`
      then `python check_challenge.py`
      state at handoff (2026-11-07, final): cross-impl MATCH x4 at every
      budget; adequacy: C1 PASS all budgets; C2 grows 2/18 -> 9/18
      (150 -> 2400 words); C3 FAIL (prose chunks carry years outside
      1980-2010, e.g. climate-normal periods); C4 0/13 at every budget —
      no structured figure5/* unit is ever selected because its match
      vocabulary (hurricane/cost/billion, score 2-3) loses to prose chunks
      (score 5-7). This is the headline finding and the motivation for the
      ASM_DESIGN amendments queued in W7 (candidate-listing layer).

## §R Locked decisions (do NOT re-derive or re-decide)

1. The challenge is a BENCHMARK TEST INPUT, not a task for the agent. Never "answer"
   the challenge question in analysis.
2. Eval scope: retrieval-adequacy only (context contains the facts each criterion
   needs). No LLM in the loop.
3. Fixture content: document text chunks + structured Figure 5 event entries.
4. Budget sweep over a RANGE of small context windows (user requirement). Windows are
   counted in whitespace-delimited WORDS (ASCII `[A-Za-z0-9]+` runs), labeled `words`,
   never `tokens` (ASM_DESIGN.md §5.2: never present word counts as tokenizer counts).
5. All four implementations consume the same input and emit the same JSON shape:
   `{original_source_words, question_words, retrieved_addresses:[], selected:[{address,score}],
   "context":"...", context_words}` — already implemented on the toy sample.
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

## §X Do-not list + open questions

- Do NOT add new dependencies (stdlib + pymupdf + PIL only).
- Do NOT delete oracles, `page_18*.png`, `figure5_full.png`, `fig5_grid.png`, `gt_*.png`.
- Do NOT invent events to close the count. Every event exists only if read on the map.
- Do NOT edit `challenge.txt` or the PDF-derived text extract.

Open questions (decided by digit-level crops only, never by outside inference):

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

## The Queue

### W1  Lock Figure 5 transcription
status: deferred (user directive 2026-11-07 — no PDF/digit processing)
depends: nothing
inputs: gt_*.png tiles + figure5_full.png; `figure5_events_draft.json`
steps:
  1. Read remaining unread tiles: gt_22, gt_23, gt_12, gt_02, gt_10, gt_20, gt_01, gt_00.
  2. Make >=3x LANCZOS micro-crops for X1..X6; read crops one at a time; record
     digits verbatim, defer inference.
  3. Apply draft edits (adjust per crop findings):
     a. REMOVE hypothesis/dup entries: e85 (1985/$15.4 is a misread), e98 (2005/$1.0
        guess), e99 (2004/$8.1 guess), e100 (2010/$2.0 dup of e21).
     b. ADD: {1983, 4.2, <icon>}, {1985, 2.3, <icon>} (X1) and any confirmed plains
        stack events per X2.
     c. FIX: e23 years -> [2000]; e24 cost -> 1.1; e09/e10 location ->
        northern_rockies; e61 type -> ice_storm (rain-cloud icon); e42 type ->
        heat_wave_drought (thermometer+sun icon); e43 type per crop (cost stays 9.5).
     d. Hawaii: exactly one event, e84 1992/$2.7 HURRICANE (hollow circle + dots are
        island outlines, verified in gt_21).
  4. Run validator (§V) -> must exit 0.
  5. Write final `figure5_events.json` (same schema, no `_flag` fields), then create
     `challenge-documents/oracle-notes.md` with: tile-read log, X-question resolutions,
     history (one line per completed item), BLOCKERS section, and the STATE snapshot
     (validator output summary).
done-check: validator exits 0; `figure5_events.json` + `oracle-notes.md` exist.

### W2  Build ASM fixture from report text + Figure 5 events
status: done 2026-11-07 (`challenge-documents/mk_fixture.py`; outputs
`asm_fixture.json` + `asm_input.txt`, rerun hash-stable; 550 units,
28,177 words). AMENDMENT vs original spec: the challenge question is NOT a
memory unit (it echoes into context at score 39) — it stays in asm_input.txt
line 1 only; see mk_fixture.py docstring.
depends: (W1 deferred by directive — draft events used as-is)
Create `challenge-documents/mk_fixture.py`:
  1. Chunk `noaTechnicalReport.txt`: split on blank lines; merge blocks to ~55-80
     whitespace-words; ids `doc/chunk/0001`...
  2. Event units from `figure5_events.json`: per event address
     `figure5/disaster/<year|yearspan>/<NN>` text per §R8; plus per-year aggregate
     units `figure5/year-summary/<year>` (comma-joined `<type> <cost> billion` list).
  3. Question unit `challenge/question` = challenge.txt line 1 minus `#question:`.
  4. Deterministic ordering: doc chunks, then events sorted by address.
  5. Emit `asm_fixture.json` (array of {address, text}) AND `asm_input.txt` (W4
     line format). Generated artifacts; never hand-edit.
done-check: running twice yields identical bytes (hash compare); report unit count
  and total words.

### W3  Budget sweep design (user requirement: range of small context windows)
status: done 2026-11-07 (anchors 150/300/600/1200/2400 implemented in
challenge.py; per-(impl,budget) context hash/counts/timing recorded in
results/challenge_results.json)
depends: W2
Sweep anchors: 150, 300, 600, 1200, 2400 words. 150 forces severe selection
pressure (Figure 5 events must compete); 2400 admits most of the document.
Record per (impl, budget): context hash, context_words, retrieved count, selected
count, internal_ns, process_ns, cross-impl MATCH. Lives in the runner (W5).

### W4  Parameterize the four mains (fixture input + budget CLI)
status: done 2026-11-07 (`asm_main.py` added; file modes added to
asm_c_main.c / asm_main.rs / asm_main.go: argv[1]=input, argv[2]=budget
optional, line-2 default; parse OUTSIDE timed section; toy fallback byte-
identical — `python benchmark.py` remains 4/4 MATCH; file-mode smoke test
Python/C/Rust/Go all MATCH at budgets 150 and 600)
depends: W2
LINE FORMAT (locked; no JSON parsing needed in C):
  `asm_input.txt` line 1 = question (single line, literal `\t`/`\n` escapes);
  line 2 = budget (integer words); lines 3..N = `<address>\t<text>` (one per unit).
Behavior: each main takes OPTIONAL argv[1] = input file, argv[2] = budget; with no
args keeps the embedded toy sample so `python benchmark.py` stays green (regression
guarantee). Input parsing happens OUTSIDE the timed section; algorithm +
serialization stay INSIDE (uniform scope across languages).
done-check: `python benchmark.py --build` + `python benchmark.py` all MATCH on toy;
and a fixture-input smoke test where each compiled impl run with
`asm_input.txt <budget>` yields identical results to asm.py on the same input.

### W5  Challenge runner
status: done 2026-11-07 (`challenge.py`; per-budget cross-impl MATCH asserts,
results/challenge_results.json + per-budget console table). USER-DIRECTIVE
ADDITION: writes `results/prompt_budget_<B>.txt` (question + bounded
context for testing local models directly — feed a prompt file to a local
model, score the response with `results/criteria_checklist.md`, which holds
the five criteria verbatim) and no LLM is invoked by the harness.
depends: W3, W4
New `challenge.py`:
  1. Reuse benchmark.py build().
  2. Generate asm_input.txt per budget (same fragments; only line 2 changes).
  3. Run all four impls x budgets; per-budget cross-impl MATCH assert (parse JSON
     canonically; compare context string). MISMATCH aborts with impl+budget shown.
  4. Write `results/challenge_results.json`; print per-budget table
     (impl / context_words / retrieved / selected / internal_ns / process_ns).
done-check: `python challenge.py --budgets 150,300,600,1200,2400` completes; all
  impls match at every budget; artifacts written.

### W6  Retrieval-adequacy checker
status: done 2026-11-07 (`check_challenge.py`; emits
results/challenge_adequacy.json + .md). Verified from challenge_results.json
only, no rerun. FINDINGS (see §V): C1 PASS everywhere; C2 grows with budget
(2/18 -> 9/18); C3 FAIL — generic prose chunk years (1870-1960 normals,
2011-2050 scenario horizons) enter context; C4 0/13 — flat term-overlap
scoring never selects figure5/* units (their 2-3 matching terms lose to
prose chunks with 5-7). Improving C4 needs the ASM_DESIGN candidate-listing
layer (W7 amendments), not a harness change.
depends: W5
New `check_challenge.py` (reads challenge_results.json; no re-run needed). Parse
challenge.txt criteria; per (impl, budget) verdicts:
  - C2 zero-years: PASS iff for every zero-year the context contains a unit
    mentioning that year AND no unit dates a hurricane event to that year
    (deterministic adjacency scan; heuristic documented in-script).
  - C4 percentages: per verdict year, context must contain the year's total-cost
    facts and its hurricane-cost facts. Report which years each budget loses.
  - C1: context-scope note + verify all `selected` addresses are figure5/* or
    doc/chunk/*; verdict label "response-side; out of retrieval-adequacy scope".
  - C3: every year token appearing in context must be within 1980..2010.
  - C5: response-side N/A; context-side note that TS-only events exist and are
    retrievable (they may be excluded by the responder, not the assembler).
Emit `results/challenge_adequacy.json` + per-budget markdown table.
done-check: runs from existing results; prints per-impl adequacy summary.

### W7  Final consistency pass
status: partially done 2026-11-07 (README challenge-harness section added;
WORKQUEUE statuses updated; harness committed+pushed. Remaining:
ASM_DESIGN.md review amendments + scratch-crop cleanup)
depends: W6
 1. README: challenge-harness section — DONE 2026-11-07.
 2. ASM_DESIGN.md: still TO-DO — append the three review amendments
    (candidate-listing layer; listing token-list cap; `fits_budget` field in
    §6.3) marked "Added in review, 2026-11-07" — do not rewrite the file.
    PRIORITY RAISED: the W6 C4=0/13 finding is the empirical motivation.
 3. Scratch-crop cleanup per §I — still TO-DO (crops kept on disk).
 4. Full §V green on benchmark.py + challenge commands; update statuses here,
    commit. — DONE 2026-11-07 (results artifacts also committed).

### W8  Stretch (only after W7)
- Baseline comparison: same sweep on a text-only fixture (event units disabled) to
  quantify the sufficiency drop against criteria 2/4 (ASM_DESIGN §12 baseline).
- Multiple repeats with min/median/max per (impl, budget).

---

## §H Handoff protocol (for the next agent)

1. Read §Q; scan §E/§I; run §V. Do not skip §V.
2. Continue the `in_progress` item if present, else first `todo`. Read that item,
   its dependencies, and the relevant §R rules. Ignore the rest.
3. §X constraints always apply. If a done-check fails twice: STOP, add a dated line
   to `challenge-documents/oracle-notes.md` under BLOCKERS, then pick the next todo
   whose dependencies are green.
4. After completing an item: flip its status here, append a one-line history entry
   to oracle-notes.md, re-run §V, update §V's snapshot if it changed.
5. Never mark anything `blocked` without an entry in BLOCKERS explaining why and
   what would unblock it.
