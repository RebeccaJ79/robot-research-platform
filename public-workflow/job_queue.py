"""Persistent, local-only task queue for PDF-to-Skill jobs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class JobStore:
    """Coordinate local workers while allowing only one writer per Skill state."""

    def __init__(self, queue_root: Path) -> None:
        self.queue_root = Path(queue_root)
        self.queue_root.mkdir(parents=True, exist_ok=True)
        self.database = self.queue_root / "jobs.sqlite3"
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    input_paths TEXT NOT NULL,
                    state_dir TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    ocr_mode TEXT NOT NULL DEFAULT 'auto',
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    current_pdf TEXT,
                    completed_files INTEGER NOT NULL DEFAULT 0,
                    total_files INTEGER NOT NULL,
                    progress REAL NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    error_code TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS workers (
                    id TEXT PRIMARY KEY,
                    pid INTEGER NOT NULL,
                    heartbeat_at TEXT NOT NULL
                );
                """
            )
            columns = {str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)").fetchall()}
            if "ocr_mode" not in columns:
                connection.execute("ALTER TABLE jobs ADD COLUMN ocr_mode TEXT NOT NULL DEFAULT 'auto'")

    def enqueue(self, input_paths: list[Path], state_dir: Path, output_path: Path, *, ocr_mode: str = "auto") -> str:
        if not input_paths:
            raise ValueError("PDF_REQUIRED")
        if ocr_mode not in {"auto", "off", "force"}:
            raise ValueError("OCR_MODE_INVALID")
        job_id = uuid.uuid4().hex
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO jobs (
                    id, input_paths, state_dir, output_path, ocr_mode, status, stage, total_files, created_at
                ) VALUES (?, ?, ?, ?, ?, 'queued', '排队中', ?, ?)""",
                (job_id, json.dumps([str(Path(path)) for path in input_paths]), str(Path(state_dir)), str(Path(output_path)), ocr_mode, len(input_paths), _now()),
            )
        return job_id

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """SELECT * FROM jobs AS candidate
                WHERE candidate.status = 'queued'
                  AND NOT EXISTS (
                    SELECT 1 FROM jobs AS running
                    WHERE running.status = 'running' AND running.state_dir = candidate.state_dir
                  )
                ORDER BY candidate.rowid
                LIMIT 1"""
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                "UPDATE jobs SET status='running', stage='等待解析', worker_id=?, started_at=? WHERE id=?",
                (worker_id, _now(), row["id"]),
            )
            return self.get(str(row["id"]), connection=connection)

    def update_progress(
        self,
        job_id: str,
        *,
        stage: str,
        current_pdf: str | None = None,
        completed_files: int | None = None,
        total_files: int | None = None,
        progress: float | None = None,
    ) -> None:
        updates: dict[str, Any] = {"stage": stage}
        if current_pdf is not None:
            updates["current_pdf"] = current_pdf
        if completed_files is not None:
            updates["completed_files"] = completed_files
        if total_files is not None:
            updates["total_files"] = total_files
        if progress is not None:
            updates["progress"] = max(0.0, min(1.0, progress))
        columns = ", ".join(f"{name}=?" for name in updates)
        with self._connect() as connection:
            connection.execute(f"UPDATE jobs SET {columns} WHERE id=?", (*updates.values(), job_id))

    def complete(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status='completed', stage='已完成', progress=1, finished_at=? WHERE id=?",
                (_now(), job_id),
            )

    def fail(self, job_id: str, error_code: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE jobs SET status='failed', stage='失败', error_code=?, finished_at=? WHERE id=?",
                (error_code[:300], _now(), job_id),
            )

    def register_worker(self, worker_id: str, pid: int) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO workers (id, pid, heartbeat_at) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET pid=excluded.pid, heartbeat_at=excluded.heartbeat_at",
                (worker_id, pid, _now()),
            )

    def heartbeat(self, worker_id: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE workers SET heartbeat_at=? WHERE id=?", (_now(), worker_id))

    def get(self, job_id: str, *, connection: sqlite3.Connection | None = None) -> dict[str, Any]:
        if connection is None:
            with self._connect() as owned:
                return self.get(job_id, connection=owned)
        row = connection.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job_dict(row)

    def list_jobs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._job_dict(row) for row in rows]

    def workers(self, *, heartbeat_max_age_seconds: int = 5) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = [dict(row) for row in connection.execute("SELECT * FROM workers ORDER BY id").fetchall()]
        cutoff = datetime.now(UTC) - timedelta(seconds=heartbeat_max_age_seconds)
        return [row for row in rows if datetime.fromisoformat(str(row["heartbeat_at"])) >= cutoff]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _job_dict(row: sqlite3.Row) -> dict[str, Any]:
        job = dict(row)
        job["input_paths"] = [Path(value) for value in json.loads(job["input_paths"])]
        for field in ("state_dir", "output_path"):
            job[field] = Path(job[field])
        return job
