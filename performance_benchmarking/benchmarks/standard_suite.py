"""Deterministic, local-only Standard ASM Benchmark v1 task set."""

from __future__ import annotations

# The smoke mode exercises the smallest pipeline paths of the standard suite:
# one exact-answer case with expected evidence and one missing-information case
# whose expected evidence is empty. Both carry evaluation criteria so the local
# criterion evaluator is exercised once. Add no larger or more expensive case.
SMOKE_CASE_IDS = ("factual-v1", "missing-fact-v1")


STANDARD_CATEGORIES = [
    "Factual retrieval",
    "Exact wording retrieval",
    "Long-document comprehension",
    "Information far apart",
    "Multiple-document reasoning",
    "Contradictory information",
    "Missing information",
    "Relationships",
    "Numerical information",
    "Source reconstruction",
]


def build_standard_suite() -> list[dict]:
    """Build the fixed suite from embedded synthetic sources; no network data."""
    long_source = " ".join(
        f"Archive log {i:03d} records routine inventory calibration and administrative review with no exceptional change."
        for i in range(80)
    ) + " The observatory's assigned beacon color is violet."
    suite = [
        {
            "case_id": "factual-v1", "category": "Factual retrieval",
            "source": "The North Annex stores the sealed archive in cabinet Kappa. The reading room opens at 09:00.",
            "question": "What cabinet stores the sealed archive? Answer with only the cabinet name.",
            "expected_answer": "Kappa", "expected_evidence": ["The North Annex stores the sealed archive in cabinet Kappa."],
            "criteria": ["Identifies cabinet Kappa.", "Does not confuse the opening time with the cabinet location."],
        },
        {
            "case_id": "exact-wording-v1", "category": "Exact wording retrieval",
            "source": "The field note says: 'Quiet rivers remember the stone.' The note is classified as archival poetry.",
            "question": "Quote the field note exactly, including its punctuation.",
            "expected_answer": "Quiet rivers remember the stone.", "expected_evidence": ["Quiet rivers remember the stone."],
            "criteria": ["Returns the exact quoted phrase.", "Preserves the final period."],
        },
        {
            "case_id": "long-document-v1", "category": "Long-document comprehension",
            "source": long_source,
            "question": "What color is the observatory's assigned beacon? Answer with only the color.",
            "expected_answer": "violet", "expected_evidence": ["The observatory's assigned beacon color is violet."],
            "criteria": ["Identifies violet as the beacon color.", "Does not invent another color."],
        },
        {
            "case_id": "distant-facts-v1", "category": "Information far apart",
            "source": "Project Alder uses the Lumen controller. " + "Routine status logs contain no deployment change. " * 20 + "The Lumen controller's final deployment is in bay 14.",
            "question": "In which bay is the controller currently used by Project Alder? Answer with only the bay number.",
            "expected_answer": "14", "expected_evidence": ["Project Alder uses the Lumen controller.", "The Lumen controller's final deployment is in bay 14."],
            "criteria": ["Connects Project Alder to the Lumen controller.", "States bay 14 as the deployment location."],
        },
        {
            "case_id": "multi-document-v1", "category": "Multiple-document reasoning",
            "source": "Document A: Project Rowan uses module Cedar.\nDocument B: Cedar was replaced by module Flint.\nDocument C: Flint requires 24 GB of memory.",
            "question": "How much memory does the current module used by Project Rowan require? Answer with only the amount.",
            "expected_answer": "24 GB", "expected_evidence": ["Project Rowan uses module Cedar.", "Cedar was replaced by module Flint.", "Flint requires 24 GB of memory."],
            "criteria": ["Identifies Flint as the current module.", "States 24 GB.", "Does not describe Cedar as current."],
        },
        {
            "case_id": "conflicting-records-v1", "category": "Contradictory information",
            "source": "January 4 revision: the reserve pressure is 18 kPa. March 9 revision: the reserve pressure is 21 kPa. The March revision supersedes the January revision.",
            "question": "What reserve pressure is current? Answer with only the value and unit.",
            "expected_answer": "21 kPa", "expected_evidence": ["March 9 revision: the reserve pressure is 21 kPa.", "The March revision supersedes the January revision."],
            "criteria": ["Uses the superseding March value of 21 kPa.", "Does not report the superseded January value as current."],
        },
        {
            "case_id": "missing-fact-v1", "category": "Missing information",
            "source": "The workshop is in building 6. Its access hours are 08:00 to 16:00. The document does not list a room number.",
            "question": "What room number is the workshop in? If the source does not specify it, answer 'not specified'.",
            "expected_answer": "not specified", "expected_evidence": [],
            "criteria": ["States that the room number is not specified.", "Does not invent a room number."],
        },
        {
            "case_id": "relationships-v1", "category": "Relationships",
            "source": "Nia supervises Omar. Omar maintains the west archive. Priya supervises the east archive.",
            "question": "Who supervises the person maintaining the west archive? Answer with only the name.",
            "expected_answer": "Nia", "expected_evidence": ["Nia supervises Omar.", "Omar maintains the west archive."],
            "criteria": ["Names Nia as Omar's supervisor.", "Uses the west archive relationship rather than the east archive distractor."],
        },
        {
            "case_id": "numerical-v1", "category": "Numerical information",
            "source": "A storage tank contains 240 liters. The maintenance plan removes 15 percent of the contents.",
            "question": "How many liters remain after maintenance? Answer with only the number.",
            "expected_answer": "204", "expected_evidence": ["A storage tank contains 240 liters.", "The maintenance plan removes 15 percent of the contents."],
            "criteria": ["Calculates 204 liters remaining.", "Applies the 15 percent reduction rather than subtraction of 15 liters."],
        },
        {
            "case_id": "reconstruction-v1", "category": "Source reconstruction",
            "source": "Step 1: the intake valve is closed. Step 2: the filter is replaced. Step 3: the intake valve is reopened.",
            "question": "Summarize the maintenance sequence in order.",
            "expected_answer": "Close the intake valve, replace the filter, then reopen the intake valve.",
            "expected_evidence": ["the intake valve is closed", "the filter is replaced", "the intake valve is reopened"],
            "criteria": ["Places valve closure before filter replacement.", "Places filter replacement before reopening the valve.", "Includes all three actions."],
        },
    ]
    return suite


def build_smoke_suite() -> list[dict]:
    """Return the fixed minimal subset used by the Standard Benchmark smoke mode."""
    suite = {case["case_id"]: case for case in build_standard_suite()}
    smoke_cases = [suite[case_id] for case_id in SMOKE_CASE_IDS]
    if len(smoke_cases) != len(SMOKE_CASE_IDS):
        raise ValueError("the standard suite must contain every fixed smoke case")
    return smoke_cases
