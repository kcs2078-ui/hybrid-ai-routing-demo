"""Bounded SQLite conversation-memory example using only synthetic/local data."""

from __future__ import annotations

import os
import sqlite3
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MemoryRecord:
    session_id: str
    user_text: str
    assistant_text: str
    created_at: str


class MemoryRejected(ValueError):
    """Input or storage does not meet the local demo contract."""


class ConversationMemory:
    """A small local store; defaults to ephemeral in-memory SQLite."""

    def __init__(self, database: str | Path = ":memory:", *, max_results: int = 20) -> None:
        if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 100:
            raise MemoryRejected("max_results must be between 1 and 100")
        self._max_results = max_results
        if str(database) == ":memory:":
            self._connection = sqlite3.connect(":memory:")
        else:
            path = Path(database)
            self._validate_database_path(path)
            if path.exists():
                self._validate_database_file(path)
            else:
                flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                try:
                    fd = os.open(path, flags, 0o600)
                    os.close(fd)
                except FileExistsError:
                    self._validate_database_file(path)
                except OSError:
                    raise MemoryRejected("database file could not be created safely") from None
            self._validate_database_file(path)
            self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=DELETE")
        self._connection.execute(
            """CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            )"""
        )
        self._connection.execute("CREATE INDEX IF NOT EXISTS turns_session_id ON turns(session_id, id)")
        self._connection.commit()

    @staticmethod
    def _validate_database_path(path: Path) -> None:
        if not path.is_absolute() or path.name in {"", ".", ".."}:
            raise MemoryRejected("database path must be an absolute file path")
        parent = path.parent
        try:
            parent_info = parent.lstat()
        except OSError:
            raise MemoryRejected("database parent must already exist") from None
        if stat.S_ISLNK(parent_info.st_mode) or not stat.S_ISDIR(parent_info.st_mode):
            raise MemoryRejected("database parent must be a real directory")
        if parent_info.st_uid != os.getuid() or stat.S_IMODE(parent_info.st_mode) != 0o700:
            raise MemoryRejected("database parent must be caller-owned with mode 0700")

    @staticmethod
    def _validate_database_file(path: Path) -> None:
        try:
            info = path.lstat()
        except OSError:
            raise MemoryRejected("database file is unavailable") from None
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise MemoryRejected("database file must be caller-owned, regular, and mode 0600")

    @staticmethod
    def _validate_text(value: str, label: str, limit: int) -> None:
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise MemoryRejected(f"{label} is empty or exceeds its limit")

    def save(self, session_id: str, user_text: str, assistant_text: str) -> None:
        self._validate_text(session_id, "session_id", 128)
        self._validate_text(user_text, "user_text", 4_000)
        self._validate_text(assistant_text, "assistant_text", 4_000)
        self._connection.execute(
            "INSERT INTO turns(session_id, user_text, assistant_text) VALUES (?, ?, ?)",
            (session_id, user_text, assistant_text),
        )
        self._connection.commit()

    def search(self, query: str, *, session_id: str | None = None, limit: int | None = None) -> list[MemoryRecord]:
        self._validate_text(query, "query", 256)
        if session_id is not None:
            self._validate_text(session_id, "session_id", 128)
        bound = self._max_results if limit is None else limit
        if not isinstance(bound, int) or isinstance(bound, bool) or not 1 <= bound <= self._max_results:
            raise MemoryRejected("limit exceeds the configured result bound")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        if session_id is None:
            rows = self._connection.execute(
                """SELECT session_id, user_text, assistant_text, created_at FROM turns
                   WHERE user_text LIKE ? ESCAPE '\\' OR assistant_text LIKE ? ESCAPE '\\'
                   ORDER BY id DESC LIMIT ?""",
                (pattern, pattern, bound),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """SELECT session_id, user_text, assistant_text, created_at FROM turns
                   WHERE session_id = ? AND (user_text LIKE ? ESCAPE '\\' OR assistant_text LIKE ? ESCAPE '\\')
                   ORDER BY id DESC LIMIT ?""",
                (session_id, pattern, pattern, bound),
            ).fetchall()
        return [MemoryRecord(**dict(row)) for row in rows]

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "ConversationMemory":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
