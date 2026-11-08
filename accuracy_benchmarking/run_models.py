"""
LLM model-matrix runner (WORKQUEUE paired-measurement rule) - the
opt-in LLM arm of the accuracy track.

For each registered small local model (five popular distinct families,
including Qwen and Granite), for each context budget, it runs:

  - one CONTROL pass: the no-ASM prompt (prompt_control_<B>.txt) - the
    same-size first-N-words serve WITHOUT any retrieval, and
  - one ASM pass per source-code build: the identical ASM-served prompt
    (prompt_budget_<B>.txt) attributed to the Python/C/Rust/Go build
    whose pipeline assembled that context (cross-impl MATCH asserted by
    challenge.py, so the four passes share one prompt text and the
    pass matrix is per build).

Each pass generates one response generation (temperature 0, engine =
Ollama, which must be running locally) and scores it with the
deterministic scorer (score_answers.py - no LLM judge). Each model's
result is a GROUP of metrics: the five challenge categories (C1-C5
deterministic proxies) + response time, per arm (control + per-build
ASM).

Results: results/results_models.json + results/models_matrix.md.
Models that are not pulled locally are reported with their pull command
and SKIPPED - no model download happens from the harness itself.

Usage:
  python run_models.py [--budgets 600] [--builds python,c,rust,go]
                       [--models qwen2.5:1.5b,granite3.3:2b]
"""

import argparse
import json
import math
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
ENGINE_BASE = "http://127.0.0.1:11434"
API_TAGS = f"{ENGINE_BASE}/api/tags"
API_GENERATE = f"{ENGINE_BASE}/api/generate"
# Registered MODEL SUITE (WORKQUEUE R19). Tags resolvable on the local
# engine; aliases let an already-pulled variant stand in for the suite tag.
MODEL_SUITE = json.loads((ROOT / "models_suite.json").read_text(
    encoding="utf-8"))["models"]


def http_json(url, payload=None, timeout=240):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ensure_server():
    """Return the resolved list of pulled model tags; boot `ollama serve`
    in the background when the engine refuses connections."""
    if not engine_alive():
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        for _ in range(30):
            time.sleep(1.0)
            if engine_alive():
                break
        else:
            print("ollama engine did not come up on 127.0.0.1:11434")
            raise SystemExit(1)
    try:
        listing = http_json(API_TAGS, timeout=10)
    except Exception as error:  # engine up but API unreachable
        print(f"ollama API read failed: {error}")
        raise SystemExit(1)
    return [m["name"] for m in listing.get("models", [])]


def engine_alive():
    try:
        http_json(API_TAGS, timeout=2)
        return True
    except Exception:
        return False


def num_ctx_for(words):
    """Context window big enough for the prompt + one bounded response;
    rounded to 512-token steps and capped at 8192 (system: 10 GB GPU)."""
    return min(8192, max(2048, int(math.ceil(words * 1.7 / 512.0)) * 512))


def generate(model_tag, prompt, context_words):
    body = {
        "model": model_tag,
        "prompt": prompt,
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "num_ctx": num_ctx_for(context_words),
            "num_predict": 900,
        },
    }
    start = time.perf_counter_ns()
    payload = http_json(API_GENERATE, body, timeout=300)
    elapsed = time.perf_counter_ns() - start
    return (payload.get("response") or "").strip(), elapsed, None


def passes_to_run(builds_arg):
    order = ["control", "Python", "C", "Rust", "Go"]
    requested = [b.strip().title() if b.lower() != "control" else b.lower()
                 for b in (builds_arg or "control,python,c,rust,go").split(",")]
    return [name for name in order if name in requested or "all" in requested]


def run_suite(budgets, build_names):
    import score_answers

    pulled = ensure_server()
    print(f"ollama engine up; pulled models: {len(pulled)}")

    rows_out = {}
    for suite_entry in MODEL_SUITE:
        tag = suite_entry["tag"]
        aliases = suite_entry.get("aliases", [])
        resolved = next((t for t in [tag, *aliases] if t in pulled), None)
        entry = {
            "vendor": suite_entry["vendor"],
            "requested": tag,
            "resolved": resolved,
        }
        if resolved is None:
            print(f"\nMODEL {tag} ({suite_entry['vendor']}): not pulled - SKIP")
            print(f"          pull with: ollama pull {tag}")
            rows_out[tag] = entry
            continue
        entry["runs"] = {}
        print(f"\nMODEL {resolved} ({suite_entry['vendor']})")
        print("-" * 72)
        for budget in budgets:
            asm_prompt_path = RESULTS_DIR / f"prompt_budget_{budget}.txt"
            control_prompt_path = RESULTS_DIR / f"prompt_control_{budget}.txt"
            if not asm_prompt_path.exists() or not control_prompt_path.exists():
                raise SystemExit(
                    f"missing prompt files for budget {budget}; "
                    "run: python challenge.py")
            asm_words = 0
            for line_text in asm_prompt_path.read_text(encoding="utf-8").splitlines():
                if line_text.startswith("## Context ("):
                    asm_words = int(line_text.split("(")[1].split()[0])
                    break

            for arm in build_names:
                prompt_path = (control_prompt_path if arm == "control"
                               else asm_prompt_path)
                label = f"{arm}@{budget}"
                prompt_text = prompt_path.read_text(encoding="utf-8")
                served_words = asm_words if arm != "control" else budget
                try:
                    response, elapsed, error = generate(
                        resolved, prompt_text, served_words)
                except Exception as err:
                    entry["runs"][label] = {"error": str(err)[:300]}
                    print(f"  {label:<14} ERROR {str(err)[:80]}")
                    continue
                score = score_answers.score_response(
                    response) if response else None
                entry["runs"][label] = {
                    "budget": budget,
                    "served_words": served_words,
                    "response_ms": round(elapsed / 1e6, 1),
                    "response_chars": len(response),
                    "response": response,
                }
                if score is not None:
                    entry["runs"][label]["score"] = score
                print(f"  {label:<14} {entry['runs'][label].get('response_ms', '-'):>7} ms  "
                      f"{score_answers.score_line(score) if score else '(empty response)'}")

    payload = {
        "engine": "ollama",
        "engine_base": ENGINE_BASE,
        "pulled_models": pulled,
        "budgets": budgets,
        "arms": ["control(no-ASM)"] + ["ASM:" + b for b in ("Python", "C", "Rust", "Go")],
        "scorer": "score_answers.py (deterministic; no LLM judge)",
        "models": rows_out,
    }
    out_path = RESULTS_DIR / "results_models.json"
    out_path.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"\nwrote {out_path}")
    write_matrix_markdown(payload)
    return payload


def cell_for(run_entry, category):
    if run_entry is None or "score" not in run_entry:
        return "-" if run_entry is None else "ERR"
    score = run_entry["score"]
    if category == "C1":
        return "PASS" if score["c1_sourcing"]["pass"] else "FAIL"
    if category == "C2":
        return f"{score['c2_zero_years']['score']}/{score['c2_zero_years']['expected']}"
    if category == "C3":
        return "PASS" if score["c3_year_range"]["pass"] else "FAIL"
    if category == "C4":
        return f"{score['c4_verdict_years']['score']}/{score['c4_verdict_years']['expected']}"
    if category == "C5":
        return "PASS" if score["c5_tropical_storm"]["pass"] else "FAIL"
    return "?"


def write_matrix_markdown(payload):
    categories = ["C1", "C2", "C3", "C4", "C5", "time_ms"]
    arms = ["control", "Python", "C", "Rust", "Go"]
    lines = [
        "# LLM model matrix - per-model metric groups (paired arms)",
        "",
        "Arms: control = same-size no-ASM serve (first-words truncation);",
        "Python/C/Rust/Go = the ASM pass from that source build (cross-impl",
        "MATCH asserted, so one shared ASM prompt per budget). Scoring:",
        "deterministic proxies of the five challenge categories.",
        "",
    ]
    for tag, entry in payload["models"].items():
        lines.append(f"## {tag} ({entry['vendor']})")
        lines.append("")
        if "runs" not in entry:
            lines.append(f"SKIP - not pulled. Pull with: `ollama pull {tag}`")
            lines.append("")
            continue
        per_budget = {}
        for label, run_entry in entry["runs"].items():
            if "@" not in label:
                continue
            budget, arm = label.split("@", 1)
            per_budget.setdefault(budget, {})[arm] = run_entry
        for budget, arms_runs in sorted(per_budget.items(), key=lambda kv: int(kv[0])):
            lines.append(f"**budget {budget} words**")
            lines.append("")
            head = "| category | " + " | ".join(f"{a} ASM" if a != "control"
                                                else "control (no-ASM)"
                                                for a in arms) + " |"
            rule = "|---" * (len(arms) + 1) + "|"
            lines.append(head)
            lines.append(rule)
            for category in categories:
                cells = []
                for arm in arms:
                    run_entry = arms_runs.get(arm)
                    if category == "time_ms":
                        cells.append(str(run_entry.get("response_ms", "-"))
                                     if run_entry else "-")
                    else:
                        cells.append(cell_for(run_entry, category))
                lines.append(f"| {category} | " + " | ".join(cells) + " |")
            lines.append("")
        lines.append("")
    path = RESULTS_DIR / "models_matrix.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budgets", default="600",
                        help="comma-separated context-word budgets (model "
                        "passes; keep small so local 4k windows fit)")
    parser.add_argument("--models", default=None,
                        help="comma-separated subset of the registered suite")
    parser.add_argument("--builds", default=None,
                        help="subset: control,python,c,rust,go")
    args = parser.parse_args()
    budgets = [int(b) for b in args.budgets.split(",") if b.strip()]

    build_names = passes_to_run(args.builds)
    if args.models:
        wanted = [m.strip() for m in args.models.split(",")]
        global MODEL_SUITE
        MODEL_SUITE = [e for e in MODEL_SUITE
                       if e["tag"] in wanted or
                       any(a in wanted for a in e.get("aliases", []))]
        if not MODEL_SUITE:
            raise SystemExit(f"no suite model matches {wanted}")

    print(f"model matrix: {len(MODEL_SUITE)} models x {budgets} budgets x"
          f" {len(build_names)} passes [engine ollama]")
    started = time.perf_counter_ns()
    run_suite(budgets, build_names)
    print(f"model matrix wall time: {(time.perf_counter_ns() - started) / 1e9:.0f} s")


if __name__ == "__main__":
    main()
