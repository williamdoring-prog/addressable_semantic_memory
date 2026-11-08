# ASM benchmark tools — deploy package

Complete, generally usable deployment of the benchmark tool set, assembled
by `python bench.py package` from the source repository (this directory's
README is generated; never hand-edit copies — refresh with
`python bench.py package`). Rule: WORKQUEUE section R21.

## Install & use

Requirements:
- Python 3.10+ (stdlib only) — enough to run the accuracy suite.
- Optional: a C11 compiler (gcc works), rustc, and go for the C/Rust/Go
  parity builds. Notes: on Windows the MSVC rust host needs Visual Studio
  Build Tools; without it the runner falls back to the standard
  x86_64-pc-windows-gnu target automatically. The Go binary must match
  GOROOT (the runner picks `$GOROOT/bin/go` when present).

Commands (run from THIS directory):

```text
python bench.py all          # registry refresh + parity + tools + accuracy + baseline
python bench.py performance  # cross-language parity + timing only
python bench.py tools        # LLM tool-interface suite (json/xml/yaml/toml/
                             # csv/plain ops + tool schemas)
python bench.py accuracy     # budget sweep + adequacy + full-serve baseline
python bench.py registry     # print + write docs/tools_registry.json
python bench.py registry --check   # committed registry must match the CLI
python bench.py package --check    # copies in this directory must match sources
```

`--build` on the performance suite compiles the C/Rust/Go binaries first
(deploy copies of the sources live in `accuracy_benchmarking/`; binaries
are generated, not shipped).

## Contents

- `bench.py` — the central CLI (single entry point for all suites).
- `accuracy_benchmarking/` — four equivalent deterministic ASM
  implementations (Python/C/Rust/Go sources), the challenge harness
  (`challenge.py`, `check_challenge.py`, single-run entry `asm_main.py`),
  the LLM tool interface (`asm_tool.py`: `serve`/`list`/`inspect` ops over
  JSON, XML, a documented YAML subset, TOML (tomllib-gated, Python
  3.11+), one-flat-row CSV, or plain-text requests; responses echo the
  request format, csv responses are address/error rows; `--schema`
  emits the OpenAI/Anthropic/JSON-Schema function-calling tool
  definition; `expand` reports `unsupported_op` until the abstraction
  ladder exists — ASM_DESIGN section 6), the hash-stable
  fixture (`asm_fixture.json`, `asm_input.txt`), the challenge oracle
  text + fixture builder (`challenge-documents/challenge.txt`,
  `challenge-documents/mk_fixture.py`), and the committed `results/`
  artifacts (per-budget model prompts, criteria checklist, adequacy
  reports, tool-interface report + committed tool-definition schemas).
- `docs/tools_registry.json` — machine-readable agent tool registry
  (same list as the source repository's registry; regenerated here by
  `python bench.py registry`, where repo = this package).

Not included: the predecessor performance track (prior art of record;
the former web app and its history recover via
`git clone performance_benchmarking/previous-history.bundle` in the
source repository) and the Figure-5 transcription validator, which
fails by design while work item W1 stays deferred.

## Measuring

Every printed number answers: "Can ASM preserve or improve task
performance while requiring substantially less context, memory, compute,
or retrieval?" Context budgets are ranges of small windows counted in
whitespace-delimited WORDS (`[A-Za-z0-9]+` runs), never tokens. The
metric framework (Quality Retention, active-vs-storage compression,
recall/precision/efficiency, accuracy per 1000 words, latency split,
SAE with a 1.00 full-context baseline) is defined once in the source
repository's `WORKQUEUE.md` section R19. The harness runs no LLM: feed
`accuracy_benchmarking/results/prompt_budget_<B>.txt` to any local model
and score with `criteria_checklist.md`, out of band.
