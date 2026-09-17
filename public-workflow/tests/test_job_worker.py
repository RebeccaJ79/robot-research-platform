from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1]))


def test_worker_completes_queued_job_and_writes_zip(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import EvidenceBundle
    from job_queue import JobStore
    import job_worker

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    store = JobStore(tmp_path / "queue")
    job_id = store.enqueue([source], tmp_path / "state", tmp_path / "skill-package.zip")
    bundle = EvidenceBundle(documents=[], evidence=[])
    monkeypatch.setattr(job_worker, "build_evidence_bundle", lambda *_args, **_kwargs: bundle)
    monkeypatch.setattr(job_worker, "request_updates", lambda *_args, **_kwargs: [])

    result = job_worker.process_one_job(store, "worker-1")

    assert result["id"] == job_id
    assert result["status"] == "completed"
    assert result["output_path"].is_file()


def test_ensure_workers_starts_missing_local_processes(tmp_path: Path, monkeypatch) -> None:
    import job_worker

    launched: list[list[str]] = []
    monkeypatch.setattr(job_worker, "_is_worker_running", lambda _worker: False)
    monkeypatch.setattr(job_worker.subprocess, "Popen", lambda command, **_kwargs: launched.append(command))

    worker_ids = job_worker.ensure_workers(tmp_path / "queue", count=2)

    assert worker_ids == ["worker-1", "worker-2"]
    assert len(launched) == 2
    assert all("--queue-root" in command and "--worker-id" in command for command in launched)


def test_worker_failure_keeps_private_path_out_of_task_status(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import EvidenceBundle
    from job_queue import JobStore
    import job_worker

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    store = JobStore(tmp_path / "queue")
    job_id = store.enqueue([source], tmp_path / "state", tmp_path / "skill-package.zip")
    monkeypatch.setattr(job_worker, "build_evidence_bundle", lambda *_args, **_kwargs: EvidenceBundle(documents=[], evidence=[]))
    monkeypatch.setattr(job_worker, "request_updates", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("C:\\private\\report.pdf")))

    result = job_worker.process_one_job(store, "worker-1")

    assert result["id"] == job_id
    assert result["status"] == "failed"
    assert result["error_code"] == "RUNTIMEERROR"
