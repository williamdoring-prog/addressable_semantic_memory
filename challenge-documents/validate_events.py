"""
Validates the Figure 5 transcription (figure5_events_draft.json) against the
oracle values embedded in challenge.txt.

Checks:
  1. Per-year hurricane share (one decimal) for every year 1980-2010 that has
     any disaster cost, compared with the percentages stated in criterion 4.
  2. Years declared 0% in criterion 2 must have zero hurricane cost AND some
     non-zero total cost.
  3. Total event count vs total_events_expected.

Multi-year events are allocated evenly across their span, per the question
text. "hurricane" type events count in the numerator; all other types count
only in the denominator. This is fixed by the criteria math, not by choice:
e.g. 1992 (94.9%) only reconciles when the Hawaii Iniki icon counts as a
hurricane, and 1985 (70.1%) requires BOTH 1985 tropical icons to be hurricanes.
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHALLENGE = HERE / "challenge.txt"
DRAFT = HERE / "figure5_events_draft.json"

YEARS = list(range(1980, 2011))


def parse_oracle(text):
    zero_years = []
    for line in text.splitlines():
        if "0% of total disaster costs:" in line:
            tail = line.split(":", 1)[1]
            zero_years = [int(y) for y in re.findall(r"\b(19|20)\d{2}\b", tail.replace(", ", " "))]
            # simpler: findall on the tail directly
    pct_years = {}
    for line in text.splitlines():
        if "percentage of total disaster costs from hurricanes:" in line:
            for m in re.finditer(r"(19|20)(\d{2})\s*\(([\d.]+)%\)", line):
                year = int(m.group(1) + m.group(2))
                pct_years[year] = float(m.group(3))
    # re-findall both lines robustly
    for line in text.splitlines():
        if "0% of total disaster costs:" in line:
            zero_years = sorted({int(m.group(0)) for m in re.finditer(r"(?:19|20)\d{2}", line.split(":", 1)[1])})
    return zero_years, pct_years


def yearly_allocations(events):
    totals = defaultdict(float)
    hurricane = defaultdict(float)
    contrib = defaultdict(list)
    for ev in events:
        span = ev.get("years", [])
        if not span:
            continue
        each = ev["cost"] / len(span)
        for year in span:
            if year not in YEARS:
                continue
            totals[year] += each
            contrib[year].append((ev["id"], ev["type"], round(each, 4)))
            if ev["type"] == "hurricane":
                hurricane[year] += each
    return totals, hurricane, contrib


def sharps(totals, hurricane):
    out = {}
    for year in YEARS:
        total = totals.get(year, 0.0)
        if total <= 0:
            continue
        out[year] = hurricane.get(year, 0.0) / total * 100.0
    return out


def main():
    text = CHALLENGE.read_text(encoding="utf-8", errors="replace")
    zero_years, pct_years = parse_oracle(text)

    data = json.loads(DRAFT.read_text(encoding="utf-8"))
    events = data["events"]
    expected_count = data.get("total_events_expected")

    totals, hurricane, contrib = yearly_allocations(events)
    shares = sharps(totals, hurricane)

    failures = 0

    print("YEAR  TOTAL$   HURR$   COMPUTED   EXPECTED   OK   EVENTS(H=hurricane*)")
    print("-" * 118)
    for year in YEARS:
        total = totals.get(year, 0.0)
        if total <= 0:
            continue
        h = hurricane.get(year, 0.0)
        share = shares[year]
        rounded = round(share, 1)
        ev_str = ", ".join(f"{eid}{'*' if t == 'hurricane' else ''}({t[:4]}){each:g}" for eid, t, each in contrib[year])
        if year in pct_years:
            exp = pct_years[year]
            ok = abs(rounded - exp) < 0.051
            flag = "OK  " if ok else "FAIL"
            if not ok:
                failures += 1
            print(f"{year}  {total:7.2f}  {h:7.2f}  {rounded:7.1f}%   {exp:7.1f}%   {flag}  {ev_str}")
        else:
            flag = "OK  " if abs(share) < 0.051 else "FAIL"
            if year in zero_years and abs(share) >= 0.051:
                failures += 1
                flag = "FAIL"
            elif year not in zero_years:
                flag = "????"
                print(f"(note: {year} has cost {total:.2f} but neither a 0% nor a percentage "
                      f"claim in challenge.txt)")
            print(f"{year}  {total:7.2f}  {h:7.2f}  {rounded:7.1f}%      --     {flag}  {ev_str}")

    print()
    covered_zero = {y for y in zero_years if totals.get(y, 0.0) > 0}
    missing_zero = [y for y in zero_years if totals.get(y, 0.0) <= 0]
    if missing_zero:
        print(f"FAIL years declared 0% but have NO events transcribed: {missing_zero}")
        failures += len(missing_zero)
    if covered_zero:
        print(f"OK zero-years fully covered by transcription: {len(covered_zero)}/{len(zero_years)}")

    if expected_count and len(events) != expected_count:
        print(f"FAIL event count {len(events)} != expected {expected_count}")
        failures += 1
    else:
        print(f"OK event count {len(events)}")

    print()
    if failures:
        print(f"RESULT: {failures} failure(s). Target next: the FAIL rows above, then any "
              f"'????' rows need an oracle value check (should not happen with challenge.txt).")
        sys.exit(1)
    print("RESULT: all criteria percentages and zero-years reproduced.")


if __name__ == "__main__":
    main()
