from dataclasses import dataclass
from typing import List, Dict, Tuple
import re

WORD_RE = re.compile(r"[A-Za-z0-9]+")

@dataclass
class Fragment:
    address: str
    text: str

class ASM:
    """Simple deterministic ASM retrieval/selection implementation."""

    def words(self, text: str) -> List[str]:
        return [w.lower() for w in WORD_RE.findall(text)]

    def run(self, question: str, fragments: List[Fragment], budget: int) -> Dict:
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
