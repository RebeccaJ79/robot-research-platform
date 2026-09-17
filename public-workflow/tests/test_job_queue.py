from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1]))


def test_queue_serializes_one_skill_state_but_allows_other_states(tmp_path: Path) -> None:
    from job_queue import JobStore

    store = JobStore(tmp_path / "queue")
    first = store.enqueue([tmp_path / "a.pdf"], tmp_path / "state-a", tmp_path / "a.zip")
    second = store.enqueue([tmp_path / "b.pdf"], tmp_path / "state-a", tmp_path / "b.zip")
    third = store.enqueue([tmp_path / "c.pdf"], tmp_path / "state-b", tmp_path / "c.zip")

    claimed_first = store.claim_next("worker-1")
    claimed_second = store.claim_next("worker-2")

    assert claimed_first["id"] == first
    assert claimed_second["id"] == third
    assert store.get(second)["status"] == "queued"


def test_queue_reports_current_pdf_and_progress(tmp_path: Path) -> None:
    from job_queue import JobStore

    store = JobStore(tmp_path / "queue")
    job_id = store.enqueue([tmp_path / "a.pdf", tmp_path / "b.pdf"], tmp_path / "state", tmp_path / "skill.zip")
    store.claim_next("worker-1")
    store.update_progress(job_id, stage="解析 PDF", current_pdf="a.pdf", completed_files=1, total_files=2, progress=0.35)

    job = store.get(job_id)

    assert job["worker_id"] == "worker-1"
    assert job["stage"] == "解析 PDF"
    assert job["current_pdf"] == "a.pdf"
    assert job["completed_files"] == 1
    assert job["progress"] == 0.35


def test_queue_preserves_the_requested_ocr_mode(tmp_path: Path) -> None:
    from job_queue import JobStore

    store = JobStore(tmp_path / "queue")
    job_id = store.enqueue([tmp_path / "scan.pdf"], tmp_path / "state", tmp_path / "skill.zip", ocr_mode="force")

    assert store.get(job_id)["ocr_mode"] == "force"


def test_queue_hides_workers_with_expired_heartbeats(tmp_path: Path) -> None:
    from job_queue import JobStore

    store = JobStore(tmp_path / "queue")
    store.register_worker("worker-1", 1234)
    stale = (datetime.now(UTC) - timedelta(seconds=30)).isoformat(timespec="seconds")
    with store._connect() as connection:
        connection.execute("UPDATE workers SET heartbeat_at=? WHERE id='worker-1'", (stale,))

    assert store.workers() == []
