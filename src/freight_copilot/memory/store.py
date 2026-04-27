"""SQLite-backed long-term memory.

Three tables, one db file:

  customer_notes — historical notes about a customer entity.
                   E.g., "Brookline Apparel — sometimes slow on
                   Commercial Invoice; expect 4–6h shipper response."

  shipment_notes — historical notes tied to a specific shipment.
                   E.g., "FRT-1042 — last time we triaged this lane,
                   broker held the queue for 18h."

  corrections    — explicit corrections the user made during a session
                   ("the customer is Platinum, not Gold"). Surfaced on
                   future turns for the same entity so the agent can
                   apply them without being told twice.

The store is multi-session: any AgentSession reads and writes the same
db file under data/memory.sqlite3. This is what gives us "long-term
memory across sessions" (vs Phase 3's in-memory MemorySaver, which is
only short-term).
"""

from __future__ import annotations

import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = _REPO_ROOT / "data" / "memory.sqlite3"


def _db_path() -> Path:
    """Resolve the memory db path. Honors MEMORY_DB env var for tests."""
    override = os.getenv("MEMORY_DB")
    return Path(override) if override else DEFAULT_DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS customer_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    customer_name   TEXT NOT NULL,
    note            TEXT NOT NULL,
    source_thread_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_customer_notes_customer
    ON customer_notes(customer_name);

CREATE TABLE IF NOT EXISTS shipment_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    shipment_id     TEXT NOT NULL,
    note            TEXT NOT NULL,
    source_thread_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_shipment_notes_shipment
    ON shipment_notes(shipment_id);

CREATE TABLE IF NOT EXISTS corrections (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              REAL NOT NULL,
    entity_kind     TEXT NOT NULL,    -- 'customer' / 'shipment' / 'general'
    entity_id       TEXT NOT NULL,
    correction      TEXT NOT NULL,    -- the verbatim correction the user gave
    source_thread_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_corrections_entity
    ON corrections(entity_kind, entity_id);
"""


@dataclass
class CustomerNote:
    ts: float
    customer_name: str
    note: str
    source_thread_id: str | None = None


@dataclass
class ShipmentNote:
    ts: float
    shipment_id: str
    note: str
    source_thread_id: str | None = None


@dataclass
class Correction:
    ts: float
    entity_kind: str  # 'customer' | 'shipment' | 'general'
    entity_id: str
    correction: str
    source_thread_id: str | None = None


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.commit()
        c.close()


def init_db() -> None:
    """Create tables if they don't already exist. Idempotent."""
    with _conn() as c:
        c.executescript(SCHEMA)


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


def add_customer_note(note: CustomerNote) -> int:
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO customer_notes (ts, customer_name, note, source_thread_id) "
            "VALUES (?, ?, ?, ?)",
            (note.ts, note.customer_name, note.note, note.source_thread_id),
        )
        return cur.lastrowid


def add_shipment_note(note: ShipmentNote) -> int:
    init_db()
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO shipment_notes (ts, shipment_id, note, source_thread_id) "
            "VALUES (?, ?, ?, ?)",
            (note.ts, note.shipment_id, note.note, note.source_thread_id),
        )
        return cur.lastrowid


def add_correction(c_: Correction) -> int:
    init_db()
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO corrections (ts, entity_kind, entity_id, correction, source_thread_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (c_.ts, c_.entity_kind, c_.entity_id, c_.correction, c_.source_thread_id),
        )
        return cur.lastrowid


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def list_customer_notes(customer_name: str, limit: int = 10) -> list[CustomerNote]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, customer_name, note, source_thread_id "
            "FROM customer_notes WHERE customer_name = ? "
            "ORDER BY ts DESC LIMIT ?",
            (customer_name, limit),
        ).fetchall()
    return [CustomerNote(**dict(r)) for r in rows]


def list_shipment_notes(shipment_id: str, limit: int = 10) -> list[ShipmentNote]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, shipment_id, note, source_thread_id "
            "FROM shipment_notes WHERE shipment_id = ? "
            "ORDER BY ts DESC LIMIT ?",
            (shipment_id, limit),
        ).fetchall()
    return [ShipmentNote(**dict(r)) for r in rows]


def list_corrections(
    entity_kind: str, entity_id: str, limit: int = 10
) -> list[Correction]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            "SELECT ts, entity_kind, entity_id, correction, source_thread_id "
            "FROM corrections WHERE entity_kind = ? AND entity_id = ? "
            "ORDER BY ts DESC LIMIT ?",
            (entity_kind, entity_id, limit),
        ).fetchall()
    return [Correction(**dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def now() -> float:
    return time.time()


def export_dict() -> dict:
    """Whole-db snapshot — used by tests + the ingest CLI script."""
    init_db()
    with _conn() as c:
        cn = [dict(r) for r in c.execute("SELECT * FROM customer_notes").fetchall()]
        sn = [dict(r) for r in c.execute("SELECT * FROM shipment_notes").fetchall()]
        co = [dict(r) for r in c.execute("SELECT * FROM corrections").fetchall()]
    return {"customer_notes": cn, "shipment_notes": sn, "corrections": co}


def reset_db() -> None:
    """Drop and recreate all tables. Used by `seed_memory.py`."""
    with _conn() as c:
        c.executescript(
            "DROP TABLE IF EXISTS customer_notes; "
            "DROP TABLE IF EXISTS shipment_notes; "
            "DROP TABLE IF EXISTS corrections;"
        )
        c.executescript(SCHEMA)


__all__ = [
    "CustomerNote",
    "ShipmentNote",
    "Correction",
    "init_db",
    "reset_db",
    "add_customer_note",
    "add_shipment_note",
    "add_correction",
    "list_customer_notes",
    "list_shipment_notes",
    "list_corrections",
    "now",
    "export_dict",
    "DEFAULT_DB_PATH",
]
