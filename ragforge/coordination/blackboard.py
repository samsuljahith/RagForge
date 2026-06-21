"""
Blackboard: a shared key/value workspace for multi-agent coordination.

The Blackboard is the central coordination primitive. Agents NEVER talk to each
other directly — they only read/write the blackboard. This is cheaper than
direct messaging because:
  1. No full-context re-sends between agents (each read is targeted)
  2. Shared state persists across crashes (SQLite-backed)
  3. Every write is logged with author, timestamp, and version — fully traceable

Each entry carries:
  - key: string identifier
  - value: any JSON-serializable data
  - author: agent id that wrote it
  - timestamp: when it was written (ISO 8601)
  - tags: lightweight markers/pheromones (e.g. status="needs_review", confidence=0.4)
  - version: auto-incrementing per key (for conflict detection)

Concurrency safety: uses SQLite's built-in locking (WAL mode for readers +
exclusive lock on writes). Last-write-wins with version tracking so agents
can detect conflicts if needed.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class BlackboardEntry:
    """One entry on the blackboard."""

    key: str
    value: Any
    author: str
    timestamp: str
    tags: dict[str, Any] = field(default_factory=dict)
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict."""
        return {
            "key": self.key,
            "value": self.value,
            "author": self.author,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlackboardEntry":
        return cls(
            key=data["key"],
            value=data["value"],
            author=data["author"],
            timestamp=data["timestamp"],
            tags=data.get("tags", {}),
            version=data.get("version", 1),
        )

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "BlackboardEntry":
        return cls(
            key=row["key"],
            value=json.loads(row["value"]),
            author=row["author"],
            timestamp=row["timestamp"],
            tags=json.loads(row["tags"]),
            version=row["version"],
        )


class Blackboard:
    """
    A shared key/value workspace for multi-agent coordination.

    Backed by SQLite for persistence (survives crashes) and concurrency safety.
    All writes are logged to a history table for tracing and replay.

    Usage:
        board = Blackboard("my-task")
        board.write("findings", {"data": "..."}, author="researcher", tags={"confidence": 0.9})
        entry = board.read("findings")
        entries = board.read_by_tag("confidence", lambda v: v > 0.5)
        history = board.history()
    """

    def __init__(self, name: str, persist_dir: Optional[str | Path] = None) -> None:
        """
        Args:
            name: Name of this blackboard (used as filename for persistence).
            persist_dir: Directory for the SQLite file. Defaults to .ragforge/boards/.
        """
        self.name = name
        self._lock = threading.Lock()

        if persist_dir is None:
            persist_dir = Path.home() / ".ragforge" / "boards"
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._persist_dir / f"{name}.db"

        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                author TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                author TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '{}',
                version INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_history_key ON history(key);
            CREATE INDEX IF NOT EXISTS idx_history_author ON history(author);
            CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp);
        """)
        self._conn.commit()

    def write(
        self,
        key: str,
        value: Any,
        author: str,
        tags: Optional[dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """
        Write an entry to the blackboard.

        If the key already exists, its version is incremented (last-write-wins).
        Every write is also appended to the history log for tracing.

        Args:
            key: Entry identifier.
            value: Any JSON-serializable data.
            author: Agent ID performing the write.
            tags: Optional markers/pheromones (e.g. {"status": "needs_review"}).

        Returns:
            The BlackboardEntry as written.
        """
        if tags is None:
            tags = {}

        ts = datetime.now(timezone.utc).isoformat()
        value_json = json.dumps(value)
        tags_json = json.dumps(tags)

        with self._lock:
            # Get current version for this key (if exists)
            row = self._conn.execute(
                "SELECT version FROM entries WHERE key = ?", (key,)
            ).fetchone()
            new_version = (row["version"] + 1) if row else 1

            # Upsert the current entry
            self._conn.execute(
                """INSERT INTO entries (key, value, author, timestamp, tags, version)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                     value = excluded.value,
                     author = excluded.author,
                     timestamp = excluded.timestamp,
                     tags = excluded.tags,
                     version = excluded.version""",
                (key, value_json, author, ts, tags_json, new_version),
            )

            # Append to history (immutable log)
            self._conn.execute(
                """INSERT INTO history (key, value, author, timestamp, tags, version)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (key, value_json, author, ts, tags_json, new_version),
            )
            self._conn.commit()

        return BlackboardEntry(
            key=key,
            value=value,
            author=author,
            timestamp=ts,
            tags=tags,
            version=new_version,
        )

    def read(self, key: str) -> Optional[BlackboardEntry]:
        """
        Read the current value for a key.

        Returns None if the key doesn't exist (agent can decide how to handle).
        """
        row = self._conn.execute(
            "SELECT * FROM entries WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        return BlackboardEntry.from_row(row)

    def read_all(self) -> list[BlackboardEntry]:
        """Read all current entries on the blackboard."""
        rows = self._conn.execute("SELECT * FROM entries ORDER BY key").fetchall()
        return [BlackboardEntry.from_row(r) for r in rows]

    def read_by_tag(
        self,
        tag_key: str,
        predicate: Optional[Callable[[Any], bool]] = None,
    ) -> list[BlackboardEntry]:
        """
        Read entries that have a specific tag, optionally filtered by a predicate.

        Args:
            tag_key: The tag name to look for.
            predicate: Optional function that takes the tag's value and returns True/False.
                       If None, returns all entries that have the tag (regardless of value).

        Example:
            board.read_by_tag("confidence", lambda v: v > 0.7)
            board.read_by_tag("status")  # all entries with a "status" tag
        """
        entries = self.read_all()
        results = []
        for entry in entries:
            if tag_key in entry.tags:
                if predicate is None or predicate(entry.tags[tag_key]):
                    results.append(entry)
        return results

    def read_by_author(self, author: str) -> list[BlackboardEntry]:
        """Read all current entries written by a specific agent."""
        rows = self._conn.execute(
            "SELECT * FROM entries WHERE author = ? ORDER BY key", (author,)
        ).fetchall()
        return [BlackboardEntry.from_row(r) for r in rows]

    def watch(self, predicate: Callable[[BlackboardEntry], bool]) -> list[BlackboardEntry]:
        """
        Poll the blackboard for entries matching a predicate.

        This is a one-shot check (not a blocking wait). The orchestrator calls this
        repeatedly to check agent trigger conditions.

        Args:
            predicate: Function that takes a BlackboardEntry and returns True if it matches.

        Returns:
            All current entries satisfying the predicate.
        """
        return [e for e in self.read_all() if predicate(e)]

    def keys(self) -> list[str]:
        """List all keys currently on the blackboard."""
        rows = self._conn.execute("SELECT key FROM entries ORDER BY key").fetchall()
        return [r["key"] for r in rows]

    def has_key(self, key: str) -> bool:
        """Check if a key exists on the blackboard."""
        row = self._conn.execute(
            "SELECT 1 FROM entries WHERE key = ?", (key,)
        ).fetchone()
        return row is not None

    def delete(self, key: str) -> bool:
        """Remove an entry from the blackboard (does NOT remove from history)."""
        with self._lock:
            cursor = self._conn.execute("DELETE FROM entries WHERE key = ?", (key,))
            self._conn.commit()
            return cursor.rowcount > 0

    def clear(self) -> None:
        """Clear all current entries (history is preserved)."""
        with self._lock:
            self._conn.execute("DELETE FROM entries")
            self._conn.commit()

    def history(self, key: Optional[str] = None, limit: int = 100) -> list[BlackboardEntry]:
        """
        Get the write history (all writes ever, in order).

        Args:
            key: If provided, only history for this key. Otherwise all history.
            limit: Maximum number of entries to return (most recent first).

        Returns:
            List of BlackboardEntry objects representing past writes.
        """
        if key:
            rows = self._conn.execute(
                "SELECT * FROM history WHERE key = ? ORDER BY id DESC LIMIT ?",
                (key, limit),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [BlackboardEntry.from_row(r) for r in reversed(rows)]

    def history_count(self) -> int:
        """Total number of writes in the history."""
        row = self._conn.execute("SELECT COUNT(*) as cnt FROM history").fetchone()
        return row["cnt"]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the full current state to a dict."""
        return {
            "name": self.name,
            "entries": [e.to_dict() for e in self.read_all()],
            "history_count": self.history_count(),
        }

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> "Blackboard":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def __repr__(self) -> str:
        n = len(self.keys())
        return f"Blackboard(name={self.name!r}, entries={n}, db={self._db_path})"


class InMemoryBlackboard(Blackboard):
    """
    An in-memory blackboard (no persistence) for testing and ephemeral tasks.

    Same API as Blackboard but uses SQLite :memory: — faster, no disk I/O,
    lost when the process exits.
    """

    def __init__(self, name: str = "ephemeral") -> None:
        self.name = name
        self._lock = threading.Lock()
        self._persist_dir = None
        self._db_path = ":memory:"
        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
