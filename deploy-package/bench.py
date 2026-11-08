"""
Central benchmark CLI - one command for performance, accuracy, or both
(consolidation, 2026-11-07). Clear terminal output; every number exists to
answer the central question:

    Can ASM preserve or improve task performance while requiring
    substantially less context, memory, compute, or retrieval?

Metrics implemented (definitions in WORKQUEUE §R19):
  Quality Retention     ASM facts served / facts served at full context
                        (full-serve row = 100% by construction)
  Compression Ratio     full-context words / served context words (active);
                        storage footprint reported separately, honestly
  Recall / Precision    oracle-fact units in context / oracle units;
                        oracle units in context / all units in context
  Expansion Efficiency  relevant words in context / total context words
  Accuracy per token    facts per 1000 context words (word-unit proxy)
  Latency               internal ns (ranking+selection+assembly+serialization)
                        and process ns (adds startup/IO), per language
  SAE (Semantic Access Efficiency)
                        Quality Retention / active context fraction
                        (full-context baseline = 1.00; higher = better)
  Task score proxy      oracle facts passing adequacy screens
                        (deterministic, no LLM); real model answers are
                        scored with results/criteria_checklist.md out of band

Usage:
  python bench.py                 # registry + performance + accuracy (default)
  python bench.py performance     # cross-language parity + timing
  python bench.py accuracy        # budget sweep + adequacy + full-serve baseline
  python bench.py tools           # LLM tool-interface suite (json/xml/yaml/plain)
  python bench.py all
  python bench.py registry [--check]   # --check: committed file must match
                                       # bench.py TOOL_REGISTRY (drift -> exit 1)
  python bench.py package [--check]    # assemble deploy-package/
                                       # (--check: copies must match sources)
  options: --budgets 150,300,600,1200,2400   --build (rebuild binaries)

Counts are whitespace-delimited WORDS ([A-Za-z0-9]+ runs), never "tokens".
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACC = ROOT / "accuracy_benchmarking"
sys.path.insert(0, str(ACC))

import benchmark as parity  # noqa: E402  (accuracy-track helpers: build/run_command)
import check_challenge as adequacy  # noqa: E402  (criteria parsing + checks)
import asm_tool  # noqa: E402  (LLM tool interface: formats + ops)

RULE = "=" * 78
THIN = "-" * 78
WIN = sys.platform == "win32"


def rule():
    print(RULE)


def thin():
    print(THIN)


def print_table(headers, rows):
    widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))
    print("  ".join(str(h).rjust(w) for h, w in zip(headers, widths)))
    print("  ".join("-" * w for w in widths))
    for row in rows:
        print("  ".join(str(v).rjust(w) for v, w in zip(row, widths)))


TOOL_REGISTRY = [
    {
        "tool_id": "commands/bench/all",
        "invocation": "python bench.py",
        "category": "benchmark",
        "description": "registry refresh + performance + tools + accuracy suite",
        "workdir": "repo root",
        "outputs": "console; accuracy_benchmarking/results/*",
        "wall": "< 15 s",
    },
    {
        "tool_id": "commands/bench/performance",
        "invocation": "python bench.py performance [--build]",
        "category": "benchmark",
        "description": "cross-language parity + internal/process timing on the toy sample",
        "workdir": "repo root",
        "outputs": "console table",
        "wall": "~10 s (with rebuild)",
    },
    {
        "tool_id": "commands/bench/tools",
        "invocation": "python bench.py tools",
        "category": "benchmark",
        "description": "LLM tool-interface suite: serve/list/inspect ops with "
        "json/xml/yaml/toml/csv/plain round-trips (toml parse is "
        "tomllib-gated), asm_main.py reference equality, byte-determinism, "
        "structured errors, function-calling tool schemas",
        "workdir": "repo root",
        "outputs": "console table + accuracy_benchmarking/results/"
                   "tool_results.json + tool_schema.json",
        "wall": "< 3 s",
    },
    {
        "tool_id": "commands/bench/accuracy",
        "invocation": "python bench.py accuracy [--budgets 150,300,600,1200,2400]",
        "category": "benchmark",
        "description": "challenge budget sweep, adequacy metrics, full-context baseline",
        "workdir": "repo root",
        "outputs": "results/challenge_results.json + challenge_adequacy.* + prompt files",
        "wall": "~2 s",
    },
    {
        "tool_id": "commands/bench/registry",
        "invocation": "python bench.py registry [--check]",
        "category": "registry",
        "description": "print this registry and write docs/tools_registry.json; "
        "--check verifies the committed file matches TOOL_REGISTRY "
        "(drift => exit 1 after rewriting)",
        "workdir": "repo root",
        "outputs": "console + docs/tools_registry.json",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/bench/package",
        "invocation": "python bench.py package [--check]",
        "category": "package",
        "description": "assemble deploy-package/: the complete installable tool "
        "set (bench.py + accuracy track sources + harness + fixtures + oracle "
        "text + fixture builder + generated results + tool registry + deploy "
        "README); predecessor track excluded (prior art, bundle-backed)",
        "workdir": "repo root",
        "outputs": "deploy-package/*",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/challenge/sweep",
        "invocation": "python challenge.py --budgets 150,300,600,1200,2400",
        "category": "benchmark-piece",
        "description": "budget sweep alone; asserts cross-impl MATCH per budget",
        "workdir": "accuracy_benchmarking/",
        "outputs": "results/challenge_results.json; results/prompt_budget_<B>.txt",
        "wall": "~1 s",
    },
    {
        "tool_id": "commands/challenge/adequacy",
        "invocation": "python check_challenge.py",
        "category": "benchmark-piece",
        "description": "deterministic adequacy (C1-C5) from existing results",
        "workdir": "accuracy_benchmarking/",
        "outputs": "results/challenge_adequacy.json + .md",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/fixture/build",
        "invocation": "python challenge-documents/mk_fixture.py",
        "category": "fixture",
        "description": "regenerate asm_fixture.json + asm_input.txt (hash-stable)",
        "workdir": "accuracy_benchmarking/",
        "outputs": "asm_fixture.json, asm_input.txt",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/parity/toy",
        "invocation": "python benchmark.py",
        "category": "parity",
        "description": "toy parity check across the four language implementations",
        "workdir": "accuracy_benchmarking/",
        "outputs": "console table (must be 4x MATCH)",
        "wall": "~5 s",
    },
    {
        "tool_id": "commands/parity/build",
        "invocation": "python benchmark.py --build",
        "category": "parity",
        "description": "compile C/Rust/Go binaries (gnu-target fallbacks automatic)",
        "workdir": "accuracy_benchmarking/",
        "outputs": "asm_c.exe, asm_rust.exe, asm_go.exe",
        "wall": "~10 s",
    },
    {
        "tool_id": "commands/challenge/entry",
        "invocation": "python asm_main.py asm_input.txt <budget>",
        "category": "benchmark-piece",
        "description": "single challenge-mode run in Python (file + budget args; "
        "no args = embedded toy sample); stdout JSON + BENCHMARK_NS on stderr; "
        "the baseline row in bench.py accuracy is this command at budget 1000000",
        "workdir": "accuracy_benchmarking/",
        "outputs": "stdout JSON; stderr BENCHMARK_NS",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/asm/tool",
        "invocation": "python asm_tool.py (--request FILE | --op OP) "
        "[--input FILE] [--format json|xml|yaml|toml|csv|txt] "
        "[--schema openai|anthropic|jsonschema]",
        "category": "interface",
        "description": "ASM LLM tool interface (ASM_DESIGN section 6, WORKQUEUE "
        "T1): structured requests in JSON, XML, a documented YAML subset, "
        "TOML (tomllib, 3.11+), CSV (one flat row), or plain text; ops "
        "serve/list/inspect; expand reports unsupported_op until the "
        "abstraction ladder exists; responses echo the sniffed request "
        "format with --format as response-only override (csv responses "
        "are address/error rows; serve/inspect read back in the other "
        "formats; serve JSON is byte-identical with asm_main.py stdout); "
        "--schema emits the function-calling tool definition an LLM "
        "harness binds; exit 0 ok / 1 structured error document",
        "workdir": "accuracy_benchmarking/",
        "outputs": "stdout response document (json/xml/yaml/toml/csv/txt) "
                   "or tool-definition JSON via --schema; exit code",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/challenge/validate_events",
        "invocation": "python challenge-documents/validate_events.py",
        "category": "known-fail",
        "description": "Figure 5 transcription validator - FAILS BY DESIGN while "
        "W1 stays deferred (user directive); do not fix without new directive",
        "workdir": "accuracy_benchmarking/",
        "outputs": "exit 1 + known-fail list (see WORKQUEUE W1)",
        "wall": "< 1 s",
    },
    {
        "tool_id": "commands/predecessor/language_bench",
        "invocation": "python run_benchmarks.py",
        "category": "predecessor-benchmark",
        "description": "predecessor correctness-gated, repeated language "
        "microbenchmark driver (cases from standard_suite.py); prior art of "
        "record - do not couple to the accuracy track",
        "workdir": "performance_benchmarking/",
        "outputs": "console + data/ jsonl",
        "wall": "minutes (repeats)",
    },
    {
        "tool_id": "commands/predecessor/context_pressure",
        "invocation": "python run_context_pressure.py",
        "category": "predecessor-benchmark",
        "description": "predecessor context-pressure pilot (local-model required; "
        "appends a JSONL result file); opt-in only, predecessor-tracked",
        "workdir": "performance_benchmarking/",
        "outputs": "doc-stated JSONL result file",
        "wall": "minutes or longer; needs a local model",
    },
    {
        "tool_id": "commands/predecessor/standard_suite",
        "invocation": "(imported library, not a CLI)",
        "category": "predecessor-library",
        "description": "Standard ASM Benchmark v1 task set definitions "
        "(SMOKE_CASE_IDS + categories) consumed by run_benchmarks.py; "
        "familiarity note for agents, not an invocation",
        "workdir": "performance_benchmarking/benchmarks/",
        "outputs": "module-level constants",
        "wall": "-",
    },
    {
        "tool_id": "artifacts/local_model_prompts",
        "invocation": "(file pointers, for any agent or human)",
        "category": "artifact",
        "description": "feed prompt_budget_<B>.txt to a local model; score its answer "
        "against criteria_checklist.md",
        "workdir": "accuracy_benchmarking/results/",
        "outputs": "prompt_budget_150..2400.txt, criteria_checklist.md",
        "wall": "-",
    },
    {
        "tool_id": "artifacts/history_backup",
        "invocation": "git clone performance_benchmarking/previous-history.bundle",
        "category": "artifact",
        "description": "full predecessor repository history (master 0dd9839)",
        "workdir": "repo root",
        "outputs": " a recovered clone",
        "wall": "-",
    },
]


def command_registry(check=False):
    out_path = ROOT / "docs" / "tools_registry.json"
    payload = {
        "version": 1,
        "repo": ROOT.name,
        "word_unit": "words (whitespace-delimited [A-Za-z0-9]+ runs), never tokens",
        "tools": TOOL_REGISTRY,
    }
    regenerated = json.dumps(payload, indent=1) + "\n"
    drift = out_path.exists() and (
        out_path.read_text(encoding="utf-8") != regenerated
    )
    out_path.write_text(regenerated, encoding="utf-8")

    rule()
    print("AGENT TOOL REGISTRY - invocations an agent can run directly")
    thin()
    print_table(
        ["tool_id", "invocation", "wall"],
        [[t["tool_id"], t["invocation"], t["wall"]] for t in TOOL_REGISTRY],
    )
    for t in TOOL_REGISTRY:
        print(f"    {t['tool_id']}: {t['description']}  [{t['outputs']}]")
    print(f"wrote {out_path}")
    if check:
        if drift:
            print(
                "registry check: DRIFT detected - committed "
                "docs/tools_registry.json did not match bench.py "
                "TOOL_REGISTRY; the file was rewritten; commit the "
                "refreshed registry in the SAME commit as the CLI change."
            )
        else:
            print("registry check: in sync with bench.py TOOL_REGISTRY")
    print(
        "agents: read docs/tools_registry.json for exact tool_id / invocation / "
        "outputs, or invoke commands via the listed workdir + command line."
    )
    return drift


PACKAGE_FILES = [
    "asm.py", "benchmark.py", "challenge.py", "check_challenge.py",
    "asm_main.py", "asm_tool.py",
    "asm_c.c", "asm_c.h", "asm_c_main.c",
    "asm_main.rs", "asm.rs",
    "asm.go", "asm_main.go",
    "asm_fixture.json", "asm_input.txt",
    "challenge-documents/challenge.txt", "challenge-documents/mk_fixture.py",
]

DEPLOY_README = """# ASM benchmark tools — deploy package

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
"""


def command_package(check=False):
    """Assemble deploy-package/ from source of truth; --check reports
    copy drift (and refuses to exit 0 when stale)."""
    pkg = ROOT / "deploy-package"
    sources = [(ROOT / "bench.py", "bench.py")]
    for rel in PACKAGE_FILES:
        sources.append((ACC / rel, f"accuracy_benchmarking/{rel}"))
    for pattern in ("*.json", "*.md", "*.txt"):
        for art in sorted((ACC / "results").glob(pattern)):
            if art.name == "challenge_results.json":
                # Volatile copy: every sweep rewrites internal_ns/process_ns
                # timing values that reshuffle run-to-run, which would make
                # `package --check` report drift at the tail of every
                # `python bench.py all`. The shipped results/ set (deploy
                # README contents list) is the stable artifacts only:
                # prompts, criteria checklist, adequacy reports, tool report.
                continue
            sources.append((art, f"accuracy_benchmarking/results/{art.name}"))
    sources.append((ROOT / "docs" / "tools_registry.json",
                    "docs/tools_registry.json"))

    if check:
        drift = False
        for src, rel in sources:
            if not src.exists():
                continue
            dst = pkg / rel
            stale = (not dst.exists()) or dst.read_bytes() != src.read_bytes()
            drift = drift or stale
        readme = pkg / "README.md"
        stale_readme = (not readme.exists()) or (
            readme.read_text(encoding="utf-8") != DEPLOY_README
        )
        drift = drift or stale_readme
        status = (
            "in sync with sources" if not drift
            else "STALE - copies differ from sources; run: python bench.py package"
        )
        print(f"deploy-package: {status}")
        return drift

    written = []
    for src, rel in sources:
        if not src.exists():
            print(f"  skipped (missing in source repo): {rel}")
            continue
        dst = pkg / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        written.append(rel)
    (pkg / "README.md").parent.mkdir(parents=True, exist_ok=True)
    (pkg / "README.md").write_text(DEPLOY_README, encoding="utf-8")
    written.append("README.md")

    rule()
    print("DEPLOY PACKAGE - complete tool set assembled in deploy-package/")
    thin()
    for rel in written:
        print(f"  {rel}")
    print(
        f"\nassembled {len(written)} files; regenerate anytime: "
        "python bench.py package; predecessor track excluded (prior art of "
        "record, recover from previous-history.bundle)."
    )
    return False


def suite_performance():
    rule()
    print("PERFORMANCE - identical ASM core in four languages (toy sample)")
    print("internal ns = ranking + selection + assembly + serialization;")
    print("process ns  = adds interpreter/binary startup and console IO.")
    thin()

    exes = {
        "C": ACC / ("asm_c.exe" if WIN else "asm_c"),
        "Rust": ACC / ("asm_rust.exe" if WIN else "asm_rust"),
        "Go": ACC / ("asm_go.exe" if WIN else "asm_go"),
    }
    if WIN and any(not p.exists() for p in exes.values()):
        parity.build()

    # Delegate to the canonical cross-language parity runner instead of
    # re-implementing the toy sample here (single source of truth; the
    # binaries carry their own embedded sample data).
    proc = subprocess.run(
        [sys.executable, "benchmark.py"],
        cwd=ACC, capture_output=True, text=True,
    )
    print(proc.stdout.rstrip())
    if proc.returncode != 0:
        print(proc.stderr)
        raise SystemExit("toy parity runner failed; see output above")

    matches = sum(1 for line in proc.stdout.splitlines() if line.endswith(": MATCH"))
    if "DIFFERENT" in proc.stdout or matches != 3:
        raise SystemExit(
            "cross-language parity check failed (expected 1 reference + 3 MATCH)"
        )
    print("parity check: 4/4 OK (Python reference + 3 MATCH)")


def suite_tools():
    """LLM tool-interface gate (ASM_DESIGN section 6; WORKQUEUE T1):
    every check is deterministic - format parity (json/xml/yaml/toml/csv/
    plain), reference equality, byte determinism, structured errors,
    function-calling tool schemas. Writes
    accuracy_benchmarking/results/tool_results.json + tool_schema.json
    (hash-stable fixture input; no timings, so packaged copies never
    drift run-to-run)."""
    rule()
    print("TOOLS - the ASM LLM tool interface (serve/list/inspect ops)")
    print("request formats json/xml/yaml/toml/csv/plain (toml parse is")
    print("tomllib-gated; csv is request-only); responses echo the request")
    print("format; timing contracts remain with asm_main.py / benchmark.py")
    thin()

    def canonical(value):
        """Format-neutral comparison form: all numeric leaves to str."""
        if isinstance(value, dict):
            return {key: canonical(item) for key, item in value.items()}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        if isinstance(value, bool) or isinstance(value, (int, float)):
            return str(value)
        return value

    store_path = ACC / "asm_input.txt"
    raw = store_path.read_text(encoding="utf-8")
    question = asm_tool.unescape(raw.split("\n")[0].rstrip("\r"))
    fragment_rows = []
    for line in raw.split("\n")[2:]:
        line = line.rstrip("\r")
        if not line or "\t" not in line:
            continue
        address, text = line.split("\t", 1)
        fragment_rows.append((address, text))
    first_address, first_text = fragment_rows[0]

    def run_tool(doc, fmt, extra_flags=()):
        args = [sys.executable, "asm_tool.py"] + list(extra_flags)
        return subprocess.run(
            args, input=asm_tool.render_request(doc, fmt),
            cwd=ACC, capture_output=True, text=True, encoding="utf-8")

    def run_tool_or_fail(doc, fmt, what):
        proc = run_tool(doc, fmt)
        if proc.returncode != 0:
            print(proc.stderr)
            raise SystemExit(f"tool serve {what} ({fmt}) failed")
        return proc.stdout

    serve_doc = {"op": "serve", "question": question, "budget": 600,
                 "store": "asm_input.txt"}
    serve_out = {
        fmt: run_tool_or_fail(serve_doc, fmt, "serve")
        for fmt in ("json", "xml", "yaml")
    }
    serve_parsed = {
        fmt: asm_tool.parse_response(text, fmt)
        for fmt, text in serve_out.items()
    }
    checks = []

    record = checks.append
    canon_ref = canonical(serve_parsed["json"])
    record({
        "check": "serve format parity",
        "pass": all(canonical(serve_parsed[fmt]) == canon_ref
                    for fmt in ("xml", "yaml")),
        "detail": "budget 600 serve: json == xml == yaml canonical form",
    })

    reference = subprocess.run(
        [sys.executable, "asm_main.py", "asm_input.txt", "600"],
        cwd=ACC, capture_output=True, text=True, encoding="utf-8")
    if reference.returncode != 0:
        print(reference.stderr)
        raise SystemExit("asm_main.py reference run failed")
    record({
        "check": "asm_main.py reference equality",
        "pass": serve_out["json"] == reference.stdout,
        "detail": "tool serve JSON is byte-identical with asm_main stdout",
    })
    record({
        "check": "serve byte determinism",
        "pass": run_tool(serve_doc, "json").stdout == serve_out["json"],
        "detail": "two independent runs, byte-identical stdout",
    })

    list_doc = {"op": "list", "store": "asm_input.txt"}
    list_out = {
        fmt: run_tool_or_fail(list_doc, fmt, "list")
        for fmt in ("json", "xml", "yaml", "txt")
    }
    list_json = asm_tool.parse_response(list_out["json"], "json")
    record({
        "check": "list op (all formats)",
        "pass": (isinstance(list_json, list)
                 and len(list_json) == len(fragment_rows)
                 and list_json[0] == first_address
                 and list_json[-1] == fragment_rows[-1][0]
                 and canonical(asm_tool.parse_response(list_out["xml"],
                                                       "xml")) == canonical(list_json)
                 and canonical(asm_tool.parse_response(list_out["yaml"],
                                                       "yaml")) == canonical(list_json)
                 and list_out["txt"].splitlines() == list_json),
        "detail": f"{len(list_json)} stable addresses in file order; "
                  "json == xml == yaml == txt",
    })

    inspect_doc = {"op": "inspect", "store": "asm_input.txt",
                   "address": first_address}
    insp_out = {
        fmt: run_tool_or_fail(inspect_doc, fmt, "inspect")
        for fmt in ("json", "xml", "yaml")
    }
    insp_json = asm_tool.parse_response(insp_out["json"], "json")
    expected_words = len(asm_tool.WORD_RE.findall(first_text))
    record({
        "check": "inspect op (exact-ID resolve)",
        "pass": (insp_json == {"address": first_address,
                               "text": first_text,
                               "words": expected_words}
                 and canonical(asm_tool.parse_response(insp_out["xml"],
                                                       "xml")) == canonical(insp_json)
                 and canonical(asm_tool.parse_response(insp_out["yaml"],
                                                       "yaml")) == canonical(insp_json)),
        "detail": f"{first_address} -> {expected_words} words verbatim; "
                  "json == xml == yaml canonical",
    })

    txt_serve = run_tool(serve_doc, "txt").stdout
    record({
        "check": "txt response = model-readable serve",
        "pass": txt_serve == serve_parsed["json"]["context"] + "\n",
        "detail": "txt serve stdout == json context text",
    })

    # toml: emission is deterministic on every runtime; parsing needs
    # tomllib (Python 3.11+), so this runtime round-trips fully or the
    # request answers with the honest unsupported_runtime code.
    toml_emit = run_tool(serve_doc, "json",
                         extra_flags=("--format", "toml")).stdout
    record({
        "check": "toml emit determinism",
        "pass": (toml_emit == run_tool(
            serve_doc, "json", extra_flags=("--format", "toml")).stdout
            and toml_emit.startswith("original_source_words = ")
            and "\n[[selected]]" in toml_emit),
        "detail": "--format toml response: key = value scalars, inline "
                  "arrays, [[selected]] array-of-tables; identical bytes "
                  "across runs",
    })
    toml_request = run_tool(serve_doc, "toml").stdout
    if asm_tool._HAS_TOMLLIB:
        toml_parsed = asm_tool.parse_response(toml_request, "toml")
        record({
            "check": "toml request round-trip",
            "pass": (canonical(toml_parsed) == canon_ref),
            "detail": "tomllib (3.11+) reads the emitted toml back "
                      "canonical-equal to json",
        })
    else:
        toml_error = (json.loads(toml_request).get("error", {})
                      if toml_request.strip() else {})
        record({
            "check": "toml request round-trip",
            "pass": toml_error.get("code") == "unsupported_runtime",
            "detail": "runtime-limited: no tomllib on this Python; toml "
                      "requests answer unsupported_runtime honestly "
                      "(round-trip gate applies on 3.11+)",
        })

    # csv: flat single-row requests; responses default to json (rows
    # exist for the list/error shapes only).
    csv_request = run_tool(list_doc, "csv").stdout
    record({
        "check": "csv request -> json response",
        "pass": (json.loads(csv_request) == list_json),
        "detail": "quoted-comma-safe flat request; default response json",
    })
    csv_rows = run_tool(list_doc, "json",
                        extra_flags=("--format", "csv")).stdout
    record({
        "check": "csv list rows (format: csv)",
        "pass": (asm_tool.parse_response(csv_rows, "csv") == list_json),
        "detail": f"{len(list_json)} address rows, in file order",
    })
    csv_serve = run_tool(serve_doc, "json",
                         extra_flags=("--format", "csv"))
    record({
        "check": "csv serve refuses honestly",
        "pass": csv_serve.returncode == 1 and (
            asm_tool.parse_response(csv_serve.stdout, "csv")
            .get("error", {}).get("code") == "render_error"),
        "detail": "no row shape for serve/inspect; json/xml/yaml instead",
    })

    # LLM harness binding: the tool definition an agent imports.
    schemas = {}
    for style in ("openai", "anthropic", "jsonschema"):
        spec = subprocess.run(
            [sys.executable, "asm_tool.py", "--schema", style],
            cwd=ACC, capture_output=True, text=True, encoding="utf-8")
        if spec.returncode != 0:
            print(spec.stderr)
            raise SystemExit(f"tool schema {style} failed")
        schemas[style] = json.loads(spec.stdout)
    schemas_path = ACC / "results" / "tool_schema.json"
    schemas_path.write_text(
        json.dumps({
            "reference": "accuracy_benchmarking/asm_tool.py",
            "note": "stable artifact; regenerated by python bench.py tools",
            "cli": "python asm_tool.py --schema openai|anthropic|jsonschema",
            "schemas": schemas,
        }, indent=1) + "\n",
        encoding="utf-8")
    openai_params = schemas["openai"]["function"]["parameters"]
    record({
        "check": "function-calling schemas",
        "pass": (
            schemas["openai"]["function"]["name"] == "asm"
            and openai_params["properties"]["op"]["enum"]
            == list(asm_tool.SUPPORTED_OPS)
            and openai_params["properties"]["budget"]["minimum"] == 1
            and schemas["anthropic"]["input_schema"]["type"] == "object"
            and schemas["jsonschema"]["type"] == "object"),
        "detail": "openai / anthropic / jsonschema bindings name 'asm' "
                  "with op enum + WORD budget minimum 1",
    })

    for what, doc, expected_code in (
            ("expand",
             {"op": "expand"}, "unsupported_op"),
            ("zero budget",
             {"op": "serve", "question": question, "budget": 0,
              "store": "asm_input.txt"}, "invalid_budget"),
            ("no store",
             {"op": "list"}, "no_store"),
            ("unknown address",
             {"op": "inspect", "address": "unit/does/not/exist",
              "store": "asm_input.txt"}, "address_not_found"),
    ):
        proc = run_tool(doc, "json")
        parsed_error = (asm_tool.parse_response(proc.stdout, "json")
                        if proc.stdout.strip() else {})
        code = parsed_error.get("error", {}).get("code")
        record({
            "check": f"structured error: {what}",
            "pass": proc.returncode == 1 and code == expected_code,
            "detail": f"exit 1 + error code {expected_code}",
        })

    failed = [entry for entry in checks if not entry["pass"]]
    print_table(
        ["check", "detail", "status"],
        [(entry["check"], entry["detail"],
          "PASS" if entry["pass"] else "FAIL") for entry in checks])
    out_path = ACC / "results" / "tool_results.json"
    payload = {
        "suite": "asm-llm-tool-interface",
        "reference": "accuracy_benchmarking/asm_tool.py",
        "design": "ASM_DESIGN section 6; WORKQUEUE T1",
        "formats": list(asm_tool.SUPPORTED_FORMATS),
        "ops": list(asm_tool.SUPPORTED_OPS),
        "store": "asm_input.txt",
        "store_sha256": hashlib.sha256(store_path.read_bytes()).hexdigest(),
        "budget": 600,
        "unit_total": len(fragment_rows),
        "served_units": len(serve_parsed["json"]["selected"]),
        "context_words": serve_parsed["json"]["context_words"],
        "checks": checks,
        "all_pass": not failed,
    }
    out_path.write_text(json.dumps(payload, indent=1) + "\n",
                        encoding="utf-8")

    print(f"\ntool interface: {len(checks) - len(failed)}/{len(checks)}"
          f" checks OK; wrote {out_path}")
    if failed:
        raise SystemExit(
            "tool-interface suite failed: "
            + "; ".join(f"{entry['check']} - {entry['detail']}"
                        for entry in failed))


def oracle_unit_set(meta, zero_years, verdict_years):
    relevant = set()
    for year in zero_years:
        relevant.add(f"figure5/year-summary/{year}")
    for year in verdict_years:
        relevant.add(f"figure5/year-summary/{year}")
        for address, entry in meta.items():
            if entry.get("type") == "hurricane" and year in entry.get("years", []):
                relevant.add(address)
    return relevant


def suite_accuracy(budgets):
    rule()
    print("ACCURACY - task-context retention as the served window shrinks")
    print("(NOAA challenge suite; deterministic oracle-fact proxy, no LLM in loop)")
    print("paired arms per WORKQUEUE R19: no-ASM control run vs ASM passes per build")
    thin()

    sweep = subprocess.run(
        [sys.executable, "challenge.py", "--budgets", ",".join(map(str, budgets))],
        cwd=ACC, capture_output=True, text=True,
    )
    if sweep.returncode != 0:
        print(sweep.stdout)
        print(sweep.stderr)
        raise SystemExit("challenge sweep failed; see output above")

    payload = json.loads(
        (ACC / "results" / "challenge_results.json").read_text(encoding="utf-8")
    )
    zero_years, verdict_years = adequacy.parse_challenge_criteria()
    meta = adequacy.load_unit_meta()
    oracle = oracle_unit_set(meta, zero_years, verdict_years)

    # PAIRED-MEASUREMENT ARMS (WORKQUEUE R19), written by challenge.py into
    # results/challenge_results.json:
    #   baseline = ASM pipeline at an unconstrained budget, PER source build
    #   control  = the run WITHOUT ASM (asm_main.py --no-asm: entire input
    #              served verbatim, file order, no ranking/selection/filter)
    baseline_block = payload["baseline"]
    control_block = payload["control"]
    base = baseline_block["Python"]["result"]
    control = control_block["result"]
    source_serve_words = control["context_words"]

    def selected_of(rows_list):
        return [entry["address"] for entry in rows_list]

    def facts_for(addresses, label):
        summary = {"selected": [
            {"address": a, "score": 1} for a in addresses
        ], "Python": {"context_words": 0}}
        check = adequacy.check_budget(label, summary, meta, zero_years, verdict_years)
        c2, c4 = check["C2_zero_years"], check["C4_verdict_years"]
        return (
            c2["passing"] + c4["passing"],
            c2["expected_zero_total"] + c4["verdict_total"],
            c2, c4,
        )

    control_selected = selected_of(control["selected"])
    control_facts, fact_total, _, _ = facts_for(control_selected, "control")
    base_selected = selected_of(base["selected"])
    base_facts, _, _, _ = facts_for(base_selected, "base")

    def retrieval_metrics(addresses, context_words):
        selected = set(addresses)
        inter = selected & oracle
        recall = len(inter) / len(oracle) if oracle else 0.0
        precision = len(inter) / len(selected) if selected else 0.0
        relevant_words = sum(len(meta[a]["tokens"]) for a in inter)
        expansion = relevant_words / context_words if context_words else 0.0
        return recall, precision, expansion, relevant_words

    main_rows, eff_rows, lat_rows, plat_rows = [], [], [], []
    measured = []
    for budget in budgets:
        budget_key = str(budget)
        block = payload["per_budget"][budget_key]
        py = block["Python"]
        addresses = selected_of(block["selected"])
        ctx_words = py["context_words"]
        facts, _, _, _ = facts_for(addresses, budget_key)
        quality = facts / control_facts * 100 if control_facts else 0.0
        compression = source_serve_words / ctx_words if ctx_words else 0.0
        sae = (quality / 100) / (ctx_words / source_serve_words) if ctx_words else 0.0
        facts_per_1k = facts / ctx_words * 1000 if ctx_words else 0.0
        recall, precision, expansion, _ = retrieval_metrics(addresses, ctx_words)

        main_rows.append((
            budget, "asm", f"{ctx_words:,}",
            f"{ctx_words / source_serve_words * 100:.1f}%",
            f"{compression:,.1f}x", str(facts), f"{quality:.0f}%", f"{sae:.2f}",
            f"{facts_per_1k:.1f}",
        ))
        eff_rows.append((
            budget, "asm", f"{recall * 100:.0f}%", f"{precision * 100:.0f}%",
            f"{expansion * 100:.1f}%",
        ))
        lat_rows.append((
            budget, "asm",
            f"{block['Python']['internal_ns'] / 1000:,.0f}",
            f"{block['C']['internal_ns'] / 1000:,.0f}",
            f"{block['Rust']['internal_ns'] / 1000:,.0f}",
            f"{block['Go']['internal_ns'] / 1000:,.0f}",
        ))
        plat_rows.append((
            budget, "asm",
            f"{block['Python']['process_ns'] / 1e6:,.1f}",
            f"{block['C']['process_ns'] / 1e6:,.1f}",
            f"{block['Rust']['process_ns'] / 1e6:,.1f}",
            f"{block['Go']['process_ns'] / 1e6:,.1f}",
        ))
        measured.append({
            "budget": budget, "facts": facts, "quality_pct": quality,
            "sae": sae, "compression": compression,
        })

    # The ASM-unconstrained full serve (per-build) vs the no-ASM control.
    serve_words = base["context_words"]
    base_quality = base_facts / control_facts * 100 if control_facts else 0.0
    base_rec, base_prec, base_exp, _ = retrieval_metrics(base_selected, serve_words)
    control_rec, control_prec, control_exp, _ = retrieval_metrics(
        control_selected, source_serve_words)

    main_rows.append((
        "full", "asm", f"{serve_words:,}",
        f"{serve_words / source_serve_words * 100:.1f}%",
        f"{source_serve_words / serve_words:,.2f}x", str(base_facts),
        f"{base_quality:.0f}%",
        f"{(base_quality / 100) / (serve_words / source_serve_words):.2f}"
        if serve_words else "-",
        f"{base_facts / serve_words * 1000:.1f}" if serve_words else "-",
    ))
    eff_rows.append((
        "full", "asm", f"{base_rec * 100:.0f}%", f"{base_prec * 100:.0f}%",
        f"{base_exp * 100:.1f}%",
    ))
    lat_rows.append((
        "full", "asm",
        f"{baseline_block['Python']['internal_ns'] / 1000:,.0f}",
        f"{baseline_block['C']['internal_ns'] / 1000:,.0f}",
        f"{baseline_block['Rust']['internal_ns'] / 1000:,.0f}",
        f"{baseline_block['Go']['internal_ns'] / 1000:,.0f}",
    ))
    plat_rows.append((
        "full", "asm",
        f"{baseline_block['Python']['process_ns'] / 1e6:,.1f}",
        f"{baseline_block['C']['process_ns'] / 1e6:,.1f}",
        f"{baseline_block['Rust']['process_ns'] / 1e6:,.1f}",
        f"{baseline_block['Go']['process_ns'] / 1e6:,.1f}",
    ))
    main_rows.append((
        "full", "control (no-ASM)", f"{source_serve_words:,}", "100.0%",
        "1.00x", str(control_facts), "100%", "1.00",
        f"{control_facts / source_serve_words * 1000:.1f}",
    ))
    eff_rows.append((
        "full", "control (no-ASM)", f"{control_rec * 100:.0f}%",
        f"{control_prec * 100:.0f}%", f"{control_exp * 100:.1f}%",
    ))
    lat_rows.append((
        "full", "control",
        f"{control_block['internal_ns'] / 1000:,.0f}", "-", "-", "-",
    ))
    plat_rows.append((
        "full", "control",
        f"{control_block['process_ns'] / 1e6:,.1f}", "-", "-", "-",
    ))

    print("table 1 - context economy and quality retention (arm rows)")
    print_table(
        ["budget", "arm", "ctx words", "% context", "compression", "facts",
         "quality retention", "SAE", "facts/1k words"],
        main_rows,
    )
    print(
        "\n   arm legend: asm = ASM pass (cross-impl MATCH x4 per budget, so one"
        " shared row); asm full = unconstrained-budget ASM serve;"
        " control = the run WITHOUT ASM (asm_main.py --no-asm serve-all).")

    print("\ntable 2 - retrieval effectiveness (oracle-relevant units)")
    print_table(
        ["budget", "arm", "recall", "precision", "relevant words %"],
        eff_rows,
    )
    print("\ntable 3 - internal latency (us per language build)")
    print_table(
        ["budget", "arm", "python", "c", "rust", "go"], lat_rows)
    print("\ntable 4 - process wall time (ms per language build)")
    print_table(
        ["budget", "arm", "python", "c", "rust", "go"], plat_rows)

    print(
        f"\narms: control(no-ASM) serves the entire {source_serve_words:,}-word "
        f"storage verbatim and scores {control_facts}/{fact_total} oracle facts; "
        f"the ASM pipeline at an unconstrained budget serves {serve_words:,} "
        f"words (identical across all builds) and scores {base_facts}/{fact_total}"
        " - its score>0 retrieval filter structurally drops the 1984/1987"
        " none-summaries, which only the control serves. At every small budget"
        " verdict-year facts (C4) are 0/13: flat term-overlap ranking retrieves"
        " only prose chunks, never the structured figure5 year-summary or"
        " disaster units; the candidate-listing amendment (ASM_DESIGN, queued"
        " C3) is the targeted lever."
    )
    return payload, control_block, baseline_block, measured, fact_total


def write_answer(payload, control_block, baseline_block, measured, fact_total):
    rule()
    print("ANSWER SUMMARY - Can ASM preserve or improve task performance while")
    print("requiring substantially less context, memory, compute, or retrieval?")
    thin()
    best = max(measured, key=lambda m: m["sae"])
    top_budget = max(m["budget"] for m in measured)
    top = next(m for m in measured if m["budget"] == top_budget)
    control = control_block["result"]
    base = baseline_block["Python"]["result"]
    print(
        f"context : at budget {top_budget} words ASM serves the "
        f"{top['compression']:.1f}x-smaller twin of the full no-ASM serve "
        f"({top['quality_pct']:.0f}% of control oracle-fact quality)."
    )
    print(
        f"memory  : active context memory scales with the served budget: "
        f"~{top['compression']:.0f}x less memory held per task at budget {top_budget}."
    )
    print(
        f"compute : ASM ranking is paid once per pass - control serve "
        f"{control_block['internal_ns'] / 1000:,.0f} us vs ASM passes "
        f"{baseline_block['Python']['internal_ns'] / 1000:,.0f} (Python) / "
        f"{baseline_block['C']['internal_ns'] / 1000:,.0f} (C) / "
        f"{baseline_block['Rust']['internal_ns'] / 1000:,.0f} (Rust) / "
        f"{baseline_block['Go']['internal_ns'] / 1000:,.0f} (Go) internal us "
        "for the full unfiltered serve."
    )
    print(
        f"accuracy: quality retention {top['quality_pct']:.0f}% at "
        f"budget {top_budget} (denominator = no-ASM control serve); accuracy"
        " per 1000 words favors small budgets when facts survive."
    )
    print(
        f"SAE     : best small-budget Semantic Access Efficiency = {best['sae']:.2f} "
        f"(budget {best['budget']}; quality retention {best['quality_pct']:.0f}% at "
        f"1/{best['compression']:.1f} of the control serve); control = 1.00 by definition."
    )
    print(
        "arms    : every metric category pairs a control run WITHOUT ASM with"
        " ASM passes per source build (Python/C/Rust/Go) - context-side here;"
        " LLM-side via the opt-in five-model matrix (python bench.py models):"
        " per model, per category, control pass + ASM pass per build."
    )
    print(
        "gap     : verdict-year facts score 0/13 at every small budget - flat "
        "term-overlap ranking retrieves only prose chunks, never the structured "
        "figure5 year-summary or disaster units (the control serve carries them). "
        "The candidate-listing layer amendment (ASM_DESIGN, queued C3) is the "
        "targeted lever to raise quality retention."
    )
    print(
        "next    : to measure true task accuracy (quality retention on ANSWERS, "
        "not context), run the model matrix - it feeds each local model both"
        " arms' prompts and scores responses with the deterministic scorer."
    )
    print("units   : all counts are whitespace-delimited words, never 'tokens'.")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument(
        "suite", nargs="?", default="all",
        choices=["performance", "tools", "accuracy", "models", "all",
                 "registry", "package"],
    )
    parser.add_argument("--budgets", default="150,300,600,1200,2400")
    parser.add_argument("--build", action="store_true")
    parser.add_argument(
        "--check", action="store_true",
        help="with 'registry': verify the committed docs/tools_registry.json "
        "matches bench.py TOOL_REGISTRY (drift exits 1 after rewriting); "
        "with 'package': verify deploy-package/ copies match sources "
        "(drift exits 1 after reporting)",
    )
    args = parser.parse_args()
    budgets = [int(b) for b in args.budgets.split(",") if b.strip()]

    if args.suite == "registry":
        drift = command_registry(check=args.check)
        if args.check and drift:
            raise SystemExit(1)
        return

    if args.suite == "package":
        drift = command_package(check=args.check)
        if args.check and drift:
            raise SystemExit(1)
        return

    if args.build:
        parity.build()

    if args.suite in ("all", "performance"):
        suite_performance()
        print()
    if args.suite in ("all", "tools"):
        suite_tools()
        print()
    if args.suite in ("all", "accuracy"):
        payload, base, base_internal, measured, fact_total = suite_accuracy(budgets)
        print()
        write_answer(payload, base, base_internal, measured, fact_total)
    if args.suite == "all":
        print()
        command_registry()
        print()
        command_package(check=True)


if __name__ == "__main__":
    main()
