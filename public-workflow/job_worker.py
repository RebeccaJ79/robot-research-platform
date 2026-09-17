"""Local background worker for queued PDF-to-Skill jobs."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

from evidence_pipeline import build_evidence_bundle
from job_queue import JobStore
from skill_cli import fresh_pdf_paths, request_updates, run
from skill_package import load_skill_context


def _windows_pid_running(pid: int) -> bool:
    """Use the Windows process handle API when os.kill(pid, 0) is unreliable."""
    if os.name != "nt":
        return False
    try:
        import ctypes

        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    except (AttributeError, OSError):
        return False


def _is_worker_running(worker: dict[str, Any] | None) -> bool:
    if not worker:
        return False
    try:
        os.kill(int(worker["pid"]), 0)
    except SystemError:
        return _windows_pid_running(int(worker["pid"]))
    except (OSError, ValueError, TypeError):
        return False
    return True


def ensure_workers(queue_root: Path, *, count: int = 2) -> list[str]:
    """Start missing local workers; existing live workers are reused."""
    store = JobStore(queue_root)
    existing = {str(worker["id"]): worker for worker in store.workers(include_stale=True)}
    worker_ids = [f"worker-{index}" for index in range(1, count + 1)]
    for worker_id in worker_ids:
        if _is_worker_running(existing.get(worker_id)):
            store.heartbeat(worker_id)
            continue
        subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "--queue-root", str(Path(queue_root)), "--worker-id", worker_id],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    return worker_ids


def process_one_job(store: JobStore, worker_id: str) -> dict[str, Any] | None:
    """Claim and execute one job, retaining a safe error code for the monitor."""
    job = store.claim_next(worker_id)
    if job is None:
        return None
    job_id = str(job["id"])
    stop_heartbeat = threading.Event()

    def keep_lease_alive() -> None:
        while not stop_heartbeat.wait(2):
            store.heartbeat(worker_id)
            store.heartbeat_job(job_id)

    heartbeat_thread = threading.Thread(target=keep_lease_alive, daemon=True)
    heartbeat_thread.start()

    def progress(event: dict[str, object]) -> None:
        store.update_progress(
            job_id,
            stage=str(event["stage"]),
            current_pdf=str(event["file_name"]),
            completed_files=int(event["completed_files"]),
            total_files=int(event["total_files"]),
            progress=float(event["progress"]),
            current_page=int(event["current_page"]) if event.get("current_page") is not None else None,
            total_pages=int(event["total_pages"]) if event.get("total_pages") is not None else None,
        )

    try:
        input_paths = list(job["input_paths"])
        fresh = fresh_pdf_paths(input_paths, job["state_dir"])
        if fresh:
            bundle = build_evidence_bundle(fresh, job["state_dir"], ocr_mode=str(job["ocr_mode"]), progress_callback=progress)
            store.update_progress(job_id, stage="请求模型", progress=0.68)
            updates = request_updates(bundle, load_skill_context(job["state_dir"]))
            store.update_progress(job_id, stage="模型校验完成", progress=0.84)
        else:
            updates = []
            store.update_progress(job_id, stage="复用已有 PDF", progress=0.84)
        store.update_progress(job_id, stage="导出 Skill ZIP", progress=0.92)
        run(input_paths, job["state_dir"], job["output_path"], updates, text_extractor=lambda _path: "prepared local evidence")
        store.complete(job_id)
    except Exception as error:
        message = str(error).strip()
        error_code = message if message.replace("_", "").isalnum() and message.upper() == message else type(error).__name__.upper()
        store.fail(job_id, error_code)
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
    return store.get(job_id)


def worker_loop(queue_root: Path, worker_id: str, *, poll_seconds: float = 0.5) -> None:
    store = JobStore(queue_root)
    store.register_worker(worker_id, os.getpid())
    while True:
        store.heartbeat(worker_id)
        if process_one_job(store, worker_id) is None:
            time.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one local PDF-to-Skill job worker.")
    parser.add_argument("--queue-root", type=Path, required=True)
    parser.add_argument("--worker-id", required=True)
    args = parser.parse_args()
    worker_loop(args.queue_root, args.worker_id)


if __name__ == "__main__":
    main()
