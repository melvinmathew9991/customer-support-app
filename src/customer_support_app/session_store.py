"""Saves a conversation so it survives a process restart (docs/Persistence-Design.md).

One SQLite row per session, rewritten as a whole after every turn. The schema is versioned
with PRAGMA user_version and brought up to date by the ordered migrations below.
"""
import json
import logging
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SessionStoreError(RuntimeError):
    """The database cannot be used as configured (for example, it is from a newer version)."""


@dataclass
class SessionRecord:
    session_id: str
    conversation_id: str
    node: str
    node_input: Optional[Dict[str, Any]]
    edge_fails: Dict[str, int]
    messages: List[Dict[str, str]]
    is_over: bool


def _create_sessions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE sessions (
            session_id      TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            node            TEXT NOT NULL,
            node_input      TEXT,
            edge_fails      TEXT NOT NULL,
            messages        TEXT NOT NULL,
            is_over         INTEGER NOT NULL,
            created_at      TEXT NOT NULL,
            updated_at      TEXT NOT NULL
        )
        """
    )


# Append only: the schema version is the number of migrations applied.
_MIGRATIONS = [_create_sessions_table]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


class SessionStore:
    def __init__(self, path: Union[str, Path]):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path, timeout=5)

    def _migrate(self) -> None:
        with closing(self._connect()) as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version > len(_MIGRATIONS):
                raise SessionStoreError(
                    f"{self._path} uses session schema {version}, but this version of the "
                    f"app only knows schema {len(_MIGRATIONS)}. Upgrade the app, or point "
                    "SESSION_DB_PATH at a different file."
                )
            for target, migration in enumerate(_MIGRATIONS[version:], start=version + 1):
                with conn:
                    conn.execute("BEGIN")
                    migration(conn)
                    conn.execute(f"PRAGMA user_version = {target}")

    def save(self, record: SessionRecord) -> None:
        now = _now()
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, conversation_id, node, node_input,
                                      edge_fails, messages, is_over, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    conversation_id = excluded.conversation_id,
                    node            = excluded.node,
                    node_input      = excluded.node_input,
                    edge_fails      = excluded.edge_fails,
                    messages        = excluded.messages,
                    is_over         = excluded.is_over,
                    updated_at      = excluded.updated_at
                """,
                (
                    record.session_id,
                    record.conversation_id,
                    record.node,
                    None if record.node_input is None else json.dumps(record.node_input),
                    json.dumps(record.edge_fails),
                    json.dumps(record.messages),
                    int(record.is_over),
                    now,
                    now,
                ),
            )

    def load(self, session_id: str) -> Optional[SessionRecord]:
        """The saved session, or None if there is none or its row cannot be read.

        A bad row logs a warning instead of raising: it must never stop the app opening.
        """
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT conversation_id, node, node_input, edge_fails, messages, is_over "
                "FROM sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        try:
            conversation_id, node, node_input, edge_fails, messages, is_over = row
            record = SessionRecord(
                session_id=session_id,
                conversation_id=str(conversation_id),
                node=str(node),
                node_input=None if node_input is None else json.loads(node_input),
                edge_fails=json.loads(edge_fails),
                messages=json.loads(messages),
                is_over=bool(is_over),
            )
            self._check_shape(record)
        except (ValueError, TypeError, KeyError) as error:
            logger.warning("Ignoring unreadable saved session %s: %s", session_id, error)
            return None
        return record

    @staticmethod
    def _check_shape(record: SessionRecord) -> None:
        if record.node_input is not None and not isinstance(record.node_input, dict):
            raise ValueError("node_input is not an object")
        if not isinstance(record.edge_fails, dict):
            raise ValueError("edge_fails is not an object")
        if not isinstance(record.messages, list) or not all(
            isinstance(m, dict) and "role" in m and "content" in m for m in record.messages
        ):
            raise ValueError("messages is not a list of role/content objects")

    def latest_unfinished(self) -> Optional[str]:
        """The id of the most recently updated session that has not ended, if any."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT session_id FROM sessions WHERE is_over = 0 "
                "ORDER BY updated_at DESC, rowid DESC LIMIT 1"
            ).fetchone()
        return None if row is None else row[0]
