"""
Builds the ASM fixture for the NOAA challenge (WORKQUEUE W2).

Inputs (no PDF processing — everything is read from text/JSON that already
exists in the repository):
  - challenge.txt               : question line 1 (+ the 5 criteria oracle)
  - noaTechnicalReport.txt      : extracted report text (25,062 words)
  - figure5_events_draft.json   : Figure 5 transcription (PROVISIONAL;
                                  digit-verification was deferred by user
                                  directive 2026-11-07, see WORKQUEUE W1)

Outputs (repo root, generated — never hand-edit):
  - asm_fixture.json : array of {address, text} units
  - asm_input.txt    : line-format input for the four implementations
                       line 1 = question (single line, \t/\n as \t and \n)
                       line 2 = default budget (words)
                       lines 3..N = <address>\t<text>

Unit kinds:
  doc/chunk/NNNN                      ~55-80 word report-text chunks
  figure5/disaster/<year>/<event-id>  one unit per mapped event
  figure5/year-summary/<year>         per-year event list, 1980-2010; a year
                                      with no events reads "none" — this is
                                      what lets a checker verify the
                                      "0% hurricane share" criteria (C2)

Amendment (2026-11-07): the challenge question is NOT a memory unit. It is
carried as line 1 of asm_input.txt (every implementation already receives it
as the query argument) and in every challenge.py prompt file, so it must not
compete for context budget. (W2 originally specified a challenge/question
unit; observation showed it echoes the query into the context at score 39.)

Determinism: running twice yields byte-identical outputs. Because every
downstream implementation treats input as UTF-8 (or raw bytes in C), all
generated text is sanitized to ASCII (non-ASCII -> '?') and whitespace is
collapsed; tabs never occur in generated text bodies.

Word counts are whitespace-delimited [A-Za-z0-9]+ runs (words, never
"tokens" — ASM_DESIGN.md 5.2).
"""

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

WORD_RE = re.compile(r"[A-Za-z0-9]+")
YEARS = list(range(1980, 2011))
DEFAULT_BUDGET = 600  # line 2 default; the sweep overrides via argv


def words(text):
    return WORD_RE.findall(text)


def sanitize(text):
    """ASCII-only, whitespace-collapsed, tab-free single-line text."""
    out = []
    last_space = False
    for ch in text:
        code = ord(ch)
        if code < 256 and not ch.isspace() and ch.isprintable():
            ch = ch if code < 128 else "?"
            out.append(ch)
            last_space = False
        else:
            if not last_space:
                out.append(" ")
                last_space = True
    return "".join(out).strip()


def fmt_cost(value):
    """Trim trailing zeros but keep at least one decimal: 2.0 -> '2.0',
    2.3 -> '2.3', 17.25 -> '17.25', 6.8/2 -> '3.4'."""
    s = f"{round(float(value), 4):.2f}".rstrip("0")
    return s if not s.endswith(".") else s + "0"


def build_doc_chunks(report_text):
    """Greedy line-accumulation chunking to the 55-80 word target."""
    chunks = []
    buffer = []

    def flush():
        if buffer:
            chunks.append(sanitize(" ".join(buffer)))
            buffer.clear()

    for line in report_text.splitlines():
        if not line.strip():
            continue
        buffer.append(line)
        if len(words(" ".join(buffer))) >= 55:
            flush()
    flush()

    return [
        {"address": f"doc/chunk/{i:04d}", "text": text}
        for i, text in enumerate(chunks, start=1)
        if text
    ]


def years_key(years):
    if len(years) == 1:
        return str(years[0])
    return f"{years[0]}-{years[-1]}"


def build_event_units(events):
    for event in events:
        key = years_key(event["years"])
        address = f"figure5/disaster/{key}/{event['id']}"
        text = sanitize(
            f"Figure 5 event: {event['type']}. Location: {event['location']}. "
            f"{key}: cost {fmt_cost(event['cost'])} billion dollars."
        )
        yield {"address": address, "text": text, "event": event}


def build_year_summaries(per_year):
    units = []
    for year in YEARS:
        entries = per_year.get(year, [])
        if entries:
            listing = "; ".join(
                f"{event['type']}, {fmt_cost(event['cost'] / len(event['years']))} billion dollars"
                for event in entries
            )
        else:
            listing = "none"
        text = sanitize(f"Figure 5 events in {year}: {listing}.")
        units.append({"address": f"figure5/year-summary/{year}", "text": text})
    return units


def main():
    challenge_txt = (HERE / "challenge.txt").read_text(encoding="utf-8")
    question = sanitize(
        challenge_txt.splitlines()[0].removeprefix("#question:").strip()
    )
    if not question:
        raise SystemExit("challenge.txt line 1 missing the #question: prefix")

    report_text = (HERE / "noaTechnicalReport.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    draft = json.loads(
        (HERE / "figure5_events_draft.json").read_text(encoding="utf-8")
    )
    events = draft["events"]

    per_year = {}
    for event in events:
        for year in event["years"]:
            per_year.setdefault(year, []).append(event)

    units = build_doc_chunks(report_text)
    figure_units = [u for u in build_event_units(events)]
    figure_units.extend(build_year_summaries(per_year))
    figure_units.sort(key=lambda u: u["address"])
    units.extend(
        {"address": u["address"], "text": u["text"]} for u in figure_units
    )

    fixture_json = ROOT / "asm_fixture.json"
    fixture_txt = ROOT / "asm_input.txt"

    lines = [
        question.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n"),
        str(DEFAULT_BUDGET),
    ]
    lines.extend(f"{u['address']}\t{u['text']}" for u in units)
    fixture_txt.write_bytes("\n".join(lines).encode("ascii") + b"\n")

    fixture_json.write_text(
        json.dumps(units, ensure_ascii=True, indent=1) + "\n", encoding="ascii"
    )

    unit_count = len(units)
    total_words = sum(len(words(u["text"])) for u in units)
    json_sha = hashlib.sha256(fixture_json.read_bytes()).hexdigest()
    txt_sha = hashlib.sha256(fixture_txt.read_bytes()).hexdigest()
    print(f"units={unit_count} total_words={total_words}")
    print(f"asm_fixture.json sha256={json_sha}")
    print(f"asm_input.txt    sha256={txt_sha}")


if __name__ == "__main__":
    main()
