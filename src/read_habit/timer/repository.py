"""JSON-backed persistence for :class:`ReadingSessionRecord` entities."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from read_habit.timer.models import ReadingSessionRecord, TimerStats

DEFAULT_SESSIONS_PATH = Path.home() / ".read-habit" / "sessions.json"

_SESSIONS_ADAPTER = TypeAdapter(list[ReadingSessionRecord])


class SessionRepository:
    """Stores reading sessions as a JSON array of objects in a single file.

    Parameters
    ----------
    path:
        Location of the JSON file. Defaults to
        ``~/.read-habit/sessions.json``. The file (and any missing parent
        directories) is created lazily on the first write.
    """

    def __init__(self, path: Path | None = None) -> None:
        self._path = path if path is not None else DEFAULT_SESSIONS_PATH

    @property
    def path(self) -> Path:
        """Return the path backing this repository."""
        return self._path

    def list(self) -> list[ReadingSessionRecord]:
        """Return all stored sessions, ordered by id."""
        return sorted(self._load(), key=lambda session: session.id)

    def add(self, stats: TimerStats, book_id: int | None = None) -> ReadingSessionRecord:
        """Create and persist a new session, assigning it the next free id."""
        sessions = self._load()
        next_id = max((session.id for session in sessions), default=0) + 1
        record = ReadingSessionRecord(id=next_id, book_id=book_id, stats=stats)
        sessions.append(record)
        self._save(sessions)
        return record

    def _load(self) -> list[ReadingSessionRecord]:
        if not self._path.exists():
            return []
        content = self._path.read_text(encoding="utf-8").strip()
        if not content:
            return []
        return _SESSIONS_ADAPTER.validate_json(content)

    def _save(self, sessions: list[ReadingSessionRecord]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = _SESSIONS_ADAPTER.dump_python(sessions, mode="json")
        self._path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
