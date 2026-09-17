from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1]))


def test_agent_submit_copies_pdf_and_starts_local_workers(tmp_path: Path, monkeypatch) -> None:
    import job_cli
    from job_queue import JobStore

    source = tmp_path / "report.pdf"
    source.write_bytes(b"agent input")
    started: list[Path] = []
    monkeypatch.setattr(job_cli, "ensure_workers", lambda root: started.append(root))

    job_id = job_cli.submit_job([source], tmp_path / "queue", tmp_path / "state", tmp_path / "skill.zip", ocr_mode="off")

    job = JobStore(tmp_path / "queue").get(job_id)
    assert job["input_paths"][0] != source
    assert job["input_paths"][0].read_bytes() == b"agent input"
    assert job["ocr_mode"] == "off"
    assert started == [tmp_path / "queue"]
