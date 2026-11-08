"""
Retrieval-adequacy checker (WORKQUEUE W6). Reads results/challenge_results.json
(written by challenge.py) plus the fixture and challenge-documents/challenge.txt
— no re-run needed. No LLM in the loop; responses are scored elsewhere using
results/criteria_checklist.md.

Because challenge.py asserts full cross-implementation MATCH per budget, all
implementations share one context per budget; adequacy is therefore computed
per budget and labeled with the implementation set.

Checks (criterion semantics, deterministic):
  C1 source scope: every selected address is challenge/question, doc/chunk/*,
     figure5/disaster/*, or figure5/year-summary/*. Response-side
     interpretation ("response should derive its answer exclusively from the
     provided PDF") is out of retrieval-adequacy scope; the check reports the
     context-side fact.
  C2 zero-hurricane-share years: for each oracle zero-year, the context must
     contain at least one unit mentioning that year AND no selected
     hurricane-typed disaster unit spanning that year.
  C3 year-range: every 4-digit year token appearing in the context must be
     within 1980-2010.
  C4 verdict years (with percentages): for each oracle verdict year the
     context must contain BOTH the year-summary unit and at least one
     hurricane-typed disaster unit covering that year (the responder still
     has to do the arithmetic).
  C5 tropical-storm relevance: response-side N/A. Context-side note: the
     assembler serves tropical-storm units exactly like any other unit and a
     criterion tells the responder to exclude them from the answer.

Outputs:
  results/challenge_adequacy.json
  results/challenge_adequacy.md   (per-budget table)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
WORD_RE = re.compile(r"[A-Za-z0-9]+")
EVENT_RE = re.compile(r"^Figure 5 event: ([a-z_]+)\.")

ZERO_YEAR_HINT = "accounted for 0% of total disaster costs:"
VERDICT_HINT = "total disaster costs from hurricanes:"


def parse_challenge_criteria():
    text = (ROOT / "challenge-documents" / "challenge.txt").read_text(encoding="utf-8")
    zero_years = []
    verdict_years = []
    for line in text.splitlines():
        if ZERO_YEAR_HINT in line:
            zero_years = re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", line)
        elif VERDICT_HINT in line:
            verdict_years = sorted(set(re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", line)))
    return zero_years, verdict_years


def load_unit_meta():
    """address -> {type, years, tokens} for event/summary/question units."""
    units = json.loads((ROOT / "asm_fixture.json").read_text(encoding="utf-8"))
    meta = {}
    for unit in units:
        address = unit["address"]
        entry = {"address": address, "tokens": set(WORD_RE.findall(unit["text"]))}
        match = EVENT_RE.match(unit["text"])
        if match:
            entry["type"] = match.group(1)
            years_part = address.split("/")[2]
            if "-" in years_part:
                first, last = years_part.split("-")
                entry["years"] = list(range(int(first), int(last) + 1))
            else:
                entry["years"] = [int(years_part)]
        if address.startswith("figure5/year-summary/"):
            entry["type"] = "year_summary"
            entry["years"] = [int(address.rsplit("/", 1)[1])]
        meta[address] = entry
    return meta


def check_budget(budget_key, summary, meta, zero_years, verdict_years):
    selected = summary["selected"]
    addresses = [entry["address"] for entry in selected]
    selected_meta = [meta[a] for a in addresses if a in meta]

    context_tokens = set()
    for entry in selected_meta:
        context_tokens |= entry["tokens"]

    # C1: address scope
    scope_ok = all(
        a == "challenge/question"
        or a.startswith("doc/chunk/")
        or a.startswith("figure5/disaster/")
        or a.startswith("figure5/year-summary/")
        for a in addresses
    )

    # C2: zero-hurricane-share years
    hurricane_years = set()
    for entry in selected_meta:
        if entry.get("type") == "hurricane":
            hurricane_years |= set(entry.get("years", []))
    zero_report = []
    for year in zero_years:
        year_token = year
        mentioned = year_token in context_tokens
        hurricanes = int(year) in hurricane_years
        zero_report.append(
            {"year": year, "mentioned": mentioned, "hurricanes": hurricanes,
             "pass": mentioned and not hurricanes}
        )

    # C3: year-range tokens in context
    stray = sorted(
        t for t in context_tokens
        if t.isdigit() and len(t) == 4 and not (1980 <= int(t) <= 2010)
    )

    # C4: verdict years need summary + hurricane facts
    verdict_report = []
    for year in verdict_years:
        has_summary = f"figure5/year-summary/{year}" in addresses
        has_hurricane = any(
            entry.get("type") == "hurricane" and int(year) in entry.get("years", [])
            for entry in selected_meta
        )
        verdict_report.append(
            {"year": year, "summary": has_summary, "hurricane_event": has_hurricane,
             "pass": has_summary and has_hurricane}
        )

    ts_count = sum(1 for entry in selected_meta if entry.get("type") == "tropical_storm")

    return {
        "budget": int(budget_key),
        "context_words": summary["Python"]["context_words"],
        "selected": len(addresses),
        "C1_address_scope": scope_ok,
        "C2_zero_years": {
            "expected_zero_total": len(zero_years),
            "passing": sum(1 for r in zero_report if r["pass"]),
            "detail": zero_report,
        },
        "C3_year_range": {
            "stray_year_tokens": stray,
            "pass": not stray,
        },
        "C4_verdict_years": {
            "verdict_total": len(verdict_years),
            "passing": sum(1 for r in verdict_report if r["pass"]),
            "detail": verdict_report,
        },
        "C5": {
            "response_side": "N/A (scoring-side; see criteria_checklist.md)",
            "tropical_storm_units_in_context": ts_count,
        },
    }


def verdict(checks):
    rows = []
    for summary in sorted(checks, key=lambda c: c["budget"]):
        c2 = summary["C2_zero_years"]
        c4 = summary["C4_verdict_years"]
        c1 = "PASS" if summary["C1_address_scope"] else "FAIL"
        c2v = f"{c2['passing']}/{c2['expected_zero_total']}"
        c3 = "PASS" if summary["C3_year_range"]["pass"] else "FAIL"
        c4v = f"{c4['passing']}/{c4['verdict_total']}"
        c5 = f"{summary['C5']['tropical_storm_units_in_context']} TS units"
        rows.append(
            (summary["budget"], summary["context_words"], summary["selected"],
             c1, c2v, c3, c4v, c5)
        )
    return rows


def write_markdown(checks):
    lines = [
        "# Retrieval-adequacy by context budget (words)",
        "",
        "One adequacy check per budget: cross-impl MATCH is asserted by",
        "challenge.py, so all implementations share the same context.",
        "",
        "| budget | ctx words | selected | C1 scope | C2 zero-years | C3 range | C4 verdict-years | C5 note |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for b, cw, sel, c1, c2, c3, c4, c5 in verdict(checks):
        lines.append(f"| {b} | {cw} | {sel} | {c1} | {c2} | {c3} | {c4} | {c5} |")
    lines += ["", "C2/C4 denominators are oracle counts from challenge.txt.",
              "Percentages themselves are response-side scoring (criteria_checklist.md).", ""]
    path = RESULTS_DIR / "challenge_adequacy.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    results_path = RESULTS_DIR / "challenge_results.json"
    if not results_path.exists():
        raise SystemExit(f"missing {results_path}; run: python challenge.py")

    payload = json.loads(results_path.read_text(encoding="utf-8"))
    zero_years, verdict_years = parse_challenge_criteria()
    if not zero_years or not verdict_years:
        raise SystemExit("could not parse oracle year lists from challenge.txt")

    meta = load_unit_meta()
    checks = [
        check_budget(key, summary, meta, zero_years, verdict_years)
        for key, summary in payload["per_budget"].items()
    ]

    out = {
        "source": "challenge.py results",
        "oracle_zero_years": zero_years,
        "oracle_verdict_years": verdict_years,
        "impls": ["Python", "C", "Rust", "Go"],
        "cross_impl_match_asserted": True,
        "per_budget": sorted(checks, key=lambda c: c["budget"]),
    }
    out_path = RESULTS_DIR / "challenge_adequacy.json"
    out_path.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    md_path = write_markdown(checks)

    print("\nRETRIEVAL-ADEQUACY CHECK (context-side, deterministic)")
    print("=" * 72)
    header = f"{'budget':>6} {'words':>6} {'sel':>4}  {'C1':<5} {'C2 zero-yrs':<12} {'C3':<5} {'C4 verdict-yrs':<15} C5"
    print(header)
    print("-" * 72)
    for b, cw, sel, c1, c2, c3, c4, c5 in verdict(checks):
        print(f"{b:>6} {cw:>6} {sel:>4}  {c1:<5} {c2:<12} {c3:<5} {c4:<15} {c5}")
    print(f"\nwrote {out_path}")
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
