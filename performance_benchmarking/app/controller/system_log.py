"""Append-only local system event log with automatic failure alerts.

Every system event is one JSON line in ``data/logs/system_events.jsonl``.
Events with severity ``error`` or ``critical`` carry ``"alert": true`` so the
interface lists them as automatic alerts. When the same component keeps
failing, one escalation alert is emitted per fixed window so recurring
problems are visible without flooding the log.

Design constraints (project rules):

- Standard library only; no frameworks, no external services, no cloud calls.
- The log must never break the application: if writing the event file fails,
  events are mirrored to the console instead and the failure is swallowed.
- Every reader can rely on: ``event_id``, ``timestamp``, ``severity``,
  ``component``, ``event_type``, ``message`` being present in every record.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import sys
from threading import Lock
import traceback
import uuid
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.controller.storage import ResultStore  # noqa: E402

SEVERITIES = ("info", "warning", "error", "critical")
ALERT_SEVERITIES = ("error", "critical")
ALERT_REPEAT_THRESHOLD = 3
ALERT_REPEAT_WINDOW_MINUTES = 15
TRACEBACK_LIMIT = 4000
DEFAULT_LOG_PATH = ROOT / "data" / "logs" / "system_events.jsonl"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _jsonable(value):
    """Return a value that json.dumps can serialize, degrading unknown types to str."""
    try:
        json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)
    return value


def _format_exception(exc) -> str | None:
    if exc is None:
        return None
    return "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))[:TRACEBACK_LIMIT]


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


class EventStore:
    """Append-only system event store with escalation alert rules."""

    def __init__(
        self,
        path: Path,
        repeat_threshold: int = ALERT_REPEAT_THRESHOLD,
        repeat_window_minutes: int = ALERT_REPEAT_WINDOW_MINUTES,
    ) -> None:
        self.store = ResultStore(path)
        self.repeat_threshold = max(1, int(repeat_threshold))
        self.repeat_window_seconds = max(0, int(repeat_window_minutes)) * 60
        self._alert_lock = Lock()
        self._streaks: dict[tuple[str, str], dict] = {}

    # -- recording ---------------------------------------------------------------

    def record(
        self,
        severity: str,
        component: str,
        event_type: str,
        message: str,
        details: dict | None = None,
        exc: BaseException | None = None,
    ) -> dict:
        """Record one system event; return the stored event record."""
        event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": _utcnow().isoformat(),
            "severity": severity if severity in SEVERITIES else "warning",
            "component": str(component),
            "event_type": str(event_type),
            "message": str(message),
            "details": {key: _jsonable(value) for key, value in (details or {}).items()} or None,
            "traceback": _format_exception(exc),
            "alert": severity in ALERT_SEVERITIES,
        }
        self._append(event)
        self._mirror(event)
        if event["alert"]:
            self._escalate(event)
        return event

    def _append(self, event: dict) -> None:
        try:
            self.store.append(event)
        except OSError:
            # The system log itself must never break the application.
            print(
                f"SYSTEM LOG WRITE FAILED {event['timestamp']} "
                f"{event['severity']} {event['component']}/{event['event_type']}: {event['message']}",
                file=sys.stderr,
            )

    def _mirror(self, event: dict) -> None:
        print(
            f"{event['severity'].upper()} {event['timestamp']} "
            f"{event['component']}/{event['event_type']}: {event['message']}",
            file=sys.stderr,
        )

    def _escalate(self, event: dict) -> None:
        key = (event["component"], event["event_type"])
        now = _utcnow()
        escalation = None
        with self._alert_lock:
            state = self._streaks.get(key)
            if state is None or (now - state["window_start"]).total_seconds() > self.repeat_window_seconds:
                state = {"window_start": now, "count": 0, "alerted": False}
                self._streaks[key] = state
            state["count"] += 1
            if state["count"] >= self.repeat_threshold and not state["alerted"]:
                state["alerted"] = True
                escalation = {
                    "event_id": str(uuid.uuid4()),
                    "timestamp": now.isoformat(),
                    "severity": "critical",
                    "component": event["component"],
                    "event_type": "repeat_failure_alert",
                    "message": (
                        f"{state['count']} repeated {event['event_type']} failures recorded for "
                        f"{event['component']} within the {self.repeat_window_seconds // 60 or 0}-minute alert window."
                    ),
                    "details": {
                        "repeat_count": state["count"],
                        "component": event["component"],
                        "watched_event_type": event["event_type"],
                        "triggering_event_id": event["event_id"],
                        "window_minutes": self.repeat_window_seconds // 60,
                    },
                    "traceback": None,
                    "alert": True,
                    "alert_type": "repeat_failures",
                    "repeat_count": state["count"],
                }
        if escalation is not None:
            self._append(escalation)
            self._mirror(escalation)

    # -- reading ---------------------------------------------------------------

    def _records(self) -> list[dict]:
        malformed: list[int] = []
        records = self.store.list(on_malformed=lambda line_number, _count: malformed.append(line_number))
        self.malformed_line_numbers = sorted(set(malformed))
        return records

    def list_events(self, limit: int = 60, severity: str | None = None) -> list[dict]:
        """Return the most recent events, newest first, skipping malformed lines."""
        records = self._records()
        if severity is not None:
            records = [record for record in records if record.get("severity") == severity]
        return list(reversed(records[-max(1, int(limit)):]))

    def counts(self) -> dict:
        return dict(Counter(record.get("severity") for record in self._records()))

    def alert_counts(self) -> dict:
        records = self._records()
        alerts = [record for record in records if record.get("alert") or record.get("alert_type")]
        return {
            "alert_total": len(alerts),
            "escalation_alerts": sum(1 for record in alerts if record.get("alert_type")),
        }

    def health(self, alert_window_minutes: int = 60, event_limit: int = 40) -> dict:
        """Summarize log state for the interface: counts, active alerts, recent events."""
        records = self._records()
        now = _utcnow()
        window = timedelta(minutes=alert_window_minutes)
        alerts = []
        for record in reversed(records):
            stamped = _parse_timestamp(record.get("timestamp"))
            if stamped is None or now - stamped > window:
                continue
            if record.get("alert") or record.get("alert_type"):
                alerts.append({key: value for key, value in record.items() if key != "traceback"})
        events = [
            {key: value for key, value in record.items() if key != "traceback"}
            for record in reversed(records[-max(1, int(event_limit)):])
        ]
        counts = dict(Counter(record.get("severity") for record in records))
        return {
            "generated_at": now.isoformat(),
            "alert_window_minutes": alert_window_minutes,
            "counts": counts,
            "malformed_lines": getattr(self, "malformed_line_numbers", []),
            "active_alerts": alerts,
            "events": events,
        }


EVENT_LOG = EventStore(DEFAULT_LOG_PATH)
