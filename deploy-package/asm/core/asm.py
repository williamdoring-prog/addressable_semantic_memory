from dataclasses import dataclass
from typing import List, Dict, Tuple
import re

WORD_RE = re.compile(r"[A-Za-z0-9]+")


@dataclass
class Fragment:
    """A single addressed unit of semantic content."""
    address: str
    text: str


class ASM:
    """Simple deterministic ASM retrieval/selection implementation.

    Manages bounded semantic context for AI agents. Supports creating scopes,
    adding information, querying under a word budget, inspecting addresses,
    adjusting scope boundaries, creating summaries, and recovering from context loss.
    """

    def words(self, text: str) -> List[str]:
        """Extract lowercase word tokens from text (whitespace-delimited)."""
        return [w.lower() for w in WORD_RE.findall(text)]

    def run(self, question: str, fragments: List[Fragment], budget: int) -> Dict:
        """Run ASM retrieval: rank fragments by term overlap with question,
        select under a word budget, and return served context.

        Returns a dict with:
        - original_source_words: total words in all fragments
        - question_words: word count of the question
        - retrieved_addresses: all fragment addresses sorted by score
        - selected: chosen fragments within budget
        - context: served context text (join of selected fragments)
        - context_words: word count of served context
        """
        query = set(self.words(question))
        scored: List[Tuple[int, str, Fragment, int]] = []
        original_words = 0

        for fragment in fragments:
            fragment_words = self.words(fragment.text)
            token_count = len(fragment_words)
            terms = set(fragment_words)
            original_words += token_count
            score = len(query & terms)
            if score > 0:
                scored.append((score, fragment.address, fragment, token_count))

        # Sort by score (descending), then by address (stable order)
        scored.sort(key=lambda x: (-x[0], x[1]))

        context_parts = []
        selected = []
        context_tokens = 0

        for score, address, fragment, token_count in scored:
            if context_tokens + token_count > budget:
                continue
            context_parts.append(fragment.text)
            selected.append({"address": address, "score": score})
            context_tokens += token_count

        return {
            "original_source_words": original_words,
            "question_words": len(self.words(question)),
            "retrieved_addresses": [x[1] for x in scored],
            "selected": selected,
            "context": " ".join(context_parts),
            "context_words": context_tokens,
        }

    def run_control(self, fragments: List[Fragment]) -> Dict:
        """No-ASM control pass: serve every input unit verbatim in file order.

        Used as the paired comparator required by WORKQUEUE §R19: serves the
        entire input as context in file order — no ranking, no selection,
        no score>0 retrieval filter.
        """
        original_words = 0
        context_parts = []
        selected = []
        for fragment in fragments:
            token_count = len(self.words(fragment.text))
            original_words += token_count
            context_parts.append(fragment.text)
            selected.append({"address": fragment.address, "score": 1})
        return {
            "mode": "no-asm control",
            "original_source_words": original_words,
            "retrieved_addresses": [f.address for f in fragments],
            "selected": selected,
            "context": " ".join(context_parts),
            "context_words": original_words,
        }