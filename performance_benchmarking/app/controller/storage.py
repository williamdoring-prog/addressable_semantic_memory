"""Append-only JSONL experiment result storage."""

from __future__ import annotations

import json
from pathlib import Path
from threading import Lock


class ResultStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded + "\n")

    def list(self, on_malformed=None) -> list[dict]:
        """Return every record, skipping malformed lines instead of failing.

        ``on_malformed(line_number, malformed_count)`` is called for each line
        that is not valid JSON so callers can log the corruption without the
        whole read path breaking. Original data is never modified or deleted.
        """
        if not self.path.exists():
            return []
        records = []
        malformed = 0
        with self._lock, self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    malformed += 1
                    if on_malformed is not None:
                        on_malformed(line_number, malformed)
        return records
