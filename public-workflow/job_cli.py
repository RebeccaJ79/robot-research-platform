"""Agent-friendly local queue commands for PDF-to-Skill jobs."""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from job_queue import JobStore
from job_worker import ensure_workers


def submit_job(pdf_paths: list[Path], queue_root: Path, state_dir: Path, output_path: Path, *, ocr_mode: str = "auto") -> str:
    """Copy caller-selected PDFs into local queue storage and start workers."""
    queue_root = Path(queue_root)
    upload_root = queue_root / "inputs" / uuid.uuid4().hex
    upload_root.mkdir(parents=True, exist_ok=True)
    copied_paths = []
    for index, source in enumerate(pdf_paths, start=1):
        source = Path(source)
        if not source.is_file():
            raise ValueError(f"PDF_MISSING: {source.name}")
        target = upload_root / f"{index:02d}-{source.name}"
        shutil.copy2(source, target)
        copied_paths.append(target)
    store = JobStore(queue_root)
    job_id = store.enqueue(copied_paths, Path(state_dir), Path(output_path), ocr_mode=ocr_mode)
    ensure_workers(queue_root)
    return job_id


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit or inspect a local PDF-to-Skill job.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    submit = subcommands.add_parser("submit")
    submit.add_argument("--pdf", action="append", required=True, type=Path)
    submit.add_argument("--queue-root", required=True, type=Path)
    submit.add_argument("--state", required=True, type=Path)
    submit.add_argument("--output", required=True, type=Path)
    submit.add_argument("--ocr", choices=("auto", "off", "force"), default="auto")
    status = subcommands.add_parser("status")
    status.add_argument("--queue-root", required=True, type=Path)
    status.add_argument("--job-id")
    args = parser.parse_args()
    if args.command == "submit":
        print(submit_job(args.pdf, args.queue_root, args.state, args.output, ocr_mode=args.ocr))
        return
    store = JobStore(args.queue_root)
    payload = store.get(args.job_id) if args.job_id else {"jobs": store.list_jobs(), "workers": store.workers()}
    print(json.dumps(_json_safe(payload), ensure_ascii=False))


if __name__ == "__main__":
    main()
