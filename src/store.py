"""Deduplikacja ogloszen w SQLite - digest pokazuje tylko NOWE."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .bk_client import Announcement

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    id TEXT PRIMARY KEY,
    number TEXT,
    title TEXT,
    first_seen TEXT
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def _key(ann: Announcement) -> str:
    return ann.id or f"{ann.number}|{ann.title}"


def filter_new(
    conn: sqlite3.Connection, anns: list[Announcement]
) -> list[Announcement]:
    """Zwraca tylko te ogloszenia, ktorych nie ma jeszcze w bazie."""
    cur = conn.cursor()
    new = []
    for ann in anns:
        k = _key(ann)
        cur.execute("SELECT 1 FROM seen WHERE id = ?", (k,))
        if cur.fetchone() is None:
            new.append(ann)
    return new


def mark_seen(conn: sqlite3.Connection, anns: list[Announcement]) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT OR IGNORE INTO seen (id, number, title, first_seen) VALUES (?, ?, ?, ?)",
        [(_key(a), a.number, a.title, ts) for a in anns],
    )
    conn.commit()


def count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM seen").fetchone()[0]
