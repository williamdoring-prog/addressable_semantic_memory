"""
Deterministic model-response scorer (WORKQUEUE paired-measurement rule).

Scores a free-text model response against the challenge oracle with NO LLM
judge in the loop - every check is a fixed regex/arithmetic rule over the
response plus the oracle parsed from challenge-documents/challenge.txt
(zero-year list; verdict-year percentage pairs) and figure5_events_draft.json
(valid cost universe for the sourcing proxy).

Per-criterion categories (C1-C5 from the challenge; deterministic proxies):
  C1 sourcing   - every dollar/billion figure must be a valid Figure-5 value
                  (an event cost, its evenly-allocated share, or an oracle
                  percentage cited as a cost); unknown figures fail.
  C2 zero-years - years the response marks as 0% hurricane share must be
                  oracle zero-years; claims of nonzero for zero-years and
                  marks of 0% for nonzero years are contradictions.
  C3 year range - no 4-digit year outside 1980-2010 anywhere in the response.
  C4 verdict    - every (year, percentage) pair for an oracle verdict year
                  must match the oracle value to one decimal (|diff|<=0.05).
  C5 tropical   - no tropical-storm event presented WITH a dollar figure.

All counts use the response text only; the served context is not re-read.
Words are whitespace-delimited [A-Za-z0-9]+ runs (never tokens).
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys_root = str(ROOT)
if sys_root not in __import__("sys").path:
    __import__("sys").path.insert(0, sys_root)

import check_challenge as cc  # noqa: E402

YEAR_STRAY_SRC = re.compile(r"\b[0-9]{4}\b")
PCT_PAIR = re.compile(
    r"(19[0-9]{2}|20[0-9]{2})\s*[(:\-:]\s*([0-9]+(?:\.[0-9])?)\s*%")
PCT_REV = re.compile(
    r"([0-9]+(?:\.[0-9])?)\s*%\s*(?:of[^.\n]{0,50}?)?(19[0-9]{2}|20[0-9]{2})")
DOLLAR = re.compile(r"\$?\s*([0-9]+(?:\.[0-9])?)\s*(?:billion( dollars?)?\b|\bB\b)")
TS_SENT = re.compile(r"[^\n.]*tropical storm[^\n.]*")
EVENT_RE = cc.EVENT_RE


def _valid_universe():
    draft = json.loads(
        (ROOT / "challenge-documents" / "figure5_events_draft.json").read_text(
            encoding="utf-8")
    )
    values = {0.0, 100.0}
    for event in draft["events"]:
        cost = float(event["cost"])
        values.add(round(cost, 4))
        values.add(round(cost / len(event["years"]), 4))
    return values


def score_response(response, meta=None):
    zero_years, verdict_years = cc.parse_challenge_criteria()
    verdict_pct = cc.parse_verdict_pairs()
    valid = _valid_universe()

    tokens4 = set(YEAR_STRAY_SRC.findall(response))
    stray = sorted(t for t in tokens4
                   if t.isdigit() and not (1980 <= int(t) <= 2010))

    pairs = {}
    for year_str, pct_str in PCT_PAIR.findall(response):
        pairs.setdefault(year_str, float(pct_str))
    for pct_str, year_str in PCT_REV.findall(response):
        pairs.setdefault(year_str, float(pct_str))

    zero_set = set(zero_years)
    verdict_set = set(verdict_years)

    believed_zero = {y for y, p in pairs.items()
                     if y in zero_set and p <= 0.05}
    contradictions = [
        (y, p) for y, p in pairs.items()
        if (y in zero_set and p > 0.05) or (y in verdict_set and p <= 0.05)
    ]

    matched, wrong = [], []
    for year_str, oracle_pct in verdict_pct.items():
        given = pairs.get(year_str)
        if given is None:
            continue
        (matched if abs(given - oracle_pct) <= 0.05
         else wrong).append((int(year_str), given, oracle_pct))
    missing = [int(y) for y in verdict_years if y not in pairs]

    dollars = [float(v) for v, _ in DOLLAR.findall(response)]
    if dollars:
        invalid = [v for v in dollars
                   if not any(abs(v - w) <= 0.05 for w in valid)]
        invalid = sorted(set(invalid))
    else:
        invalid = []

    ts_violations = sum(
        1 for sentence in TS_SENT.findall(response) if DOLLAR.search(sentence)
    )
    ts_leak = (
        ts_violations > 0
        or bool(re.search(r"alberto[^.\n]*billion|allison[^.\n]*billion",
                          response, re.I))
    )

    return {
        "c1_sourcing": {
            "dollar_figures": len(dollars),
            "invalid_figures": invalid,
            "pass": not invalid,
        },
        "c2_zero_years": {
            "expected": len(zero_years),
            "identified_zero": len(believed_zero),
            "contradictions": contradictions,
            "score": max(0, len(believed_zero) - len(contradictions)),
        },
        "c3_year_range": {"stray": stray, "pass": not stray},
        "c4_verdict_years": {
            "expected": len(verdict_years),
            "matched": sorted(y for y, g, o in matched),
            "wrong": wrong,
            "missing": missing,
            "score": len(matched),
        },
        "c5_tropical_storm": {
            "dollar_leaks": ts_violations,
            "pass": not ts_leak,
        },
    }


def score_line(entry):
    """One human-readable pass row: category -> score for a response."""
    s = entry
    c2 = s["c2_zero_years"]
    c4 = s["c4_verdict_years"]
    return (
        f"C1 {'PASS' if s['c1_sourcing']['pass'] else 'FAIL'}"
        f"({s['c1_sourcing']['invalid_figures'][:2]}); "
        f"C2 {c2['score']}/{c2['expected']}; "
        f"C3 {'PASS' if s['c3_year_range']['pass'] else 'FAIL'}; "
        f"C4 {c4['score']}/{c4['expected']}; "
        f"C5 {'PASS' if s['c5_tropical_storm']['pass'] else 'FAIL'}"
    )


if __name__ == "__main__":
    text = __import__("sys").stdin.read()
    print(score_line(score_response(text)))
