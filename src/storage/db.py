"""SQLite audit trail.

Every arbitration is persisted in full — the inputs, plus the complete Verdict
(which itself carries the raw critic reports and detected disagreements). Any
verdict can therefore be re-fetched by ID and replayed/audited later. This durable
trail is part of the system's pitch, not just plumbing.

Storage is intentionally simple: one row per arbitration, the Verdict serialized
as JSON via Pydantic so a round-trip reproduces the object exactly.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from src.schemas.verdict import Verdict

DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "arbitrations.db"


def _db_path() -> Path:
    return Path(os.getenv("ARBITRATION_DB_PATH", str(DEFAULT_DB_PATH)))


class ArbitrationRecord(BaseModel):
    id: str
    created_at: str  # ISO-8601 UTC
    original_prompt: Optional[str]
    llm_output: str
    verdict: Verdict


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS arbitrations (
                id              TEXT PRIMARY KEY,
                created_at      TEXT NOT NULL,
                original_prompt TEXT,
                llm_output      TEXT NOT NULL,
                verdict_json    TEXT NOT NULL
            )
            """
        )


def save_arbitration(
    llm_output: str,
    original_prompt: Optional[str],
    verdict: Verdict,
    *,
    arbitration_id: Optional[str] = None,
    created_at: Optional[str] = None,
) -> ArbitrationRecord:
    """Persist one arbitration and return the stored record (with its assigned id)."""
    init_db()
    rec = ArbitrationRecord(
        id=arbitration_id or str(uuid.uuid4()),
        created_at=created_at or datetime.now(timezone.utc).isoformat(),
        original_prompt=original_prompt,
        llm_output=llm_output,
        verdict=verdict,
    )
    with _connect() as conn:
        conn.execute(
            "INSERT INTO arbitrations (id, created_at, original_prompt, llm_output, verdict_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (rec.id, rec.created_at, rec.original_prompt, rec.llm_output, verdict.model_dump_json()),
        )
    return rec


def _row_to_record(row: sqlite3.Row) -> ArbitrationRecord:
    return ArbitrationRecord(
        id=row["id"],
        created_at=row["created_at"],
        original_prompt=row["original_prompt"],
        llm_output=row["llm_output"],
        verdict=Verdict.model_validate_json(row["verdict_json"]),
    )


def get_arbitration(arbitration_id: str) -> Optional[ArbitrationRecord]:
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM arbitrations WHERE id = ?", (arbitration_id,)
        ).fetchone()
    return _row_to_record(row) if row else None


def list_arbitrations(limit: Optional[int] = None) -> List[ArbitrationRecord]:
    init_db()
    query = "SELECT * FROM arbitrations ORDER BY created_at DESC"
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    with _connect() as conn:
        rows = conn.execute(query).fetchall()
    return [_row_to_record(r) for r in rows]
