"""SQLite-backed skill registry."""
from __future__ import annotations
import json
import sqlite3
import uuid
from pathlib import Path
from typing import List, Optional

from scientia.models import SkillRecord


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS skills (
    skill_id TEXT PRIMARY KEY,
    tool_name TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    source_type TEXT NOT NULL,
    skill_dir TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    sample_output TEXT,
    generated_at TEXT NOT NULL,
    last_verified_at TEXT,
    quality_score INTEGER,
    tags TEXT NOT NULL DEFAULT '[]'
);
"""

# Migration: add new columns to existing databases
_MIGRATIONS = [
    "ALTER TABLE skills ADD COLUMN quality_score INTEGER",
    "ALTER TABLE skills ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'",
]


def _row_to_record(row: sqlite3.Row) -> SkillRecord:
    keys = row.keys()
    quality_score = row["quality_score"] if "quality_score" in keys else None
    tags_raw = row["tags"] if "tags" in keys else "[]"
    try:
        tags = json.loads(tags_raw) if tags_raw else []
    except (json.JSONDecodeError, TypeError):
        tags = []
    return SkillRecord(
        skill_id=row["skill_id"],
        tool_name=row["tool_name"],
        source=row["source"],
        source_type=row["source_type"],
        skill_dir=row["skill_dir"],
        verification_status=row["verification_status"],
        retry_count=row["retry_count"],
        sample_output=row["sample_output"],
        generated_at=row["generated_at"],
        last_verified_at=row["last_verified_at"],
        quality_score=quality_score,
        tags=tags,
    )


class Registry:
    def __init__(self, db_path: Path) -> None:
        self._path = Path(db_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)
            self._run_migrations(conn)

    def _run_migrations(self, conn: sqlite3.Connection) -> None:
        for sql in _MIGRATIONS:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass  # column already exists

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, record: SkillRecord) -> str:
        skill_id = record.skill_id or str(uuid.uuid4())
        tags_json = json.dumps(record.tags or [])
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO skills
                    (skill_id, tool_name, source, source_type, skill_dir,
                     verification_status, retry_count, sample_output,
                     generated_at, last_verified_at, quality_score, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(tool_name) DO UPDATE SET
                    skill_id = excluded.skill_id,
                    source = excluded.source,
                    source_type = excluded.source_type,
                    skill_dir = excluded.skill_dir,
                    verification_status = excluded.verification_status,
                    retry_count = excluded.retry_count,
                    sample_output = excluded.sample_output,
                    generated_at = excluded.generated_at,
                    last_verified_at = excluded.last_verified_at,
                    quality_score = excluded.quality_score,
                    tags = excluded.tags
                """,
                (
                    skill_id,
                    record.tool_name,
                    record.source,
                    record.source_type,
                    record.skill_dir,
                    record.verification_status,
                    record.retry_count,
                    record.sample_output,
                    record.generated_at,
                    record.last_verified_at,
                    record.quality_score,
                    tags_json,
                ),
            )
        return skill_id

    # ------------------------------------------------------------------
    # Aliases used in tests: load() == get_by_id()
    # ------------------------------------------------------------------
    def load(self, skill_id: str) -> Optional[SkillRecord]:
        return self.get_by_id(skill_id)

    def get_by_tool_name(self, tool_name: str) -> Optional[SkillRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM skills WHERE tool_name = ?", (tool_name,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def get_by_id(self, skill_id: str) -> Optional[SkillRecord]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM skills WHERE skill_id = ?", (skill_id,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def list_all(self, verified_only: bool = False) -> List[SkillRecord]:
        query = "SELECT * FROM skills"
        if verified_only:
            query += " WHERE verification_status = 'verified'"
        with self._connect() as conn:
            rows = conn.execute(query).fetchall()
        return [_row_to_record(r) for r in rows]

    def search(
        self,
        tag: Optional[str] = None,
        min_score: Optional[int] = None,
        verified_only: bool = False,
    ) -> List[SkillRecord]:
        """Return records filtered by tag, min quality score, and/or verified status."""
        records = self.list_all(verified_only=verified_only)
        if tag is not None:
            records = [r for r in records if tag in r.tags]
        if min_score is not None:
            records = [r for r in records if r.quality_score is not None and r.quality_score >= min_score]
        return records

    def delete(self, tool_name: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM skills WHERE tool_name = ?", (tool_name,))
