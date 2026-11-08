"""Small deterministic ASM prototype with source-preserving addresses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re
import time
from typing import Iterable


TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)
WORD_RE = re.compile(r"[\w]+", re.UNICODE)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def tokenize(text: str) -> list[str]:
    """Tokenize with the documented deterministic ASM word/punctuation tokenizer."""
    return TOKEN_RE.findall(text)


@dataclass(frozen=True)
class Fragment:
    address: str
    source_id: str
    ordinal: int
    text: str


@dataclass(frozen=True)
class Representation:
    representation_id: str
    text: str
    addresses: tuple[str, ...]
    keywords: tuple[str, ...]
    method: str


class AddressNotFoundError(KeyError):
    """Raised when a caller expands an unknown source address."""


class ASMEngine:
    """Addressable fragments with optional derived summaries; source stays intact."""

    def __init__(self) -> None:
        self.fragments: dict[str, Fragment] = {}
        self.representations: list[Representation] = []
        self.source_text = ""
        self.source_id = ""
        self.stage_times_ms: dict[str, float] = {}

    def ingest(self, source: str) -> list[Fragment]:
        started = time.perf_counter()
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source must be a non-empty string")
        self.source_text = source
        self.source_id = hashlib.sha256(source.encode("utf-8")).hexdigest()
        self.fragments.clear()
        self.representations.clear()
        pieces = []
        start = 0
        for match in SENTENCE_RE.finditer(source):
            piece = source[start:match.end()]
            if piece.strip():
                pieces.append(piece)
            start = match.end()
        tail = source[start:]
        if tail.strip():
            pieces.append(tail)
        if not pieces:
            pieces = [source]
        output = []
        for index, text in enumerate(pieces):
            address = f"src:{self.source_id[:16]}:{index:06d}"
            fragment = Fragment(address, self.source_id, index, text)
            self.fragments[address] = fragment
            output.append(fragment)
        self.stage_times_ms["source_fragmentation_time_ms"] = (time.perf_counter() - started) * 1000
        return output

    @staticmethod
    def _keywords(text: str) -> set[str]:
        terms = set()
        for word in WORD_RE.findall(text):
            term = word.casefold()
            if len(term) > 4 and term.endswith("ies"):
                term = term[:-3] + "y"
            elif len(term) > 5 and term.endswith("ing"):
                term = term[:-3]
            elif len(term) > 4 and term.endswith("s"):
                term = term[:-1]
            if len(term) > 1:
                terms.add(term)
        return terms

    def compress(self, summaries: list[dict] | None = None) -> list[Representation]:
        started = time.perf_counter()
        if not self.fragments:
            raise ValueError("ingest source before compressing")
        if summaries is not None:
            if not isinstance(summaries, list) or not summaries:
                raise ValueError("semantic summaries must be a non-empty list")
            known = set(self.fragments)
            covered: set[str] = set()
            representations = []
            for index, item in enumerate(summaries):
                if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
                    raise ValueError("each semantic summary must contain non-empty text")
                addresses = item.get("addresses")
                if not isinstance(addresses, list) or not addresses or not all(isinstance(a, str) for a in addresses):
                    raise ValueError("each semantic summary must reference one or more source addresses")
                unknown = set(addresses) - known
                if unknown:
                    raise ValueError(f"semantic summary references unknown addresses: {sorted(unknown)}")
                covered.update(addresses)
                indexed_terms = self._keywords(item["text"])
                for address in addresses:
                    indexed_terms.update(self._keywords(self.fragments[address].text))
                representations.append(Representation(
                    representation_id=f"rep:{index:06d}",
                    text=item["text"].strip(),
                    addresses=tuple(dict.fromkeys(addresses)),
                    keywords=tuple(sorted(indexed_terms)),
                    method="local-model-semantic",
                ))
            missing = known - covered
            if missing:
                raise ValueError(f"semantic summaries omit source addresses: {sorted(missing)}")
            self.representations = representations
            self.stage_times_ms["representation_indexing_time_ms"] = (time.perf_counter() - started) * 1000
            return self.representations

        # Compact lexical indexes retain searchable terms for every fragment.
        # This deterministic path is a retrieval baseline, not semantic compression.
        self.representations = []
        for index, fragment in enumerate(self.fragments.values()):
            terms = tuple(sorted(self._keywords(fragment.text)))
            self.representations.append(Representation(
                representation_id=f"rep:{index:06d}",
                text=" ".join(terms),
                addresses=(fragment.address,),
                keywords=terms,
                method="keyword-index",
            ))
        self.stage_times_ms["representation_indexing_time_ms"] = (time.perf_counter() - started) * 1000
        return self.representations

    def address(self, value: str | Representation) -> tuple[str, ...]:
        if isinstance(value, Representation):
            return value.addresses
        matches = tuple(fragment.address for fragment in self.fragments.values() if fragment.text.strip() == value.strip())
        if matches:
            return matches
        raise AddressNotFoundError(value)

    def resolve(self, address: str) -> Fragment:
        try:
            return self.fragments[address]
        except KeyError as exc:
            raise AddressNotFoundError(address) from exc

    def retrieve(self, query: str, limit: int | None = None) -> list[Representation]:
        if not self.representations:
            self.compress()
        terms = self._keywords(query)
        ranked = []
        for rep in self.representations:
            overlap = len(terms.intersection(rep.keywords))
            if overlap:
                ranked.append((overlap, rep.representation_id, rep))
        ranked.sort(key=lambda row: (-row[0], row[1]))
        results = [row[2] for row in ranked]
        return results if limit is None else results[:max(0, limit)]

    def expand(self, addresses: Iterable[str]) -> list[Fragment]:
        unique: list[str] = []
        seen: set[str] = set()
        for address in addresses:
            if address not in seen:
                self.resolve(address)  # fail explicitly before returning partial data
                unique.append(address)
                seen.add(address)
        return [self.resolve(address) for address in unique]

    def assemble(self, query: str, budget: int, expand_sources: bool = True) -> dict:
        assembly_started = time.perf_counter()
        if budget <= 0:
            raise ValueError("token budget must be positive")
        retrieval_started = time.perf_counter()
        reps = self.retrieve(query)
        retrieval_ms = (time.perf_counter() - retrieval_started) * 1000
        # Expansion of selected addresses restores verbatim source; the compact
        # representation is used as a selection index and is not presented as source.
        selected: list[dict] = []
        used = 0
        expansion_started = time.perf_counter()
        for rep in reps:
            fragments = self.expand(rep.addresses) if expand_sources else []
            text = "\n".join(fragment.text for fragment in fragments) if expand_sources else rep.text
            cost = len(tokenize(text))
            if used + cost > budget:
                continue
            selected.append({"representation": asdict(rep), "expanded": [asdict(f) for f in fragments]})
            used += cost
        expansion_ms = (time.perf_counter() - expansion_started) * 1000
        context = "\n".join(
            "\n".join(fragment["text"] for fragment in item["expanded"])
            if expand_sources else item["representation"]["text"]
            for item in selected
        )
        total_assembly_ms = (time.perf_counter() - assembly_started) * 1000
        self.stage_times_ms["retrieval_time_ms"] = retrieval_ms
        self.stage_times_ms["expansion_time_ms"] = expansion_ms
        self.stage_times_ms["context_assembly_time_ms"] = max(0.0, total_assembly_ms - retrieval_ms - expansion_ms)
        return {
            "question": query,
            "question_tokens": len(tokenize(query)),
            "context": context,
            "selected": selected,
            "token_count": used,
            "tokenizer": "ASM word/punctuation tokenizer v1",
            "budget": budget,
            "expand_sources": expand_sources,
        }

    def metrics(self, assembled: dict, elapsed_ms: float) -> dict:
        original = len(tokenize(self.source_text))
        compressed = sum(len(tokenize(rep.text)) for rep in self.representations)
        recovered = len(tokenize(assembled["context"]))
        return {
            "original_source_tokens": original,
            "compressed_representation_tokens": compressed,
            "compression_ratio": (original / compressed) if compressed else None,
            "percentage_reduction": ((1 - compressed / original) * 100) if original else 0.0,
            "representations_created": len(self.representations),
            "addresses_created": len(self.fragments),
            "addresses_retrieved": len({a for row in assembled["selected"] for a in row["representation"]["addresses"]}),
            "expansions": sum(len(row["expanded"]) for row in assembled["selected"]),
            "tokens_recovered_through_expansion": recovered,
            "final_assembled_context_tokens": assembled["token_count"],
            "question_tokens": assembled["question_tokens"],
            "system_instruction_tokens": None,
            "generation_tokens": None,
            "processing_time_ms": elapsed_ms,
            **self.stage_times_ms,
            "tokenizer": assembled["tokenizer"],
        }


def prepare_asm(source: str, question: str, budget: int, summaries: list[dict] | None = None, expand_sources: bool = True) -> tuple[ASMEngine, dict, dict]:
    started = time.perf_counter()
    engine = ASMEngine()
    engine.ingest(source)
    engine.compress(summaries)
    assembled = engine.assemble(question, budget, expand_sources)
    elapsed = (time.perf_counter() - started) * 1000
    return engine, assembled, engine.metrics(assembled, elapsed)
