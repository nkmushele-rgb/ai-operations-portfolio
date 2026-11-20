"""Thin SQLite helpers shared by all three projects.

Every project keeps its own database file, but the connection, insert and
query helpers are identical, so they live here once.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any, Iterable


def connect(path: str) -> sqlite3.Connection:
    """Open (and create the folder for) a SQLite database."""
    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(con: sqlite3.Connection, schema_sql: str) -> None:
    con.executescript(schema_sql)
    con.commit()


def execute(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
    cur = con.execute(sql, tuple(params))
    con.commit()
    return cur


def insert(con: sqlite3.Connection, table: str, row: dict) -> int:
    """Insert one dict and return the new row id."""
    cols = list(row)
    placeholders = ",".join("?" * len(cols))
    sql = f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    cur = con.execute(sql, tuple(row[c] for c in cols))
    con.commit()
    return int(cur.lastrowid)


def rows(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> list[dict]:
    return [dict(r) for r in con.execute(sql, tuple(params)).fetchall()]


def one(con: sqlite3.Connection, sql: str, params: Iterable[Any] = ()) -> dict | None:
    r = con.execute(sql, tuple(params)).fetchone()
    return dict(r) if r else None


def scalar(con: sqlite3.Connection, sql: str, params: Iterable[Any] = (), default: Any = 0) -> Any:
    r = con.execute(sql, tuple(params)).fetchone()
    if r is None or r[0] is None:
        return default
    return r[0]


def reset(con: sqlite3.Connection, tables: list[str]) -> None:
    """Empty the given tables, for repeatable demos and tests."""
    for table in tables:
        con.execute(f"DELETE FROM {table}")
    # Keep row ids predictable between demo runs.
    try:
        placeholders = ",".join("?" * len(tables))
        con.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", tuple(tables))
    except sqlite3.OperationalError:
        pass  # no AUTOINCREMENT table has been written yet
    con.commit()
