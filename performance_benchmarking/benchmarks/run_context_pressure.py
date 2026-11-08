"""Run a reproducible local-model context pressure benchmark.

This first benchmark uses a synthetic multi-hop source. It deliberately keeps
the source below the installed model's context limit because the current ASM
semantic compressor submits the entire source and address metadata in one
request. Results are appended to a dedicated JSONL file.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from asm.engine import tokenize  # noqa: E402
from app.controller import server  # noqa: E402
from app.controller.storage import ResultStore  # noqa: E402


FILLER_CLAUSES = (
    "Routine inventory tracking and procedural review continue according to the established schedule",
    "Administrative records preserve the sequence of operations across each reporting interval",
    "Storage checks confirm that ordinary materials remain available for planned handling tasks",
    "Calibration notes document standard maintenance without changing the recorded procedure",
    "Review staff retain the entry to support continuity and routine audit preparation",
    "No operational exception was reported during the ordinary handling and storage cycle",
    "The archive maintains these notes as part of the regular documentation process",
    "Staff follow the standard checklist before closing the daily administrative record",
    "Routine status remains unchanged while the scheduled review window is in progress",
    "The log records normal processing and does not describe a special deployment decision",
)

QUESTION = "What memory is required by the component currently used by Project Orion?"
CRITERIA = [
    "The answer identifies Component Sigma as the component currently used by Project Orion.",
    "The answer states that Component Sigma requires 16 GB of memory.",
    "The answer does not identify superseded Component Delta as the current component.",
]


def build_source(filler_entries: int = 300) -> str:
    """Create a deterministic long source with linked facts at distant offsets."""
    if filler_entries < 30:
        raise ValueError("filler_entries must be at least 30 to separate the evidence")
    entries = [
        f"Archive entry {index:04d} " + "; ".join(FILLER_CLAUSES) + "."
        for index in range(filler_entries)
    ]
    facts = {
        2: "Project Orion was initially assigned Component Delta.",
        filler_entries // 3: "Component Delta was replaced by Component Sigma in the final deployment.",
        (2 * filler_entries) // 3: "Component Delta requires 8 GB of memory; this is a superseded specification.",
        filler_entries - 3: "Component Sigma, the current component assigned to Project Orion, requires 16 GB of memory.",
    }
    for position, fact in facts.items():
        entries[position] = fact
    entries.insert(filler_entries // 2, "Project Orion-2 uses Component Kappa, which requires 64 GB of memory.")
    return " ".join(entries)


def run(args: argparse.Namespace) -> int:
    source = build_source(args.filler_entries)
    source_tokens = len(tokenize(source))
    invalid = [budget for budget in args.budgets if budget >= source_tokens]
    if invalid:
        raise ValueError(f"every context budget must be below source size ({source_tokens} tokens); invalid: {invalid}")
    model_versions = server.model_catalog()
    if args.model not in model_versions:
        raise ValueError(f"model {args.model!r} is not installed in the local Ollama catalog")

    output_path = (ROOT / args.output).resolve()
    server.RESULTS = ResultStore(output_path)
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    print(f"Source: {source_tokens} ASM word/punctuation tokens; sha256={source_hash}")
    print(f"Model: {args.model}; version={model_versions[args.model]}")
    print(f"Budgets: {args.budgets}; repetitions per strategy and budget: {args.repeats}")
    print(f"Append-only output: {output_path}")

    for budget in args.budgets:
        print(f"Running context budget {budget}...")
        comparison = server.execute_comparison({
            "source": source,
            "question": QUESTION,
            "criteria": CRITERIA,
            "expected_answer": "16 GB",
            "category": "synthetic-context-pressure-multihop",
            "context_budget": budget,
            "repeat_count": args.repeats,
            "run_model": True,
            "model": args.model,
            "evaluation_model": args.model,
            "expand_sources": True,
        })
        runs = comparison["runs"]
        completed = sum(1 for item in runs if item.get("response") is not None and not item.get("error"))
        exact = sum(1 for item in runs if isinstance(item.get("evaluation"), dict)
                    and item["evaluation"].get("exact_match") is True)
        judged = [item.get("criterion_evaluation", {}).get("pass_percentage") for item in runs]
        judged = [score for score in judged if score is not None]
        print(f"  {completed}/{len(runs)} answered; exact-match {exact}/{len(runs)}; "
              f"criterion scores available {len(judged)}/{len(runs)}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument("--budgets", nargs="+", type=int, default=[512, 1024, 2048, 4096, 8192])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--filler-entries", type=int, default=100)
    parser.add_argument("--output", default="data/results/context_pressure_2026-11-05.jsonl")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 20:
        parser.error("--repeats must be from 1 through 20")
    return args


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
