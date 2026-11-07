# Retrieval-adequacy by context budget (words)

One adequacy check per budget: cross-impl MATCH is asserted by
challenge.py, so all implementations share the same context.

| budget | ctx words | selected | C1 scope | C2 zero-years | C3 range | C4 verdict-years | C5 note |
|---|---|---|---|---|---|---|---|
| 150 | 147 | 3 | PASS | 2/18 | FAIL | 0/13 | 0 TS units |
| 300 | 299 | 7 | PASS | 4/18 | FAIL | 0/13 | 0 TS units |
| 600 | 600 | 12 | PASS | 5/18 | FAIL | 0/13 | 0 TS units |
| 1200 | 1199 | 19 | PASS | 8/18 | FAIL | 0/13 | 0 TS units |
| 2400 | 2399 | 38 | PASS | 9/18 | FAIL | 0/13 | 0 TS units |

C2/C4 denominators are oracle counts from challenge.txt.
Percentages themselves are response-side scoring (criteria_checklist.md).
